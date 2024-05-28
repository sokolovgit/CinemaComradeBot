from typing import Any, Optional, Union, cast

from aiogram.types import User
from aiogram_i18n.managers import BaseManager
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from enums import Language


class RedisManager(BaseManager):
    """
    This class is a custom manager for handling internationalization (i18n) using Redis as a storage system.
    It is a subclass of `BaseManager` and overrides the `get_locale`, `get_locale_by_user_id`, and `set_locale` methods.
    """
    def __init__(
        self,
        redis: Union["Redis[Any]", ConnectionPool],
        default_locale: Optional[str] = None,
    ):
        """
        Initializes a new instance of the `RedisManager` class.

        Args:
            redis (Union["Redis[Any]", ConnectionPool]): The Redis connection or connection pool.
            default_locale (Optional[str]): The default locale. Defaults to None.
        """
        super().__init__(default_locale=default_locale)
        if isinstance(redis, ConnectionPool):
            redis = Redis(connection_pool=redis)
        self.redis: "Redis[Any]" = redis

    async def get_locale_by_user_id(self, user_id: int) -> Optional[str]:
        """
        Retrieves the locale for the specified user ID from Redis.

        Args:
            user_id (int): The ID of the user.

        Returns:
            Optional[str]: The locale for the user, or None if no locale is set.
        """
        redis_key = f"i18n:{user_id}:locale"
        value = await self.redis.get(redis_key)

        if isinstance(value, bytes):
            return value.decode("utf-8")

        return value

    async def get_locale(self, event_from_user: User) -> str:
        """
        Retrieves the locale for the specified user from Redis.

        If no locale is set for the user, this method checks if the user's language code is a valid `Language` member.
        If it is, the user's language code is returned. Otherwise, the default locale is returned.

        Args:
            event_from_user (User): The user.

        Returns:
            str: The locale for the user.
        """
        value = await self.get_locale_by_user_id(event_from_user.id)

        if not value and event_from_user.language_code in Language.__members__:
            return event_from_user.language_code or cast(str, self.default_locale)

        return value or cast(str, self.default_locale)

    async def set_locale(self, language: str, event_from_user: User) -> None:
        """
        Sets the locale for the specified user in Redis.

        Args:
            language (str): The locale to set.
            event_from_user (User): The user.
        """
        redis_key = f"i18n:{event_from_user.id}:locale"

        await self.redis.set(redis_key, language)

