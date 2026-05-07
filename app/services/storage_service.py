from __future__ import annotations

import secrets
from datetime import UTC, datetime
from pathlib import Path

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
