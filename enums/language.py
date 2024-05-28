from enum import Enum


class Language(str, Enum):
    """
    Enum representing different languages.

    Attributes:
        EN: English language.
        UK: Ukrainian language.
    """
    EN = "en"
    UK = "uk"
    