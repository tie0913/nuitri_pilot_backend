# app/core/config.py
from functools import lru_cache
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    # Port Configuration
    PORT: int = 8080

    # Email Sender Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = "jeic myvu opql afef"
    SMTP_FROM: Optional[str] = "nuitripilot@gmail.com"
    SMTP_STARTTLS: bool = True

    # Logger Configuration
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_JSON: bool = False

    # Settings 行为
    model_config = SettingsConfigDict(
        env_file=".env",              
        env_file_encoding="utf-8",
        env_prefix="",                
        case_sensitive=False,         
        extra="ignore"
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()