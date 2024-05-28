from enum import Enum


class Commands(str, Enum):
    """
    Enum representing different commands.

    Attributes:
        change_language: Command to change the language.
        get_random_movie: Command to get a random movie.
        movies_on_genre: Command to get movies based on genre.
    """
    change_language = "/language"
    get_random_movie = "/random"
    movies_on_genre = "/movies_on_genre"

