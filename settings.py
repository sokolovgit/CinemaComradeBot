from typing import List

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    The Settings class is used to manage and access various settings or configuration values that your application needs to run.

    Attributes:
        TOKEN (SecretStr): The bot token.
        DATABASE_URL (str): The database URL.
        DEFAULT_LOCALE (str): The default locale.
        TMDB_API_KEY (SecretStr): The TMDB API key.
        REDIS_HOST (str): The Redis host.
        REDIS_PORT (int): The Redis port.
        PAGE_SIZE (int): The page size.
        MAX_GENRES (int): The maximum number of genres.
    """
    TOKEN: SecretStr
    DATABASE_URL: str
    DEFAULT_LOCALE: str

    TMDB_API_KEY: SecretStr

    REDIS_HOST: str
    REDIS_PORT: int

    PAGE_SIZE: int
    MAX_GENRES: int

    model_config = SettingsConfigDict(
        env_file=('.env', 'stack.env'),
        env_file_encoding='utf-8',
        extra='ignore')


settings = Settings()