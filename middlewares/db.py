from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from sqlalchemy.ext.asyncio import async_sessionmaker


class DataBaseSession(BaseMiddleware):
    """
    Middleware for managing database sessions.

    Attributes:
        session_pool: Pool of database sessions.
    """

    def __init__(self, session_pool: async_sessionmaker):
        """
        Initialize the middleware with a session pool.

        :param session_pool: Pool of database sessions.
        """
        self.session_pool = session_pool

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        """
        Asynchronously call the middleware.

        This method adds a database session to the data dictionary and then calls the handler.

        :param handler: Callable to be invoked.
        :param event: Telegram event.
        :param data: Dictionary to store data.
        :return: Result of the handler call.
        """
        async with self.session_pool() as session:
            data['session'] = session
            return await handler(event, data)
