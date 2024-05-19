import operator
import typing
from typing import Any

import tmdbsimple as tmdb

from settings import settings

from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, Dialog, Window, StartMode, ShowMode
from aiogram_dialog.widgets.text import Format, Multi, List, Const
from aiogram_dialog.widgets.kbd import Row, Button, Select, Column
from aiogram_i18n import I18nContext

from sqlalchemy.ext.asyncio import AsyncSession

from database.requests import db_get_users_movies, db_get_all_movies

from utils.logger import setup_logger
from utils.i18n_format import I18NFormat

from states.main_menu import MainMenu

from enums.language import Language
from enums.sorting import SortingType, SortingOrder

logger = setup_logger()
tmdb.API_KEY = settings.TMDB_API_KEY.get_secret_value()


async def get_movies_list(event_isolation, dialog_manager: DialogManager,
                          session: AsyncSession, i18n: I18nContext, *args, **kwargs):
    dialog_manager.dialog_data["tg_id"] = dialog_manager.start_data["tg_id"]
    dialog_manager.dialog_data.setdefault("page_size", settings.PAGE_SIZE)
    dialog_manager.dialog_data.setdefault("current_page", 1)
    dialog_manager.dialog_data.setdefault("sorting_type", SortingType.MOVIE_RATE)
    dialog_manager.dialog_data.setdefault("sorting_order", SortingOrder.DESCENDING)

    tg_id = dialog_manager.dialog_data.get("tg_id")

    #db_movies = await db_get_users_movies(session, tg_id)
    db_movies = await db_get_all_movies(session)

    movies_num = len(db_movies)

    dialog_manager.dialog_data["pages_num"] = movies_num // settings.PAGE_SIZE + 1

    is_empty = movies_num == 0

    movies_info = await fetch_movie_details(db_movies, i18n.locale, dialog_manager)
    movies_on_page = await make_list(movies_info, dialog_manager, i18n)

    return {
        "is_empty": is_empty,
        "movies_on_page": movies_on_page,
        "current_page": dialog_manager.dialog_data.get("current_page", 1),
        "pages_num": dialog_manager.dialog_data.get("pages_num", 1)
    }


async def sort_movies(movies, dialog_manager: DialogManager):
    sorting_type = dialog_manager.dialog_data.get("sorting_type")
    sorting_order = dialog_manager.dialog_data.get("sorting_order")
    reverse = False

    if sorting_type == SortingType.MOVIE_RATE:
        sort_key = lambda movie: movie['vote_average']
    if sorting_order == SortingOrder.DESCENDING:
        reverse = True

    movies.sort(key=sort_key, reverse=reverse)


async def fetch_movie_details(db_movies, language, dialog_manager: DialogManager):
    movies_info = []
    for movie in db_movies:
        movie_id = movie.tmdb_id
        movie_info = tmdb.Movies(id=movie_id).info(language=language)
        movies_info.append(movie_info)

    await sort_movies(movies_info, dialog_manager)

    return movies_info


async def make_list(movies_info: typing.List[dict], dialog_manager: DialogManager, i18n: I18nContext):
    page_size = dialog_manager.dialog_data["page_size"]
    current_page = dialog_manager.dialog_data["current_page"]

    movies_num = len(movies_info)

    start = (current_page - 1) * page_size
    end = start + page_size

    movie_list = []
    index = 1
    for i in range(start, min(end, movies_num)):
        movie = movies_info[i]

        movie_str = f"{i + 1}. {movie['title']} {movie['vote_average']}"
        movie_list.append((movie_str, movie['id']))
        index += 1

    return movie_list


