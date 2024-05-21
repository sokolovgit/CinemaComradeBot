from enum import Enum


class Commands(str, Enum):
    change_language = "/language"
    get_random_movie = "/random"

