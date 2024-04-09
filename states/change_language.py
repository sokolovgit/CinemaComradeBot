from aiogram.fsm.state import State, StatesGroup


class ChangeLanguage(StatesGroup):
    change_language = State()
    language_changed = State()