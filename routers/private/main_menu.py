import asyncio
import operator
import typing
from typing import Any
from datetime import datetime

import tmdbsimple as tmdb
from aiogram_dialog.api.entities import MediaAttachment, MediaId

from settings import settings

from aiogram import F
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import DialogManager, Dialog, Window, StartMode, ShowMode
from aiogram_dialog.widgets.text import Format, Multi, List, Const
from aiogram_dialog.widgets.kbd import Row, Button, Select, Column, Checkbox, ManagedCheckbox
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_i18n import I18nContext

from sqlalchemy.ext.asyncio import AsyncSession

from database.requests import db_get_users_movies, db_get_all_movies, db_add_movie_to_user, db_get_movie_added_time, \
    db_delete_movie_from_user, db_get_users_movie_data, db_change_movie_state, db_get_movie_state_for_user

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

    db_movies = await db_get_users_movies(session, tg_id)

    movies_num = len(db_movies)

    dialog_manager.dialog_data["pages_num"] = movies_num // settings.PAGE_SIZE if movies_num % settings.PAGE_SIZE == 0 \
        else movies_num // settings.PAGE_SIZE + 1

    is_empty = movies_num == 0
    is_movie_rate = dialog_manager.dialog_data.get("sorting_type") == SortingType.MOVIE_RATE
    is_descending = dialog_manager.dialog_data.get("sorting_order") == SortingOrder.DESCENDING

    movies_info = await fetch_movie_details(db_movies, i18n.locale, dialog_manager, session)
    movies_on_page = await make_list(movies_info, dialog_manager, i18n)

    return {
        "is_empty": is_empty,
        "movies_on_page": movies_on_page,
        "current_page": dialog_manager.dialog_data.get("current_page", 1),
        "pages_num": dialog_manager.dialog_data.get("pages_num", 1),
        "sorting_type": is_movie_rate,
        "sorting_order": is_descending
    }


async def sort_movies(movies, dialog_manager: DialogManager):
    sorting_type = dialog_manager.dialog_data.get("sorting_type")
    sorting_order = dialog_manager.dialog_data.get("sorting_order")
    sort_key = lambda movie: movie['vote_average']
    reverse = False

    if sorting_type == SortingType.MOVIE_RATE:
        sort_key = lambda movie: movie['vote_average']
    elif sorting_type == SortingType.LIKED_TIME:  # Assuming this is the constant for sorting by date
        sort_key = lambda movie: movie['added_at']

    if sorting_order == SortingOrder.DESCENDING:
        reverse = True

    movies.sort(key=sort_key, reverse=reverse)


async def fetch_movie_details(db_movies, language, dialog_manager: DialogManager, session: AsyncSession):
    movies_info = []
    for movie in db_movies:
        movie_id = movie.tmdb_id
        movie_info = tmdb.Movies(id=movie_id).info(language=language)
        added_at = await db_get_movie_added_time(session, dialog_manager.dialog_data.get("tg_id"), movie_id)
        movie_info['added_at'] = added_at
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


