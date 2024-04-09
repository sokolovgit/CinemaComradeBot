from typing import List

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    TOKEN: SecretStr
    DATABASE_URL: str
    DEFAULT_LOCALE: str

    TMDB_API_KEY: SecretStr

    REDIS_HOST: str
    REDIS_PORT: int

    PAGE_SIZE: int

    model_config = SettingsConfigDict(
        env_file=('.env', 'stack.env'),
        env_file_encoding='utf-8',
        extra='ignore')


settings = Settings()