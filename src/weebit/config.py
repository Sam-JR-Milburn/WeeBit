import os
from typing import Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Overrides
class Settings(BaseSettings):
    PROJECT_NAME: str = "Weebit API"
    DEBUG: bool = False

    # Misc config
    HOST: str = Field(default="localhost", validation_alias="HOST")
    PORT: int = Field(default=8080, validation_alias="PORT")

    # DB config
    DB_USER: str = Field(validation_alias="POSTGRES_USER") # "weebit_srvc_acc"
    DB_PASSWORD: str = Field(validation_alias="POSTGRES_PASSWORD") # "fallbackpassword"
    DB_HOST: str = Field(default="localhost", validation_alias="POSTGRES_HOST") # "localhost"
    DB_PORT: int = Field(default=5432, validation_alias="POSTGRES_PORT") # 5432
    DB_NAME: str = Field(validation_alias="POSTGRES_DB") # "weebit_db"

    @property
    def base_url(self) -> str:
        return f"http://{self.HOST}:{self.PORT}"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Cache config
    REDIS_URL: str = "localhost"
    REDIS_PORT: int = 6379
    
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
