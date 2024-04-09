import typing

from aiogram.types import CallbackQuery, Message

from settings import settings

from typing import Dict, Any

from aiogram import F

from aiogram_dialog import DialogManager, Dialog, Window, StartMode
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.text import Format, Multi, List, Const
from aiogram_dialog.widgets.kbd import Row, Button, ScrollingGroup

from aiogram_i18n import I18nContext

from sqlalchemy.ext.asyncio import AsyncSession

from database.requests import db_get_movies

from utils.logger import setup_logger
from utils.i18n_format import I18NFormat

from states.main_menu import MainMenu
from states.change_language import ChangeLanguage


logger = setup_logger()


async def get_list_movies(event_isolation, dialog_manager: DialogManager, session: AsyncSession, *args, **kwargs):
    db_movies = await db_get_movies(session)
    movie_list = [movie.to_dict() for movie in db_movies]
    dialog_manager.dialog_data["movies"] = movie_list

    if "page_size" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["page_size"] = settings.PAGE_SIZE

    if "current_pos" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["current_pos"] = 0

    movies_num = len(movie_list)
    is_empty = movies_num == 0

    message = "no movies" if is_empty else make_list(movie_list, dialog_manager)

    return {
        "is_empty": is_empty,
        "message": message,
        "current_page": dialog_manager.dialog_data.get("current_page", 1),
        "pages_num": movies_num // settings.PAGE_SIZE + 1
    }


def make_list(movies: typing.List, dialog_manager: DialogManager):
    page_size = dialog_manager.dialog_data["page_size"]
    current_pos = dialog_manager.dialog_data["current_pos"]
    current_page = current_pos // page_size + 1
    dialog_manager.dialog_data["current_page"] = current_page

    movies_num = len(movies)

    start = (current_page - 1) * page_size
    end = start + page_size

    movie_list = []
    for i in range(start, min(end, movies_num)):
        movie = movies[i]
        movie_str = f"{movie['id']}, {movie['tmdb_id']}"
        if i == current_pos:
            movie_str = f"<b>{movie_str}</b>"
        movie_list.append(movie_str)

    return "\n".join(movie_list)


async def on_arrow_up(callback: CallbackQuery, button: Button,
                      dialog_manager: DialogManager):
    current_pos = dialog_manager.dialog_data["current_pos"]
    movies_num = len(dialog_manager.dialog_data["movies"])

    if current_pos == 0:
        # If it's the first position, go to the last position
        dialog_manager.dialog_data["current_pos"] = movies_num - 1
    else:
        dialog_manager.dialog_data["current_pos"] -= 1


async def on_arrow_down(callback: CallbackQuery, button: Button,
                        dialog_manager: DialogManager):
    current_pos = dialog_manager.dialog_data["current_pos"]
    movies_num = len(dialog_manager.dialog_data["movies"])

    if current_pos == movies_num - 1:
        # If it's the last position, go to the first position
        dialog_manager.dialog_data["current_pos"] = 0
    else:
        dialog_manager.dialog_data["current_pos"] += 1


async def on_arrow_left(callback: CallbackQuery, button: Button,
                        dialog_manager: DialogManager):
    current_pos = dialog_manager.dialog_data["current_pos"]
    page_size = dialog_manager.dialog_data["page_size"]
    movies_num = len(dialog_manager.dialog_data["movies"])
    pages_num = movies_num // page_size + 1

    if current_pos - page_size < 0:
        dialog_manager.dialog_data["current_pos"] = (pages_num - 1) * page_size
    else:
        dialog_manager.dialog_data["current_pos"] -= page_size


async def on_arrow_right(callback: CallbackQuery, button: Button,
                         dialog_manager: DialogManager):
    current_pos = dialog_manager.dialog_data["current_pos"]
    page_size = dialog_manager.dialog_data["page_size"]
    movies_num = len(dialog_manager.dialog_data["movies"])
    pages_num = movies_num // page_size + (1 if movies_num % page_size else 0)
    current_page = current_pos // page_size + 1

    if current_page == pages_num:
        # If it's the last page, go to the first page
        dialog_manager.dialog_data["current_pos"] = 0
    elif current_page == pages_num - 1 and current_pos + page_size >= movies_num:
        dialog_manager.dialog_data["current_pos"] = (movies_num % page_size - 1) + (pages_num - 1) * page_size
    else:
        dialog_manager.dialog_data["current_pos"] += page_size


async def change_language(message: Message, i18n: I18nContext, dialog_manager: DialogManager):
    await dialog_manager.start(ChangeLanguage.change_language, mode=StartMode.RESET_STACK)


main_menu = Dialog(
    Window(
        Multi(
            I18NFormat("show-movies", when=~F["is_empty"]),
            I18NFormat("no-movies", when=F["is_empty"]),
            Format("{message}", when=~F["is_empty"]),
            ),
        Row(
            Button(
                I18NFormat("arrow-down"),
                id="arrow_down",
                on_click=on_arrow_down
                ),
            Button(
                I18NFormat("get-description"),
                id="get_description",
                ),
            Button(
                I18NFormat("arrow-up"),
                id="arrow_up",
                on_click=on_arrow_up
                ),
            when=~F["is_empty"]
            ),
        Row(
            Button(
                I18NFormat("arrow-left"),
                id="arrow_left",
                on_click=on_arrow_left
                ),
            Button(
                Format("{current_page} / {pages_num}", when=~F["is_empty"]),
                id="page"
                ),
            Button(
                I18NFormat("arrow-right"),
                id="arrow_right",
                on_click=on_arrow_right
                ),
            when=~F["is_empty"]
            ),
        Button(
            I18NFormat("sorting", order="pass"),
            id="sorting",
            when=~F["is_empty"]
        ),
        state=MainMenu.show_list,
        getter=get_list_movies
    )
)



