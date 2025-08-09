from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "computer-use-fastapi"
    environment: str = Field(default="development")

    # Networking
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    frontend_origin: str = Field(default="http://localhost:8080")

    # Database
    database_url: str = Field(default="sqlite:///./data/app.db", env="DATABASE_URL")

    # Anthropic
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-7-sonnet-20250219")
    enable_computer_use: bool = Field(default=True)

    # VNC / Desktop
    vnc_host: str = Field(default="vnc")
    vnc_port: int = Field(default=5901)
    novnc_port: int = Field(default=6080)
    vnc_password: str = Field(default="vncpassword", env="VNC_PASSWORD")
    media_dir: str = Field(default="data/media")

    # MongoDB (optional for event storage)
    mongodb_uri: Optional[str] = Field(default=None, env="MONGODB_URI")
    mongodb_db: str = Field(default="computer_use")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


