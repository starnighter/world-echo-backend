from __future__ import annotations

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
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
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
