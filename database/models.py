from typing import List

from sqlalchemy import BigInteger, String, Table, ForeignKey, Column, DateTime, func, Boolean
from sqlalchemy.orm import relationship, Mapped, DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    """
    pass


user_movie_association = Table(
    'user_movie_association', Base.metadata,
    Column('user_tg_id', ForeignKey('users.tg_id'), primary_key=True),
    Column('movie_tmdb_id', ForeignKey('movies.tmdb_id'), primary_key=True),
    Column('is_watched', Boolean, default=False),
    Column('personal_rating', BigInteger, default=None),
    Column('personal_review', String, default=None),
    Column('added_at', DateTime, server_default=func.now())
)
"""
Association table for User and Movie models.
"""


class User(Base):
    """
    User model representing a user in the system.

    Attributes:
        tg_id: Telegram ID of the user.
        user_name: Name of the user.
        liked_movies: List of movies liked by the user.
    """
    __tablename__ = 'users'

    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_name: Mapped[str] = mapped_column(String)
    liked_movies: Mapped[List["Movie"]] = relationship(
        secondary=user_movie_association,
        back_populates="users"
    )


class Movie(Base):
    """
    Movie model representing a movie in the system.

    Attributes:
        tmdb_id: TMDB ID of the movie.
        movie_name: Name of the movie.
        users: List of users who liked the movie.
    """
    __tablename__ = 'movies'

    tmdb_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    movie_name: Mapped[str] = mapped_column(String)
    users: Mapped[List["User"]] = relationship(
        secondary=user_movie_association,
        back_populates="liked_movies"
    )

    def __repr__(self):
        """
       String representation of the Movie instance.
       :return: String representation of the Movie instance.
       """
        return f"<Movie(tmdb_id={self.tmdb_id})>"

    def to_dict(self):
        """
        Convert the Movie instance to a dictionary.
        :return: Dictionary representation of the Movie instance.
        """
        return {
            "tmdb_id": self.tmdb_id,
            # Add other attributes here if needed
        }