async def on_sorting_type(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    sorting_type = dialog_manager.dialog_data.get("sorting_type")

    dialog_manager.dialog_data["sorting_type"] = SortingType.LIKED_TIME if sorting_type == SortingType.MOVIE_RATE \
        else SortingType.MOVIE_RATE


async def on_sorting_order(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    sorting_order = dialog_manager.dialog_data.get("sorting_order")

    dialog_manager.dialog_data["sorting_order"] = SortingOrder.ASCENDING if sorting_order == SortingOrder.DESCENDING \
        else SortingOrder.DESCENDING


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


async def get_add_movies_list(event_isolation, dialog_manager: DialogManager, i18n: I18nContext,
                              session: AsyncSession, *args, **kwargs):
    dialog_manager.middleware_data["session"] = session
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
        "pages_num": dialog_manager.dialog_data.get("pages_num"),
        "is_empty": movies_num == 0
    }


async def on_back(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.start(MainMenu.show_list,
                               mode=StartMode.RESET_STACK,
                               show_mode=ShowMode.EDIT,
                               data={"tg_id": callback.from_user.id})


async def on_movie_to_add(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager, item_id: str):
    tg_id: int = callback.from_user.id
    session: AsyncSession = dialog_manager.middleware_data.get("session")
    tmdb_id = int(item_id)

    # Fetch movie details
    movie = tmdb.Movies(id=tmdb_id)
    movie_info = movie.info()

    # Create a dictionary with the movie data
    movie_data = {
        'tmdb_id': movie_info['id'],
        'movie_name': movie_info['title'],
        # Add other attributes here if needed
    }

    await db_add_movie_to_user(session, tg_id, movie_data)

    await dialog_manager.start(MainMenu.show_list,
                               mode=StartMode.RESET_STACK,
                               show_mode=ShowMode.EDIT,
                               data={"tg_id": callback.from_user.id})


async def on_movie_details(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager, item_id: str):

    await dialog_manager.start(
        MainMenu.show_details,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.EDIT,
        data={"movie_id": item_id,
              "tg_id": callback.from_user.id}
    )


async def on_delete(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    tg_id = callback.from_user.id
    session = dialog_manager.middleware_data.get("session")
    movie_id = dialog_manager.start_data["movie_id"]

    await db_delete_movie_from_user(session, tg_id, movie_id)

    await dialog_manager.start(MainMenu.show_list,
                               mode=StartMode.RESET_STACK,
                               show_mode=ShowMode.EDIT,
                               data={"tg_id": tg_id})


async def on_state_changed(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    tg_id = callback.from_user.id
    session = dialog_manager.middleware_data.get("session")
    movie_id = dialog_manager.start_data["movie_id"]
    is_watched = await db_get_movie_state_for_user(session, tg_id, movie_id)

    await db_change_movie_state(session, tg_id, movie_id, is_watched)

    if not is_watched:
        await dialog_manager.start(MainMenu.ask_to_leave_review,
                                   mode=StartMode.RESET_STACK,
                                   show_mode=ShowMode.EDIT,
                                   data={"movie_id": movie_id})
    else:
        await dialog_manager.start(MainMenu.show_details,
                                   mode=StartMode.RESET_STACK,
                                   show_mode=ShowMode.EDIT,
                                   data={"movie_id": movie_id,
                                         "tg_id": tg_id})


async def get_movie_details(event_isolation, dialog_manager: DialogManager, session: AsyncSession, i18n: I18nContext,
                            *args, **kwargs):
    #await asyncio.sleep(0.1)

    movie_id = dialog_manager.start_data["movie_id"]
    tg_id = dialog_manager.start_data["tg_id"]
    movie = tmdb.Movies(id=movie_id).info(language=i18n.locale)

    users_movie_info = await db_get_users_movie_data(session, tg_id, movie_id)

    countries = [country['iso_3166_1'] for country in movie['production_countries']]

    movie_title = f"🎬 {i18n.get('movie-title')} <b>{movie['title']}</b>"
    original_movie_title = f"<b>({movie['original_title']})</b>" \
        if movie['original_language'] != i18n.locale else ''

    release_date = (f"📅 {i18n.get('release-date')} "
                    f"<b>{datetime.strptime(movie['release_date'], '%Y-%m-%d').strftime('%d.%m.%Y')}, "
                    f"{', '.join(countries)}</b>\n\n") \
        if movie['release_date'] else ''
    genres = f"🎭 {i18n.get('genres')} <b>{', '.join([genre['name'] for genre in movie['genres']])}</b>\n\n" \
        if movie['genres'] else ''
    tagline = f"📝 {i18n.get('tagline')} <b>{movie['tagline']}</b>\n\n" \
        if movie['tagline'] else ''
    runtime = f"🕒 {i18n.get('runtime')} <b>{movie['runtime']} {i18n.get('minutes')}</b>\n\n" \
        if movie['runtime'] else ''
    overview = f"📄 {i18n.get('overview')} <b>{movie['overview']}</b>\n\n" \
        if movie['overview'] else ''
    rating = f"⭐️ {i18n.get('rating')} <b>{movie['vote_average']}</b>\n\n" \
        if movie['vote_average'] else ''
    adult = f"🔞 <b>{i18n.get('adult')}</b>\n\n" \
        if movie['adult'] else ''

    movie_info = (f"{movie_title} {original_movie_title}\n\n"
                  f"{rating}"
                  f"{release_date}"
                  f"{adult}"
                  f"{genres}"
                  f"{runtime}"
                  f"{tagline}"
                  f"{overview}"
                  )

    poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
    is_poster = movie['poster_path'] is not None

    return {
        "movie_info": movie_info,
        "is_poster": is_poster,
        "poster": MediaAttachment(ContentType.PHOTO,
                                  url=poster_url),
        "is_watched": users_movie_info["is_watched"]
    }


async def get_rating_keyboard(event_isolation, *args, **kwargs):
    buttons = []
    for i in range(1, 11):
        buttons.append((str(i), i))

    return {"buttons": buttons}


async def on_add_review(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    pass
    #await dialog_manager.start(MainMenu.leave_rating, )


async def on_chosen_rating(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager, item_id: str):
    dialog_manager.dialog_data["rating"] = item_id


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
                item_id_getter=lambda item: item[1],
                items="movies_on_page",
                when=~F["is_empty"],
                on_click=on_movie_details
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
                Multi(
                    I18NFormat("sorting-rate", when=F["sorting_type"]),
                    I18NFormat("sorting-date", when=~F["sorting_type"]),
                ),
                id="sorting_type",
                on_click=on_sorting_type,
                when=~F["is_empty"]
            ),
            Button(
                Multi(
                    I18NFormat("order-asc", when=~F["sorting_order"] & F["sorting_type"]),
                    I18NFormat("order-desc", when=F["sorting_order"] & F["sorting_type"]),
                    I18NFormat("last-added", when=F["sorting_order"] & ~F["sorting_type"]),
                    I18NFormat("first-added", when=~F["sorting_order"] & ~F["sorting_type"]),
                ),
                id="sorting_order",
                on_click=on_sorting_order,
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
        I18NFormat("choose-movie-to-add", when=~F["is_empty"]),
        I18NFormat("no-movies-found", when=F["is_empty"]),
        Column(
            Select(
                Format("{item[0]}"),
                id="s_movies_to_add",
                item_id_getter=lambda item: item[1],
                items="movies",
                on_click=on_movie_to_add,
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
                Format("{current_page} / {pages_num}"),
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
            I18NFormat("go-back"),
            id="go_back",
            on_click=on_back
        ),
        state=MainMenu.add_movie,
        getter=get_add_movies_list
    ),
    # Movie details window
    Window(
        Format("{movie_info}"),
        Button(
            I18NFormat("delete-movie"),
            id="delete_movie",
            on_click=on_delete
        ),
        Button(
            I18NFormat("go-back"),
            id="go_back",
            on_click=on_back
        ),
        Button(
            Multi(
                I18NFormat("movie-is-watched",
                           when=F["is_watched"]),
                I18NFormat("movie-not-watched",
                           when=~F["is_watched"]),
            ),
            id="is_watched",
            on_click=on_state_changed

        ),
        DynamicMedia("poster",
                     when=F["is_poster"]),

        state=MainMenu.show_details,
        getter=get_movie_details
    ),
    # ask user to leave review window
    Window(
        I18NFormat("leave-review"),
        Row(
            Button(
                I18NFormat("yes"),
                id="yes",
                on_click=on_add_review
            ),
            Button(
                I18NFormat("no"),
                id="no",
                on_click=on_back
            )
        ),
        state=MainMenu.ask_to_leave_review
    ),
    # choose rating window
    Window(
        I18NFormat("how-would-rate"),
        Row(
            Select(
                Format("{item[0]}"),
                id="rating",

                on_click=on_chosen_rating
            ),
        ),
        state=MainMenu.leave_rating,
        getter=get_rating_keyboard
    ),
    # leave review window
    Window(
        I18NFormat("leave-review"),
        Button(
            I18NFormat("go-back"),
            id="go_back",
            on_click=on_back
        ),
        state=MainMenu.leave_review
    )
)