async def on_arrow_left(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    data = dialog_manager.dialog_data
    current_page, pages_num = data.get("current_page"), data.get("pages_num")

    data["current_page"] = pages_num if current_page == 1 else current_page - 1


async def on_arrow_right(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    data = dialog_manager.dialog_data
    current_page, pages_num = data.get("current_page"), data.get("pages_num")

    # If current page is the last page, go to the first page
    data["current_page"] = 1 if current_page == pages_num else current_page + 1


async def get_language_list(event_isolation, dialog_manager: DialogManager, i18n: I18nContext, *args, **kwargs):
    languages = []
    for language in Language.__members__.values():
        languages.append((i18n.get(language), language))

    return {
        "languages": languages
    }


async def on_language_selected(callback: CallbackQuery, widget: Any,
                               dialog_manager: DialogManager, item_id: str):
    language = item_id
    i18n: I18nContext = dialog_manager.middleware_data.get("i18n")

    await i18n.set_locale(language)
    logger.info("User id=%s chose language=%s", callback.from_user.id, language)
    await dialog_manager.start(MainMenu.show_list,
                               mode=StartMode.RESET_STACK,
                               show_mode=ShowMode.EDIT,
                               data={"tg_id": callback.from_user.id})


async def change_language(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(MainMenu.change_language, mode=StartMode.RESET_STACK, show_mode=ShowMode.EDIT)
    await message.delete()


async def add_movie(message: Message, dialog_manager: DialogManager, i18n: I18nContext):
    await dialog_manager.start(MainMenu.add_movie, mode=StartMode.RESET_STACK, show_mode=ShowMode.EDIT,
                               data={"tg_id": message.from_user.id,
                                     "message": message.text})
    await message.delete()


async def get_add_movies_list(event_isolation, dialog_manager: DialogManager, i18n: I18nContext, *args, **kwargs):
    dialog_manager.dialog_data["tg_id"] = dialog_manager.start_data["tg_id"]
    message = dialog_manager.start_data["message"]

    dialog_manager.dialog_data.setdefault("page_size", settings.PAGE_SIZE)
    dialog_manager.dialog_data.setdefault("current_page", 1)

    search = tmdb.Search()
    response = search.movie(query=message, language=i18n.locale)

    movies = []

    for movie in response['results']:
        movie_str = f"{movie['title']} {movie['vote_average']}"
        movies.append((movie_str, movie['id']))

    movies_num = len(movies)
    dialog_manager.dialog_data["pages_num"] = movies_num // settings.PAGE_SIZE

    page_size = dialog_manager.dialog_data["page_size"]
    current_page = dialog_manager.dialog_data["current_page"]

    start = (current_page - 1) * page_size
    end = start + page_size

    movies = movies[start:end]

    return {
        "movies": movies,
        "current_page": dialog_manager.dialog_data.get("current_page"),
        "pages_num": dialog_manager.dialog_data.get("pages_num")
    }


async def on_back(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.start(MainMenu.show_list,
                               mode=StartMode.RESET_STACK,
                               show_mode=ShowMode.EDIT,
                               data={"tg_id": callback.from_user.id})


main_menu = Dialog(
    # Show list of movies window
    Window(
        Multi(
            I18NFormat("show-movies",
                       when=~F["is_empty"]),
            I18NFormat("no-movies",
                       when=F["is_empty"])),
        Column(
            Select(
                Format("{item[0]}"),
                id="s_movies",
                item_id_getter=operator.itemgetter(1),
                items="movies_on_page",
                when=~F["is_empty"]
            )
        ),
        Row(
            Button(
                I18NFormat("arrow-left"),
                id="arrow_left",
                on_click=on_arrow_left
            ),
            Button(
                Format("{current_page} / {pages_num}",
                       when=~F["is_empty"]),
                id="page"
            ),
            Button(
                I18NFormat("arrow-right"),
                id="arrow_right",
                on_click=on_arrow_right
            ),
            when=~F["is_empty"]
        ),
        Row(
            Button(
                I18NFormat("get-description"),
                id="get_description",
            ),
            Button(
                I18NFormat("sorting", order="pass"),
                id="sorting",
                when=~F["is_empty"]
            )
        ),
        state=MainMenu.show_list,
        getter=get_movies_list
    ),
    # Change language window
    Window(
        I18NFormat("choose-language"),
        Select(
            Format("{item[0]}"),
            id="select_language",
            item_id_getter=lambda item: item[1],
            items="languages",
            on_click=on_language_selected
        ),
        state=MainMenu.change_language,
        getter=get_language_list
    ),
    # Add movie window
    Window(
        I18NFormat("choose-movie-to-add"),
        Column(
            Select(
                Format("{item[0]}"),
                id="s_movies_to_add",
                item_id_getter=lambda item: item[1],
                items="movies",
            ),
        ),
        Row(
            Button(
                I18NFormat("arrow-left"),
                id="arrow_left",
                on_click=on_arrow_left
            ),
            Button(
                Format("{current_page} / {pages_num}"),
                id="page"
            ),
            Button(
                I18NFormat("arrow-right"),
                id="arrow_right",
                on_click=on_arrow_right
            )
        ),
        Button(
            I18NFormat("go-back"),
            id="go_back",
            on_click=on_back
        ),
        state=MainMenu.add_movie,
        getter=get_add_movies_list
    )
)
