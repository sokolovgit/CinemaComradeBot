from enum import Enum


class SortingType(str, Enum):
    """
    Enum representing different types of sorting.

    Attributes:
        MOVIE_RATE: Sorting by movie rating.
        LIKED_TIME: Sorting by the time the movie was liked.
    """
    MOVIE_RATE = "vote_average"
    LIKED_TIME = "added_at"


class SortingOrder(str, Enum):
    """
    Enum representing different sorting orders.

    Attributes:
        ASCENDING: Ascending order.
        DESCENDING: Descending order.
    """
    ASCENDING = "asc"
    DESCENDING = "desc"

