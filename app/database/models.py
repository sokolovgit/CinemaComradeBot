from typing import List

from sqlalchemy import BigInteger, String, Table, ForeignKey, Column
from sqlalchemy.orm import relationship, Mapped, DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


user_movie_association = Table(
    'user_movie_association', Base.metadata,
    Column('user_id', ForeignKey('users.id'), primary_key=True),
    Column('movie_id', ForeignKey('movies.id'), primary_key=True)
)


movie_genre_association = Table(
    'movie_genre_association', Base.metadata,
    Column('movie_id', ForeignKey('movies.id'), primary_key=True),
    Column('genre_id', ForeignKey('genres.id'), primary_key=True)
)


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)

    liked_movies: Mapped[List["Movie"]] = relationship(secondary=user_movie_association)


class Movie(Base):
    __tablename__ = 'movies'

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(unique=True)

    genres: Mapped[List["Genres"]] = relationship(secondary=movie_genre_association)


class Genres(Base):
    __tablename__ = 'genres'

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(unique=True)









