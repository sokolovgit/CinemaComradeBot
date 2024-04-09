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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger)
    liked_movies: Mapped[List["Movie"]] = relationship(secondary=user_movie_association)


class Movie(Base):
    __tablename__ = 'movies'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tmdb_id: Mapped[int] = mapped_column()
    genres: Mapped[List["Genres"]] = relationship(secondary=movie_genre_association)

    def __repr__(self):
        return f"<Movie(id={self.id}, tmdb_id={self.tmdb_id})>"

    def to_dict(self):
        return {
            "id": self.id,
            "tmdb_id": self.tmdb_id,
            # Add other attributes here if needed
        }

class Genres(Base):
    __tablename__ = 'genres'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tmdb_id: Mapped[int] = mapped_column()









