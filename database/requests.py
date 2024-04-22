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
        user_name=data["user_name"],
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


async def db_add_movie_to_user(session: AsyncSession, tg_id: int, data: dict):
    # Query the user by tg_id
    user = await session.execute(select(User).where(User.tg_id == tg_id))
    user_in_db = user.scalars().first()

    if not user_in_db:
        logger.warning("User with tg_id=%s not found", tg_id)
        return

    logger.info("User tg_id=%s found in the database", tg_id)

    # Query the movie by tmdb_id
    movie = await session.execute(select(Movie).where(Movie.tmdb_id == data['tmdb_id']))
    movie_in_db = movie.scalars().first()

    if not movie_in_db:
        await db_add_movie(session, data)

    logger.info("Movie tmdb_id=%s found in the database", data['tmdb_id'])

    # Check if movie already added to user
    user_movie = await session.execute(select(user_movie_association).
                                       where(user_movie_association.c.user_tg_id == tg_id,
                                             user_movie_association.c.movie_tmdb_id == data['tmdb_id']))
    user_movie_in_db = user_movie.scalars().first()

    if user_movie_in_db:
        logger.info("Movie tmdb_id=%s already added to user tg_id=%s", data['tmdb_id'], tg_id)
        return

    await session.execute(user_movie_association.
                          insert().
                          values(user_tg_id=tg_id,
                                 movie_tmdb_id=data['tmdb_id']))
    await session.commit()
    logger.info("Movie tmdb_id=%s added to user tg_id=%s", data['tmdb_id'], tg_id)


async def db_add_movie(session: AsyncSession, data: dict):
    # Check if the movie already exists in the database
    existing_movie = await session.execute(select(Movie).where(Movie.tmdb_id == data['tmdb_id']))
    movie_in_db = existing_movie.scalars().first()

    if movie_in_db:
        logger.info("Movie tmdb_id=%s already exists in the database", data['tmdb_id'])
        return

    # Movie does not exist, create and add it to the database
    new_movie = Movie(tmdb_id=data['tmdb_id'], movie_name=data['movie_name'])
    session.add(new_movie)
    await session.commit()
    logger.info("New movie tmdb_id=%s added to the database", data['tmdb_id'])


async def db_get_movie_added_time(session: AsyncSession, tg_id: int, movie_id: int):
    stmt = select(user_movie_association.c.added_at).where(user_movie_association.c.user_tg_id == tg_id,
                                                           user_movie_association.c.movie_tmdb_id == movie_id)
    result = await session.execute(stmt)
    return result.scalar()


async def db_delete_movie_from_user(session, tg_id, movie_id):
    await session.execute(user_movie_association.delete().where(user_movie_association.c.user_tg_id == tg_id,
                                                                user_movie_association.c.movie_tmdb_id == movie_id))
    await session.commit()
    logger.info("Movie tmdb_id=%s deleted from user tg_id=%s", movie_id, tg_id)


async def db_get_users_movie_data(session: AsyncSession, tg_id: int, movie_id: int):
    stmt = (
        select(
            user_movie_association.c.is_watched,
            user_movie_association.c.personal_rating,
            user_movie_association.c.personal_review
        )
        .where(
            (user_movie_association.c.user_tg_id == tg_id) &
            (user_movie_association.c.movie_tmdb_id == movie_id)
        )
    )
    result = await session.execute(stmt)
    user_movie_data = result.fetchone()

    if user_movie_data is None:
        logger.info("No user movie data found for tg_id=%s and movie_id=%s", tg_id, movie_id)
        return None

    data = {
        "is_watched": user_movie_data[0],
        "personal_rating": user_movie_data[1],
        "personal_review": user_movie_data[2],
    }

    logger.info(f"User movie data: {data}")

    return data


async def db_change_movie_state(session: AsyncSession, tg_id: int, movie_id: int, state: bool):
    new_state = not state

    await session.execute(user_movie_association.update().
                          where(user_movie_association.c.user_tg_id == tg_id,
                                user_movie_association.c.movie_tmdb_id == movie_id).
                          values(is_watched=new_state))
    await session.commit()

    if new_state:
        logger.info("Movie tmdb_id=%s marked as watched for user tg_id=%s", movie_id, tg_id)
    else:
        logger.info("Movie tmdb_id=%s marked as unwatched for user tg_id=%s", movie_id, tg_id)


async def db_get_movie_state_for_user(session: AsyncSession, tg_id: int, movie_id: int):
    stmt = select(user_movie_association.c.is_watched).where(user_movie_association.c.user_tg_id == tg_id,
                                                             user_movie_association.c.movie_tmdb_id == movie_id)
    result = await session.execute(stmt)
    return result.scalar()


async def db_leave_review(session: AsyncSession, tg_id: int, movie_id: int, data: dict):
    await session.execute(user_movie_association.update().
                          where(user_movie_association.c.user_tg_id == tg_id,
                                user_movie_association.c.movie_tmdb_id == movie_id).
                          values(personal_rating=data['rating'],
                                 personal_review=data['review']))
    await session.commit()
    logger.info("User tg_id=%s left a review for movie tmdb_id=%s", tg_id, movie_id)






