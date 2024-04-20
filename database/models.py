from typing import List

from sqlalchemy import BigInteger, String, Table, ForeignKey, Column, DateTime, func
from sqlalchemy.orm import relationship, Mapped, DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


user_movie_association = Table(
    'user_movie_association', Base.metadata,
    Column('user_tg_id', ForeignKey('users.tg_id'), primary_key=True),
    Column('movie_tmdb_id', ForeignKey('movies.tmdb_id'), primary_key=True),
    Column('added_at', DateTime, server_default=func.now())  # Add a column for the timestamp
)

movie_genre_association = Table(
    'movie_genre_association', Base.metadata,
    Column('movie_tmdb_id', ForeignKey('movies.tmdb_id'), primary_key=True),
    Column('genre_tmdb_id', ForeignKey('genres.tmdb_id'), primary_key=True)
)


class User(Base):
    __tablename__ = 'users'

    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    liked_movies: Mapped[List["Movie"]] = relationship(
        secondary=user_movie_association,
        back_populates="users"
    )


class Movie(Base):
    __tablename__ = 'movies'

    tmdb_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    genres: Mapped[List["Genres"]] = relationship(secondary=movie_genre_association)
    users: Mapped[List["User"]] = relationship(
        secondary=user_movie_association,
        back_populates="liked_movies"
    )

    def __repr__(self):
        return f"<Movie(tmdb_id={self.tmdb_id})>"

    def to_dict(self):
        return {
            "tmdb_id": self.tmdb_id,
            # Add other attributes here if needed
        }


class Genres(Base):
    __tablename__ = 'genres'

    tmdb_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)









