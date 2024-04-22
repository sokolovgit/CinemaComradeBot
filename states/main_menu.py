from aiogram.fsm.state import State, StatesGroup


class MainMenu(StatesGroup):
    show_list = State()
    change_language = State()
    add_movie = State()
    show_details = State()
    ask_to_leave_review = State()
    leave_rating = State()
    leave_review = State()

