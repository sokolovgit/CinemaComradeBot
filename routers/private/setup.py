from aiogram import F

from aiogram.types import Message, CallbackQuery
from aiogram.methods import EditMessageText
from aiogram_dialog import Dialog, Window, DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import Row, Button, Group, Cancel, Start
from aiogram_i18n import I18nContext

from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.main_keyboard import main_keyboard
from settings import settings

from enums.language import Language
from enums.sorting import SortingType, SortingOrder
from states.change_language import ChangeLanguage
from states.main_menu import MainMenu
from utils.i18n_format import I18NFormat
from utils.logger import setup_logger
from database.requests import db_add_user


logger = setup_logger()


async def start_language(message: Message, i18n: I18nContext,
                         dialog_manager: DialogManager, session: AsyncSession):
    tg_id = message.from_user.id
    data = {
        "tg_id": tg_id,
        "user_name": f"{message.from_user.first_name} {message.from_user.last_name}",
    }

    try:
        await db_add_user(session, data)
    except Exception as e:
        print(f"Error = {e}.")

    if message.from_user.language_code in Language.__members__.values():
        language = message.from_user.language_code
        await i18n.set_locale(language)
        logger.info("User id=%s set to default language=%s", message.from_user.id, language)

    user_start_command = message
    greeting_message = await message.answer("Hello! I am a bot that will help you to "
                                            "keep track of the movies you have watched. ",
                                            )
    await user_start_command.delete()
    await dialog_manager.start(ChangeLanguage.change_language,
                               show_mode=ShowMode.DELETE_AND_SEND,
                               )


async def language_clicked(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    language = button.widget_id
    i18n: I18nContext = dialog_manager.middleware_data.get("i18n")

    await i18n.set_locale(language)
    logger.info("User id=%s chose language=%s", callback.from_user.id, language)

    bot = dialog_manager.middleware_data.get("bot")

    await dialog_manager.next()


async def get_user_info(event_isolation, dialog_manager: DialogManager, *args, **kwargs):
    return {
        "tg_id": dialog_manager.dialog_data.get("tg_id"),
    }


async def on_start_workflow(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):

    await dialog_manager.start(MainMenu.show_list,
                               data={"tg_id": callback.from_user.id,
                                     }
                               )


start = Dialog(
    Window(
        I18NFormat("choose-language"),
        Row(
            Button(
                I18NFormat(Language.EN),
                id=Language.EN,
                on_click=language_clicked),
            Button(
                I18NFormat(Language.UK),
                id=Language.UK,
                on_click=language_clicked),
            ),
        state=ChangeLanguage.change_language),
    Window(
        I18NFormat("chosen-language"),
        Button(
            I18NFormat("get-started"),
            id="start_workflow",
            on_click=on_start_workflow
        ),
        state=ChangeLanguage.language_changed,
        ),
)



