from aiogram.fsm.state import State, StatesGroup


class ChangeLanguage(StatesGroup):
    """
    This class represents a part of the conversation where the bot is handling changing the user's language.
    It is a subclass of `StatesGroup` and has two states: `change_language` and `language_changed`.
    """
    change_language = State()
    language_changed = State()
