import datetime

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
    user = await session.execute(select(User).where(User.tg_id == tg_id))
    user_in_db = user.scalars().first()

    if not user_in_db:
        return []

    user_tg_id = user_in_db.tg_id

    # Query movies associated with the user
    stmt = select(Movie).join(user_movie_association).filter(user_movie_association.c.user_tg_id == user_tg_id)
    result = await session.execute(stmt)

    return result.scalars().all()


async def db_add_movie_to_user(session: AsyncSession, tg_id: int, tmdb_id: int):
    # Query the user by tg_id
    user = await session.execute(select(User).where(User.tg_id == tg_id))
    user_in_db = user.scalars().first()

    if not user_in_db:
        logger.warning("User with tg_id=%s not found", tg_id)
        return

    logger.info("User tg_id=%s found in the database", tg_id)

    # Query the movie by tmdb_id
    movie = await session.execute(select(Movie).where(Movie.tmdb_id == tmdb_id))
    movie_in_db = movie.scalars().first()

    if not movie_in_db:
        await db_add_movie(session, tmdb_id)

    logger.info("Movie tmdb_id=%s found in the database", tmdb_id)

    await session.execute(user_movie_association.
                          insert().
                          values(user_tg_id=tg_id,
                                 movie_tmdb_id=tmdb_id))
    await session.commit()
    logger.info("Movie tmdb_id=%s added to user tg_id=%s", tmdb_id, tg_id)


async def db_add_movie(session: AsyncSession, tmdb_id: int):
    # Check if the movie already exists in the database
    existing_movie = await session.execute(select(Movie).where(Movie.tmdb_id == tmdb_id))
    movie_in_db = existing_movie.scalars().first()

    if movie_in_db:
        logger.info("Movie tmdb_id=%s already exists in the database", tmdb_id)
        return movie_in_db

    # Movie does not exist, create and add it to the database
    new_movie = Movie(tmdb_id=tmdb_id)
    session.add(new_movie)
    await session.commit()
    logger.info("New movie tmdb_id=%s added to the database", tmdb_id)



