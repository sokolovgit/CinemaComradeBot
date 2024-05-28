import random
import typing
from asyncio import sleep
from math import floor
from typing import Any
from datetime import datetime

import tmdbsimple as tmdb
from aiogram.fsm.context import FSMContext
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.input import MessageInput

from commands import set_bot_commands
from settings import settings

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import DialogManager, Dialog, Window, StartMode, ShowMode
from aiogram_dialog.widgets.text import Format, Multi
from aiogram_dialog.widgets.kbd import Row, Button, Select, Column
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_i18n import I18nContext

from sqlalchemy.ext.asyncio import AsyncSession

from database.requests import db_get_users_movies, db_add_movie_to_user, db_get_movie_added_time, \
    db_delete_movie_from_user, db_get_users_movie_data, db_change_movie_state, db_get_movie_state_for_user, \
    db_leave_review

from utils.logger import setup_logger
from utils.i18n_format import I18NFormat

from states.main_menu import MainMenu

from enums.language import Language
from enums.sorting import SortingType, SortingOrder


logger = setup_logger()
tmdb.API_KEY = settings.TMDB_API_KEY.get_secret_value()


async def get_movies_list(event_isolation, dialog_manager: DialogManager,
                          session: AsyncSession, i18n: I18nContext, *args, **kwargs):
    """
    Asynchronously fetches the list of movies for the user.

    :param event_isolation: Isolation level for the event.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :param session: Database session.
    :param i18n: I18nContext instance for localization.
    :param args: Additional arguments.
    :param kwargs: Additional keyword arguments.
    :return: Dictionary containing information about the movies.
    """
    dialog_manager.dialog_data.setdefault("page_size", settings.PAGE_SIZE)
    dialog_manager.dialog_data.setdefault("current_page", 1)
    dialog_manager.dialog_data.setdefault("sorting_type", SortingType.MOVIE_RATE)
    dialog_manager.dialog_data.setdefault("sorting_order", SortingOrder.DESCENDING)

    tg_id = dialog_manager.middleware_data.get("event_from_user").id

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
    """
    Asynchronously sorts a list of movies based on the sorting type and order specified in the dialog manager's data.

    :param movies: List of dictionaries where each dictionary represents a movie.
    :param dialog_manager: DialogManager instance to manage the dialog.
    """
    sorting_type = dialog_manager.dialog_data.get("sorting_type")
    sorting_order = dialog_manager.dialog_data.get("sorting_order")
    sort_key = lambda movie: movie['vote_average']
    reverse = False

    if sorting_type == SortingType.MOVIE_RATE:
        sort_key = lambda movie: movie['vote_average']
    elif sorting_type == SortingType.LIKED_TIME:
        sort_key = lambda movie: movie['added_at']

    if sorting_order == SortingOrder.DESCENDING:
        reverse = True

    movies.sort(key=sort_key, reverse=reverse)


async def fetch_movie_details(db_movies, language, dialog_manager: DialogManager, session: AsyncSession):
    movies_info = []
    for movie in db_movies:
        movie_id = movie.tmdb_id
        movie_info = tmdb.Movies(id=movie_id).info(language=language)
        added_at = await db_get_movie_added_time(session, dialog_manager.middleware_data.get("event_from_user").id, movie_id)
        movie_info['added_at'] = added_at
        movies_info.append(movie_info)

    await sort_movies(movies_info, dialog_manager)

    return movies_info


async def make_list(movies_info: typing.List[dict], dialog_manager: DialogManager, i18n: I18nContext):
    """
    Asynchronously creates a list of movies to display in the dialog.

    :param movies_info: List of dictionaries where each dictionary represents a movie.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :param i18n: I18nContext instance for localization.
    :return: List of movies to be displayed.
    """
    page_size = dialog_manager.dialog_data["page_size"]
    current_page = dialog_manager.dialog_data["current_page"]

    movies_num = len(movies_info)

    start = (current_page - 1) * page_size
    end = start + page_size

    movie_list = []
    for i in range(start, min(end, movies_num)):
        movie = movies_info[i]

        movie_str = f"{movie['title']} {movie['release_date'][0:4]}, {int(movie['vote_average'])} ⭐️"
        movie_list.append((movie_str, movie['id']))

    return movie_list


