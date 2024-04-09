from typing import List

from utils.logger import setup_logger

from sqlalchemy import select
from database.models import User, Movie, user_movie_association
from sqlalchemy.ext.asyncio import AsyncSession


logger = setup_logger()


async def db_add_user(session: AsyncSession, data: dict):
    existing_user = await session.execute(select(User).where(User.tg_id == data["tg_id"]))
    user_in_db = existing_user.scalars().first()

    if user_in_db:
        logger.info("User id=%s already in database", data["tg_id"])
        return

    new_user = User(
        tg_id=data["tg_id"],
    )

    session.add(new_user)
    await session.commit()
    logger.info("New user added to database id=%s", new_user.tg_id)


async def db_get_all_movies(session: AsyncSession):
    movies = await session.execute(select(Movie))
    return movies.scalars().all()


async def db_get_users_movies(session: AsyncSession, tg_id: int):
    # Querying movies associated with the user_id
    stmt = select(Movie).join(user_movie_association).filter(user_movie_association.c.user_id == tg_id)

    # Executing the query
    movies = await session.execute(stmt)

    # Returning the list of movies
    return movies.scalars().all()
