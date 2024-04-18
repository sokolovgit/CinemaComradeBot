from enum import Enum


class SortingType(str, Enum):
    MOVIE_RATE = "vote_average"
    LIKED_TIME = "liked_time"


class SortingOrder(str, Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"

