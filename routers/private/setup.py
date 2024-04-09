from asyncio import sleep

from aiogram import Bot, html
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import Row, Button, Group, Cancel, Start
from aiogram_i18n import I18nContext

from utils.logger import setup_logger

from states.change_language import ChangeLanguage
from states.main_menu import MainMenu
from settings import settings
from enums import Language
from utils.i18n_format import I18NFormat


logger = setup_logger()


async def start_language(message: Message, i18n: I18nContext, dialog_manager: DialogManager):

    if message.from_user.language_code in Language.__members__.values():
        language = message.from_user.language_code
        await i18n.set_locale(language)
        logger.info("User id=%s set to default language=%s", message.from_user.id, language)

    await dialog_manager.start(ChangeLanguage.change_language)

    await message.delete()


async def language_clicked(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    language = button.widget_id
    i18n: I18nContext = dialog_manager.middleware_data.get("i18n")

    await i18n.set_locale(language)
    logger.info("User id=%s chose language=%s", callback.from_user.id, language)
    await dialog_manager.next()


async def start_workflow(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):

    await dialog_manager.start(MainMenu.show_list, mode=StartMode.NEW_STACK)

    await sleep(0.02)
    await callback.message.delete()

    logger.info("User id=%s started workflow", callback.from_user.id)


language_setup = Dialog(
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
        Cancel(
            I18NFormat("get-started"),
            on_click=start_workflow,
            ),
        state=ChangeLanguage.language_changed,
        ),
)



