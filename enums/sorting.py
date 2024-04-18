from enum import Enum


class SortingType(str, Enum):
    MOVIE_RATE = "vote_average"
    LIKED_TIME = "added_at"


class SortingOrder(str, Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"

