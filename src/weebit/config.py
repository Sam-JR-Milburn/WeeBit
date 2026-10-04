import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Overrides
class Settings(BaseSettings):
    PROJECT_NAME: str = "Weebit API"
    DEBUG: bool = False

    # Misc config
    HOSTNAME: str = "localhost"

    # DB config
    DB_USER: str = "weebit_srvc_acc"
    DB_PASSWORD: str = "fallbackpassword"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "weebit_db"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Cache config
    REDIS_URL: str = "localhost"
    REDIS_PORT: int = 6379

    model_config = SettingsConfigDict(env_file=os.getenv("ENV_FILE"), env_file_encoding="utf-8", extra="ignore")

settings = Settings(_env_file=os.getenv("ENV_FILE", ".env"))