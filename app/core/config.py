from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "World Echo API"
    app_version: str = "1.0.0"
    environment: Literal["local", "dev", "test", "prod"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/v1"
    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/world_echo"

    cors_origins: list[str] = ["*"]
    static_url: str = "/static"
    storage_root: Path = BASE_DIR / "storage"
    static_root: Path = BASE_DIR / "storage"
    public_base_url: str = "http://localhost:8000"

    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/v1/auth/oauth/github/callback"
    qq_client_id: str = ""
    qq_client_secret: str = ""
    qq_redirect_uri: str = "http://localhost:8000/v1/auth/oauth/qq/callback"
    qq_scope: str = "get_user_info"
    mock_oauth: bool = True

    mock_asr: bool = True
    asr_api_url: str = ""
    asr_api_key: str = ""
    xfyun_app_id: str = ""
    xfyun_api_key: str = ""
    xfyun_rtasr_url: str = "ws://rtasr.xfyun.cn/v1/ws"

    mock_vision_prompt: bool = True
    siliconflow_api_url: str = "https://api.siliconflow.cn/v1/chat/completions"
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_api_key: str = ""
    siliconflow_model: str = "Qwen/Qwen2.5-VL-72B-Instruct"

    mock_audio_analysis: bool = True
    enable_essentia: bool = False
    models_dir: Path = BASE_DIR / "app" / "models"

    mock_minimax: bool = True
    minimax_api_url: str = "https://api.minimaxi.com/v1/music_generation"
    minimax_api_key: str = ""

    upload_image_max_mb: int = 10
    upload_audio_max_mb: int = 50


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    return settings
