from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    llm_provider: Literal["auto", "gemini", "nvidia", "none"] = "auto"
    gemini_api_key: str = ""
    gemini_model: str = ""
    nvidia_api_key: str = ""
    nvidia_model: str = ""
    system1_backend: Literal["nli", "keyword", "jev"] = "nli"
    system1_model: str = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"
    database_url: str = "sqlite:///./prism.db"
    demo_mode: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
