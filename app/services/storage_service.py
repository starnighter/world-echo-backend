from __future__ import annotations

import asyncio
import mimetypes
import secrets
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import BadRequestException


class StorageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def save_upload(
        self,
        file: UploadFile,
        category: str,
        allowed_extensions: set[str],
        max_size_mb: int,
    ) -> str:
        extension = self._get_extension(file.filename or "")
        if extension not in allowed_extensions:
            raise BadRequestException("Unsupported file format")

        content = await file.read()
        max_size = max_size_mb * 1024 * 1024
        if len(content) > max_size:
            raise BadRequestException("File too large")

        relative_path = self._build_relative_path(category, extension)
        target = self.settings.storage_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return f"{self.settings.static_url}/{relative_path.as_posix()}"

    def save_bytes(self, payload: bytes, category: str, extension: str) -> str:
        relative_path = self._build_relative_path(category, extension.lstrip("."))
        target = self.settings.storage_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        # Strip bloated ID3 tags from generated MP3s to prevent OOM
        # on mobile players (ExoPlayer's Id3Peeker reads the whole tag).
        if extension.lstrip(".").lower() == "mp3":
            payload = self.normalize_mp3_payload(payload)
        target.write_bytes(payload)
        return f"{self.settings.static_url}/{relative_path.as_posix()}"

    async def convert_audio_to_mp3(
        self,
        source_path: Path,
        category: str = "converted/audio",
    ) -> str:
        relative_path = self._build_relative_path(category, "mp3")
        target = self.settings.storage_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)

        try:
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-y",
                "-i",
                str(source_path),
                "-vn",
                "-acodec",
                "libmp3lame",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-b:a",
                "256k",
                str(target),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise BadRequestException("Audio conversion requires ffmpeg") from exc

        _, stderr = await process.communicate()
        if process.returncode != 0:
            target.unlink(missing_ok=True)
            detail = stderr.decode("utf-8", errors="ignore").strip().splitlines()
            message = detail[-1] if detail else "Audio conversion failed"
            raise BadRequestException(message)

        payload = self.normalize_mp3_payload(target.read_bytes())
        target.write_bytes(payload)
        return f"{self.settings.static_url}/{relative_path.as_posix()}"

    async def materialize_source(
        self,
        source_url: str,
        *,
        category: str,
        default_extension: str,
        max_size_mb: int,
    ) -> Path:
        try:
            return self.resolve_local_path(source_url)
        except BadRequestException:
            pass

        parsed = urlparse(source_url)
        if parsed.scheme not in {"http", "https"}:
            raise BadRequestException("Unsupported source_url")

        timeout = httpx.Timeout(connect=20.0, read=120.0, write=20.0, pool=20.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, trust_env=False) as client:
            response = await client.get(source_url)
            response.raise_for_status()
            content = response.content
            max_size = max_size_mb * 1024 * 1024
            if len(content) > max_size:
                raise BadRequestException("File too large")
            extension = self._infer_extension(source_url, response.headers.get("content-type"), default_extension)
            relative_path = self._build_relative_path(category, extension)
            target = self.settings.storage_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            return target

    def resolve_local_path(self, source_url: str) -> Path:
        prefix = f"{self.settings.static_url}/"
        if source_url.startswith(prefix):
            return self.settings.storage_root / source_url.removeprefix(prefix)
        if source_url.startswith(self.settings.public_base_url):
            path = source_url.removeprefix(self.settings.public_base_url)
            return self.resolve_local_path(path)
        raise BadRequestException("Unsupported source_url")

    @classmethod
    def normalize_mp3_payload(cls, data: bytes, max_tag_bytes: int = 1024 * 1024) -> bytes:
        """Validate MP3 bytes and strip oversized ID3v2 tags.

        Large ID3 tags (e.g. with embedded cover art) cause ExoPlayer's
        Id3Peeker to allocate hundreds of MB and crash with OOM.
        """
        if len(data) < 4:
            raise BadRequestException("Invalid MP3 audio")

        # ID3v2 header: "ID3" + 2-byte version + 1-byte flags + 4-byte size
        if len(data) >= 10 and data[:3] == b"ID3":
            # Size is a synchsafe integer (7 bits per byte). If any high bit is
            # set, the header is corrupt and can make ExoPlayer over-allocate.
            raw = data[6:10]
            if any(byte & 0x80 for byte in raw):
                raise BadRequestException("Invalid MP3 ID3 header")
            tag_size = (raw[0] << 21) | (raw[1] << 14) | (raw[2] << 7) | raw[3]
            tag_total = tag_size + 10
            if tag_total > len(data):
                raise BadRequestException("Invalid MP3 ID3 header")
            if tag_total > max_tag_bytes:
                data = data[tag_total:]

        if not cls._has_mp3_frame(data):
            raise BadRequestException("Invalid MP3 audio")
        return data

    @staticmethod
    def _has_mp3_frame(data: bytes) -> bool:
        """Return true if the payload contains a plausible MPEG audio frame."""
        start = 0
        if len(data) >= 10 and data[:3] == b"ID3":
            raw = data[6:10]
            tag_size = (raw[0] << 21) | (raw[1] << 14) | (raw[2] << 7) | raw[3]
            start = min(len(data), tag_size + 10)

        for index in range(start, max(start, len(data) - 1)):
            first = data[index]
            second = data[index + 1]
            if first != 0xFF or (second & 0xE0) != 0xE0:
                continue
            version = (second >> 3) & 0x03
            layer = (second >> 1) & 0x03
            if version != 0x01 and layer != 0x00:
                return True
        return False

    @staticmethod
    def _get_extension(filename: str) -> str:
        return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    def _build_relative_path(self, category: str, extension: str) -> Path:
        now = datetime.now(UTC)
        name = secrets.token_hex(16)
        return Path(category) / now.strftime("%Y/%m/%d") / f"{name}.{extension}"

    @staticmethod
    def _infer_extension(source_url: str, content_type: str | None, default_extension: str) -> str:
        path_extension = Path(urlparse(source_url).path).suffix.lstrip(".").lower()
        if path_extension:
            return path_extension
        if content_type:
            mime = content_type.split(";", 1)[0].strip().lower()
            guessed = mimetypes.guess_extension(mime)
            if guessed:
                return guessed.lstrip(".")
        return default_extension.lstrip(".")
