from aiogram.fsm.state import State, StatesGroup


class MainMenu(StatesGroup):
    show_list = State()