async def on_arrow_left(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """
    Handles the event when the left arrow button is clicked.

    :param callback: CallbackQuery instance representing the callback query.
    :param button: Button instance representing the clicked button.
    :param dialog_manager: DialogManager instance to manage the dialog.
    """
    data = dialog_manager.dialog_data
    current_page, pages_num = data.get("current_page"), data.get("pages_num")

    data["current_page"] = pages_num if current_page == 1 else current_page - 1


async def on_arrow_right(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """
    Handles the event when the right arrow button is clicked.

    :param callback: CallbackQuery instance representing the callback query.
    :param button: Button instance representing the clicked button.
    :param dialog_manager: DialogManager instance to manage the dialog.
    """
    data = dialog_manager.dialog_data
    current_page, pages_num = data.get("current_page"), data.get("pages_num")

    data["current_page"] = 1 if current_page == pages_num else current_page + 1


async def on_sorting_type(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """
    Handles the event when the sorting type button is clicked.

    :param callback: CallbackQuery instance representing the callback query.
    :param button: Button instance representing the clicked button.
    :param dialog_manager: DialogManager instance to manage the dialog.
    """
    sorting_type = dialog_manager.dialog_data.get("sorting_type")

    dialog_manager.dialog_data["sorting_type"] = SortingType.LIKED_TIME if sorting_type == SortingType.MOVIE_RATE \
        else SortingType.MOVIE_RATE


async def on_sorting_order(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """
    Handles the event when the sorting order button is clicked.

    :param callback: CallbackQuery instance representing the callback query.
    :param button: Button instance representing the clicked button.
    :param dialog_manager: DialogManager instance to manage the dialog.
    """

    sorting_order = dialog_manager.dialog_data.get("sorting_order")

    dialog_manager.dialog_data["sorting_order"] = SortingOrder.ASCENDING if sorting_order == SortingOrder.DESCENDING \
        else SortingOrder.DESCENDING


async def get_language_list(event_isolation, dialog_manager: DialogManager, i18n: I18nContext, *args, **kwargs):
    """
    Fetches the list of available languages.

    :param event_isolation: Isolation level for the event.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :param i18n: I18nContext instance for localization.
    :param args: Additional arguments.
    :param kwargs: Additional keyword arguments.
    :return: Dictionary containing information about the languages.
    """
    languages = []
    for language in Language.__members__.values():
        languages.append((i18n.get(language), language))

    return {
        "languages": languages
    }


async def on_language_selected(callback: CallbackQuery, widget: Any,
                               dialog_manager: DialogManager, item_id: str):
    """
    Handles the event when a language is selected.

    :param callback: CallbackQuery instance representing the callback query.
    :param widget: Widget instance representing the clicked widget.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :param item_id: ID of the selected item.
    """
    language = item_id
    i18n: I18nContext = dialog_manager.middleware_data.get("i18n")

    await i18n.set_locale(language)
    logger.info("User id=%s chose language=%s", callback.from_user.id, language)
    await set_bot_commands(callback.bot, i18n)

    await dialog_manager.start(MainMenu.show_list,
                               mode=StartMode.RESET_STACK,
                               show_mode=ShowMode.EDIT,
                               data={"tg_id": callback.from_user.id})


async def change_language(message: Message, dialog_manager: DialogManager):
    """
    Starts the language change dialog.

    :param message: Message instance representing the received message.
    :param dialog_manager: DialogManager instance to manage the dialog.
    """
    await dialog_manager.start(MainMenu.change_language, mode=StartMode.RESET_STACK, show_mode=ShowMode.EDIT)
    await message.delete()


async def add_movie(message: Message, dialog_manager: DialogManager, i18n: I18nContext, state: FSMContext):
    """
    Starts the add movie dialog.

    :param message: Message instance representing the received message.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :param i18n: I18nContext instance for localization.
    :param state: FSMContext instance representing the current state.
    """
    await dialog_manager.start(MainMenu.add_movie, mode=StartMode.RESET_STACK, show_mode=ShowMode.EDIT,
                               data={"tg_id": message.from_user.id,
                                     "message": message.text})

    await message.delete()


async def get_add_movies_list(event_isolation, dialog_manager: DialogManager, i18n: I18nContext,
                              session: AsyncSession, *args, **kwargs):
    """
    Asynchronously fetches a list of movies to add based on the user's input.

    :param event_isolation: Isolation level for the event.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :param i18n: I18nContext instance for localization.
    :param session: Database session.
    :param args: Additional arguments.
    :param kwargs: Additional keyword arguments.
    :return: Dictionary containing information about the movies.
    """
    dialog_manager.dialog_data["tg_id"] = dialog_manager.start_data["tg_id"]
    message = dialog_manager.start_data["message"]

    dialog_manager.dialog_data.setdefault("page_size", settings.PAGE_SIZE)
    dialog_manager.dialog_data.setdefault("current_page", 1)

    search = tmdb.Search()
    response = search.movie(query=message, language=i18n.locale)

    movies = []

    for movie in response['results']:
        if movie['vote_average'] > 0:
            movie_str = f"{movie['title']} {movie['release_date'][0:4]}, {int(movie['vote_average'])} ⭐️"
            movies.append((movie_str, movie['id']))

    movies_num = len(movies)
    page_size = dialog_manager.dialog_data["page_size"]
    dialog_manager.dialog_data["pages_num"] = movies_num // page_size if movies_num % page_size == 0 else movies_num // page_size + 1

    current_page = dialog_manager.dialog_data["current_page"]

    start = (current_page - 1) * page_size
    end = min((start + page_size), movies_num)

    movies = movies[start:end]

    return {
        "movies": movies,
        "current_page": dialog_manager.dialog_data.get("current_page"),
        "pages_num": dialog_manager.dialog_data.get("pages_num"),
        "is_empty": movies_num == 0
    }


async def on_back(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """
    Handles the event when the back button is clicked.

    :param callback: CallbackQuery instance representing the callback query.
    :param button: Button instance representing the clicked button.
    :param dialog_manager: DialogManager instance to manage the dialog.
    """
    await dialog_manager.start(MainMenu.show_list,
                               mode=StartMode.RESET_STACK,
                               show_mode=ShowMode.EDIT,
                               data={"tg_id": callback.from_user.id})


async def on_back_to_movie(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """
    Handles the event when the back button is clicked in the movie details view.

    :param callback: CallbackQuery instance representing the callback query.
    :param button: Button instance representing the clicked button.
    :param dialog_manager: DialogManager instance to manage the dialog.
    """
    await dialog_manager.start(MainMenu.show_details,
                               mode=StartMode.RESET_STACK,
                               show_mode=ShowMode.EDIT,
                               data={"movie_id": dialog_manager.start_data["movie_id"],
                                     "tg_id": callback.from_user.id
                                     }
                               )


async def on_movie_to_add(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager, item_id: str):
    """
    Handles the event when a movie is selected to be added from the search results.

    :param callback: CallbackQuery instance representing the callback query.
    :param widget: widget instance representing the clicked widget.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :param item_id: str representing id on the selected item.
    :return:
    """
    await dialog_manager.start(MainMenu.show_details,
                               mode=StartMode.RESET_STACK,
                               show_mode=ShowMode.EDIT,
                               data={"movie_id": item_id,
                                     "tg_id": callback.from_user.id}
                               )


async def on_movie_details(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager, item_id: str):
    """
    Handles the event when a movie is selected to show details.

    :param callback: CallbackQuery instance representing the callback query.
    :param widget: widget instance representing the clicked widget.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :param item_id: str representing id on the selected item.
    :return:
    """
    await dialog_manager.start(MainMenu.show_details,
                               mode=StartMode.RESET_STACK,
                               show_mode=ShowMode.EDIT,
                               data={"movie_id": item_id,
                                     "tg_id": callback.from_user.id}
                               )


async def on_delete(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """
    Handles the event when the delete button is clicked in the movie details view.

    :param callback: CallbackQuery instance representing the callback query.
    :param button: Button instance representing the clicked button.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :return:
    """
    tg_id = callback.from_user.id
    session = dialog_manager.middleware_data.get("session")
    movie_id = dialog_manager.start_data["movie_id"]

    await db_delete_movie_from_user(session, tg_id, movie_id)

    await dialog_manager.start(MainMenu.show_list,
                               mode=StartMode.RESET_STACK,
                               show_mode=ShowMode.EDIT,
                               )


async def on_state_changed(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """
    Handles the event when the state button is clicked in the movie details view.

    :param callback: CallbackQuery instance representing the callback query.
    :param button: Button instance representing the clicked button.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :return:
    """
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
                                   data={"movie_id": movie_id}
                                   )


async def get_movie_details(event_isolation, dialog_manager: DialogManager, session: AsyncSession, i18n: I18nContext,
                            *args, **kwargs):
    """
    Asynchronously fetches the details of a movie.

    :param event_isolation: Isolation level for the event.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :param session: Database session.
    :param i18n: I18nContext instance for localization.
    :param args:
    :param kwargs:
    :return: Dictionary containing information about the movie.
    """
    movie_id = dialog_manager.start_data["movie_id"]
    tg_id = dialog_manager.middleware_data.get("event_from_user").id
    movie = tmdb.Movies(id=movie_id).info(language=i18n.locale)

    users_movie_info = await db_get_users_movie_data(session, tg_id, movie_id)

    countries = [country['iso_3166_1'] for country in movie['production_countries']]

    movie_title = f"🎬 {i18n.get('movie-title')} <b>{movie['title']}</b>"
    original_movie_title = f"<b>({movie['original_title']})</b>" \
        if movie['original_language'] != i18n.locale else ''

    rating = f"⭐️ {i18n.get('rating')} <b>{movie['vote_average']}</b>\n\n" \
        if movie['vote_average'] else ''
    release_date = (f"📅 {i18n.get('release-date')} "
                    f"<b>{datetime.strptime(movie['release_date'], '%Y-%m-%d').strftime('%d.%m.%Y')}, "
                    f"{', '.join(countries)}</b>\n\n") \
        if movie['release_date'] else ''
    adult = f"🔞 <b>{i18n.get('adult')}</b>\n\n" \
        if movie['adult'] else ''
    genres = f"🎭 {i18n.get('genres')} <b>{', '.join([genre['name'] for genre in movie['genres']])}</b>\n\n" \
        if movie['genres'] else ''
    runtime = f"🕒 {i18n.get('runtime')} <b>{movie['runtime']} {i18n.get('minutes')}</b>\n\n" \
        if movie['runtime'] else ''
    tagline = f"📝 {i18n.get('tagline')} <b>{movie['tagline']}</b>\n\n" \
        if movie['tagline'] else ''
    overview = f"📄 {i18n.get('overview')} <b>{movie['overview']}</b>\n\n" \
        if movie['overview'] else ''
    personal_overview = (f"{'~' * 25}\n"
                         f"{i18n.get('personal-rating')} <b>{str(users_movie_info['personal_rating']) + ' ⭐' if users_movie_info['personal_rating'] is not None else i18n.get('no-personal-rating')}️</b>\n" 
                         f"{i18n.get('personal-overview')} <b>{users_movie_info['personal_review'] if users_movie_info['personal_review'] is not None else i18n.get('no-personal-review')}</b>\n"
                         ) if users_movie_info['is_watched'] else ''

    movie_info = (f"{movie_title} {original_movie_title}\n\n"
                  f"{rating}"
                  f"{release_date}"
                  f"{adult}"
                  f"{genres}"
                  f"{runtime}"
                  f"{tagline}"
                  f"{overview}"
                  f"{personal_overview}"
                  )

    poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
    is_poster = movie['poster_path'] is not None

    return {
        "movie_info": movie_info,
        "is_poster": is_poster,
        "poster": MediaAttachment(ContentType.PHOTO,
                                  url=poster_url),
        "is_watched": users_movie_info["is_watched"],
        "in_database": users_movie_info["in_database"]
    }


async def get_rating_keyboard(event_isolation, *args, **kwargs):
    """
    Asynchronously fetches the rating keyboard.

    :param event_isolation: Isolation level for the event.
    :param args:
    :param kwargs:
    :return:
    """
    buttons = []
    for i in range(1, 11):
        buttons.append((str(i), i))

    return {"first_row_buttons": buttons[:5],
            "second_row_buttons": buttons[5:]}


async def on_add_review(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """
    Handles the event when the add review button is clicked in the movie details view.

    :param callback: CallbackQuery instance representing the callback query.
    :param button: Button instance representing the clicked button.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :return:
    """
    await dialog_manager.start(MainMenu.leave_rating,
                               show_mode=ShowMode.EDIT,
                               data={"movie_id": dialog_manager.start_data["movie_id"]}
                               )


async def on_chosen_rating(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager, item_id: str):
    """
    Handles the event when a rating is chosen.

    :param callback: CallbackQuery instance representing the callback query.
    :param widget: Widget instance representing the clicked widget.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :param item_id: str representing id on the selected item.
    :return:
    """
    data = {"rating": item_id,
            "movie_id": dialog_manager.start_data["movie_id"],
            }
    session = dialog_manager.middleware_data.get("session")

    await db_leave_review(session, callback.from_user.id, data["movie_id"], {"rating": item_id, "review": None})
    dialog_manager.dialog_data.update(data)

    await dialog_manager.next()


async def get_users_review(message: Message,  message_input: MessageInput, dialog_manager: DialogManager):
    """
    Asynchronously fetches the user's review.

    :param message: Message instance representing the received message.
    :param message_input: MessageInput instance representing the received message input.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :return:
    """
    rating = dialog_manager.dialog_data["rating"]
    movie_id = dialog_manager.dialog_data["movie_id"]
    session = dialog_manager.middleware_data.get("session")
    review = message.text

    if len(review) > 150:
        i18n = dialog_manager.middleware_data.get("i18n")
        bot_message = await message.answer(i18n.get("error-limit"))
        await sleep(5)
        await bot_message.delete()
        await message.delete()
        return await dialog_manager.switch_to(MainMenu.leave_review, show_mode=ShowMode.EDIT)

    data = {
        "rating": rating,
        "review": review
    }

    await db_leave_review(session, message.from_user.id, movie_id, data)
    await dialog_manager.switch_to(MainMenu.show_details, show_mode=ShowMode.EDIT)
    await message.delete()


async def movie_name_input(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    """
    Asynchronously handles the movie name input.

    :param message: Message instance representing the received message.
    :param message_input: MessageInput instance representing the received message input.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :return:
    """
    await dialog_manager.start(MainMenu.add_movie, mode=StartMode.RESET_STACK, show_mode=ShowMode.EDIT,
                               data={"tg_id": message.from_user.id,
                                     "message": message.text})

    await message.delete()


async def show_random_movie(message: Message, dialog_manager: DialogManager):
    """
    Asynchronously shows a random movie from the user's list.

    :param message: Message instance representing the received message.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :return:
    """
    await message.delete()

    session = dialog_manager.middleware_data.get("session")
    tg_id = message.from_user.id
    db_movies = await db_get_users_movies(session, tg_id)

    unwatched_movies = []
    for movie in db_movies:
        is_watched = await db_get_movie_state_for_user(session, tg_id, movie.tmdb_id)
        if not is_watched:
            unwatched_movies.append(movie)

    if not unwatched_movies:
        await dialog_manager.start(MainMenu.all_movies_watched, show_mode=ShowMode.EDIT)
        return

    random_movie = random.choice(unwatched_movies)

    await dialog_manager.start(MainMenu.show_details,
                               mode=StartMode.RESET_STACK,
                               show_mode=ShowMode.EDIT,
                               data={"movie_id": random_movie.tmdb_id,
                                     "tg_id": tg_id}
                               )


async def genres_command(message: Message, dialog_manager: DialogManager):
    """
    Starts the genre selection dialog.

    :param message: Message instance representing the received message.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :return:
    """
    await message.delete()
    await dialog_manager.start(MainMenu.choose_genre, mode=StartMode.RESET_STACK, show_mode=ShowMode.EDIT)


async def on_genre_selected(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager, item_id: str):
    """
    Handles the event when a genre is selected.

    :param callback: CallbackQuery instance representing the callback query.
    :param widget: Widget instance representing the clicked widget.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :param item_id: str representing id on the selected item.
    :return:
    """
    selected_genres = dialog_manager.dialog_data.get("selected_genres", [])
    i18n = dialog_manager.middleware_data.get("i18n")

    if item_id in selected_genres:
        selected_genres.remove(item_id)
        dialog_manager.dialog_data["selected_genres"] = selected_genres
        return

    elif len(selected_genres) >= settings.MAX_GENRES:
        message = await callback.bot.send_message(chat_id=callback.message.chat.id,
                                                  text=i18n.get("error-genres"))
        await sleep(5)
        await message.delete()
        return

    selected_genres.append(item_id)
    dialog_manager.dialog_data["selected_genres"] = selected_genres


async def get_genres_list(event_isolation, dialog_manager: DialogManager, i18n: I18nContext, *args, **kwargs):
    """
    Asynchronously fetches the list of genres.

    :param event_isolation: Isolation level for the event.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :param i18n: I18nContext instance for localization.
    :param args:
    :param kwargs:
    :return:
    """
    tmdb_genres = tmdb.Genres().movie_list(language=i18n.locale)['genres']
    genres = []
    selected_genres = dialog_manager.dialog_data.get("selected_genres", [])

    for genre in tmdb_genres:
        name = genre["name"]
        if str(genre["id"]) in selected_genres:
            name += " ✅"

        genres.append((genre["id"], name))

    return {
        "genres1": genres[:4],
        "genres2": genres[4:8],
        "genres3": genres[8:12],
        "genres4": genres[12:16],
        "genres5": genres[16:],
    }


async def on_find_movies(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """
    Handles the event when the find movies button is clicked.

    :param callback: CallbackQuery instance representing the callback query.
    :param button: Button instance representing the clicked button.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :return:
    """
    await dialog_manager.next()


async def get_found_movies(event_isolation, dialog_manager: DialogManager, i18n: I18nContext, *args, **kwargs):
    """
    Asynchronously fetches the list of movies based on the selected genres.

    :param event_isolation: Isolation level for the event.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :param i18n: I18nContext instance for localization.
    :param args:
    :param kwargs:
    :return:
    """
    dialog_manager.dialog_data.setdefault("page_size", settings.PAGE_SIZE)
    dialog_manager.dialog_data.setdefault("current_page", 1)

    genres = ','.join(dialog_manager.dialog_data.get("selected_genres", []))
    movies = []

    for page in range(1, 3):
        response: dict = tmdb.Discover().movie(with_genres=genres,
                                               language=i18n.locale,
                                               sort_by="vote_average.desc",
                                               vote_count_gte=100,
                                               page=page)

        for movie in response['results']:
            movie_str = f"{movie['title']} {movie['release_date'][0:4]}, {int(movie['vote_average'])} ⭐️"
            movies.append((movie_str, movie['id']))

    movies_num = len(movies)
    page_size = dialog_manager.dialog_data["page_size"]
    dialog_manager.dialog_data[
        "pages_num"] = movies_num // page_size if movies_num % page_size == 0 else movies_num // page_size + 1

    current_page = dialog_manager.dialog_data["current_page"]

    start = (current_page - 1) * page_size
    end = min((start + page_size), movies_num)

    movies = movies[start:end]

    return {
        "movies": movies,
        "current_page": dialog_manager.dialog_data.get("current_page"),
        "pages_num": dialog_manager.dialog_data.get("pages_num"),
        "is_empty": movies_num == 0
    }


async def on_found_movie(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager, item_id: str):
    """
    Handles the event when a movie is selected to be added from the found movies list.

    :param callback: CallbackQuery instance representing the callback query.
    :param button: Button instance representing the clicked button.
    :param dialog_manager: DialogManager instance to manage the dialog.
    """
    await dialog_manager.start(MainMenu.show_details,
                               mode=StartMode.RESET_STACK,
                               show_mode=ShowMode.EDIT,
                               data={"movie_id": item_id,
                                     "tg_id": callback.from_user.id}
                               )


async def on_back_to_genres(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """
    Handles the event when the back button is clicked in the genre selection view.

    :param callback: CallbackQuery instance representing the callback query.
    :param button: Button instance representing the clicked button.
    :param dialog_manager: DialogManager instance to manage the dialog.
    """
    await dialog_manager.start(MainMenu.choose_genre, mode=StartMode.RESET_STACK, show_mode=ShowMode.EDIT)


async def on_found_movie_to_add(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """
    Handles the event when the add movie button is clicked in the movie details view.

    :param callback: CallbackQuery instance representing the callback query.
    :param button: Button instance representing the clicked button.
    :param dialog_manager: DialogManager instance to manage the dialog.
    :return:
    """
    tg_id = callback.from_user.id
    session = dialog_manager.middleware_data.get("session")
    tmdb_id = int(dialog_manager.start_data["movie_id"])

    movie = tmdb.Movies(id=tmdb_id).info()

    movie_data = {
        'tmdb_id': movie['id'],
        'movie_name': movie['title'],
    }

    await db_add_movie_to_user(session, tg_id, movie_data)


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
        MessageInput(
            func=movie_name_input,
            content_types=[ContentType.TEXT],
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
            on_click=on_delete,
            when=F["in_database"]
        ),
        Button(
            I18NFormat("go-back"),
            id="go_back",
            on_click=on_back
        ),
        Button(
            I18NFormat("add-movie"),
            id="add_found_movie",
            on_click=on_found_movie_to_add,
            when=~F["in_database"]
        ),
        Button(
            Multi(
                I18NFormat("movie-is-watched",
                           when=F["is_watched"]),
                I18NFormat("movie-not-watched",
                           when=~F["is_watched"]),
            ),
            id="is_watched",
            on_click=on_state_changed,
            when=F["in_database"]
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
                on_click=on_back_to_movie
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
                item_id_getter=lambda item: item[1],
                items="first_row_buttons",
                on_click=on_chosen_rating
            ),
        ),
        Row(
            Select(
                Format("{item[0]}"),
                id="rating",
                item_id_getter=lambda item: item[1],
                items="second_row_buttons",
                on_click=on_chosen_rating
            ),
        ),
        state=MainMenu.leave_rating,
        getter=get_rating_keyboard
    ),
    # leave review window
    Window(
        I18NFormat("enter-review"),
        Button(
            I18NFormat("go-back"),
            id="go_back",
            on_click=on_back_to_movie
        ),
        MessageInput(
            get_users_review,
            content_types=[ContentType.TEXT],
        ),
        state=MainMenu.leave_review
    ),
    # you have watched all movies window
    Window(
        I18NFormat("all-movies-watched-error"),
        Button(
            I18NFormat("go-back"),
            id="go_back",
            on_click=on_back
        ),
        state=MainMenu.all_movies_watched
    ),
    # window for choosing genre for reccomendation movie
    Window(
        I18NFormat("choose-genre"),
        Row(
            Select(
                Format("{item[1]}"),
                id="genre",
                item_id_getter=lambda item: item[0],
                items="genres1",
                on_click=on_genre_selected
            ),
        ),
        Row(
            Select(
                Format("{item[1]}"),
                id="genre",
                item_id_getter=lambda item: item[0],
                items="genres2",
                on_click=on_genre_selected
            ),
        ),
        Row(
            Select(
                Format("{item[1]}"),
                id="genre",
                item_id_getter=lambda item: item[0],
                items="genres3",
                on_click=on_genre_selected
            ),
        ),
        Row(
            Select(
                Format("{item[1]}"),
                id="genre",
                item_id_getter=lambda item: item[0],
                items="genres4",
                on_click=on_genre_selected
            ),
        ),
        Row(
            Select(
                Format("{item[1]}"),
                id="genre",
                item_id_getter=lambda item: item[0],
                items="genres5",
                on_click=on_genre_selected
            ),
        ),
        Button(
            I18NFormat("show-movies-with-genres"),
            id="movies_with_genres",
            on_click=on_find_movies,
        ),
        Button(
            I18NFormat("go-back"),
            id="go_back",
            on_click=on_back
        ),
        state=MainMenu.choose_genre,
        getter=get_genres_list
    ),
    # found movies window
    Window(
        I18NFormat("found-movies", when=~F["is_empty"]),
        I18NFormat("no-found-movies", when=F["is_empty"]),
        Column(
            Select(
                Format("{item[0]}"),
                id="s_found_movie",
                item_id_getter=lambda item: item[1],
                items="movies",
                on_click=on_found_movie,
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
            id="go_back_genres",
            on_click=on_back_to_genres
        ),
        state=MainMenu.show_found_movies,
        getter=get_found_movies
    ),
)
