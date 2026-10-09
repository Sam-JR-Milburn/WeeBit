import os
from typing import Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Overrides
class Settings(BaseSettings):
    PROJECT_NAME: str = "Weebit API"
    DEBUG: bool = False

    # Misc config
    HOSTNAME: str = "localhost"

    # DB config
    DB_USER: str = Field(validation_alias="POSTGRES_USER") # "weebit_srvc_acc"
    DB_PASSWORD: str = Field(validation_alias="POSTGRES_PASSWORD") # "fallbackpassword"
    DB_HOST: str = Field(default="localhost", validation_alias="POSTGRES_HOST") # "localhost"
    DB_PORT: int = Field(default=5432, validation_alias="POSTGRES_PORT") # 5432
    DB_NAME: str = Field(validation_alias="POSTGRES_DB") # "weebit_db"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Cache config
    REDIS_URL: str = "localhost"
    REDIS_PORT: int = 6379
    
    # Ingest allowed origins for frontend.
    allowed_origins: Union[list[str], str] = Field(
        default=[
            "http://localhost:3080",
            "http://127.0.0.1:3080",
        ]
    )
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Union[str, list[str]]) -> list[str]:
        if isinstance(v, str):
            v_trimmed = v.strip().strip("'\"")
            if v_trimmed.startswith("[") and v_trimmed.endswith("]"):
                import json
                return json.loads(v_trimmed)

            return [origin.strip() for origin in v_trimmed.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(env_file=os.getenv("ENV_FILE"), env_file_encoding="utf-8", extra="ignore")

settings = Settings(_env_file=os.getenv("ENV_FILE", ".env"))
