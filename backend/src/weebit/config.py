import os
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    allowed_origins: list[str] = Field(
        default=[
            "http://localhost:3080",
            "http://127.0.0.1:3080"
        ],
        validation_alias="ALLOWED_ORIGINS",
    )

    # Append BASE_URL into allowed_origins.
    @model_validator(mode="after")
    def include_base_url_in_origins(self) -> "Settings":
        if self.base_url not in self.allowed_origins:
            self.allowed_origins.append(self.base_url)
        return self

    model_config = SettingsConfigDict(env_file=os.getenv("ENV_FILE"), env_file_encoding="utf-8", extra="ignore", case_sensitive=False)

settings = Settings()
