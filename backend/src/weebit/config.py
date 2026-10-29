import os
from pydantic import Field, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any

# Overrides
class Settings(BaseSettings):
    PROJECT_NAME: str = "Weebit API"
    DEBUG: bool = False

    # Misc config
    BACKEND_HOST: str = Field(default="localhost", validation_alias="BACKEND_HOST")
    BACKEND_PORT: int = Field(default=8080, validation_alias="BACKEND_PORT")

    # DB config
    DB_USER: str = Field(validation_alias="POSTGRES_USER") # "weebit_srvc_acc"
    DB_PASSWORD: str = Field(validation_alias="POSTGRES_PASSWORD") # "fallbackpassword"
    DB_HOST: str = Field(default="localhost", validation_alias="POSTGRES_HOST") # "localhost"
    DB_PORT: int = Field(default=5432, validation_alias="POSTGRES_PORT") # 5432
    DB_NAME: str = Field(validation_alias="POSTGRES_DB") # "weebit_db"

    @property
    def base_url(self) -> str:
        return f"http://{self.BACKEND_HOST}:{self.BACKEND_PORT}"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Cache config
    CACHE_URL: str = Field(default="localhost", validation_alias="REDIS_URL")
    CACHE_PORT: int = Field(default=6379, validation_alias="REDIS_PORT")
    CACHE_PASSWORD: str | None = Field(default=None, validation_alias="REDIS_PASSWORD")

    @property
    def redis_url(self) -> str:
        """Constructs a secure redis URL string for async clients (like redis-py)"""
        if self.CACHE_PASSWORD:
            return f"rediss://:{self.CACHE_PASSWORD}@{self.CACHE_URL}:{self.CACHE_PORT}"
        return f"redis://{self.CACHE_URL}:{self.CACHE_PORT}"
    
    # Ingest allowed origins for frontend.
    allowed_origins: str | list[str] = Field(
        default=[
            "http://localhost:3080",
            "http://127.0.0.1:3080"
        ],
        validation_alias="ALLOWED_ORIGINS",
    )
    
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            # If it's a comma-separated string from Azure or .env, split and strip whitespace
            if "," in value:
                return [origin.strip() for origin in value.split(",") if origin.strip()]
            # If it's a single string URL, turn it into a list
            if value.startswith("http"):
                return [value.strip()]
            # If it's stored as a JSON string array, try parsing it safely
            try:
                import json
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(o).strip() for o in parsed]
            except Exception:
                pass
        elif isinstance(value, list):
            return [str(o).strip() for o in value]
        return value
        
    # Append BASE_URL into allowed_origins.
    @model_validator(mode="after")
    def include_base_url_in_origins(self) -> "Settings":
        if self.base_url not in self.allowed_origins:
            self.allowed_origins.append(self.base_url)
        return self

    model_config = SettingsConfigDict(env_file=os.getenv("ENV_FILE"), env_file_encoding="utf-8", extra="ignore", case_sensitive=False)

settings = Settings()
