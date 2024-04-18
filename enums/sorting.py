from enum import Enum


class Sorting(str, Enum):
    ASCENDING = "ascending"
    DESCENDING = "descending"
    DATE_ADDED = "date_added"
