import json

from settings import settings

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.filters.state import StatesGroup, State

from aiogram_dialog import Window, Dialog, DialogManager, setup_dialogs
from aiogram_dialog.widgets.text import Const
from sqlalchemy.ext.asyncio import AsyncSession

from database.requests import db_add_user

LANGUAGES = ['en', 'uk']

with open('translations.json', 'r', encoding='utf-8') as file:
    translations = json.load(file)

user_private_router = Router()


class States(StatesGroup):
    change_language = State()


change_language_window = Window(
    Const("Choo"),
    state=States.change_language,
)

dialog = Dialog(
    change_language_window
)

user_private_router.include_router(dialog)
setup_dialogs(user_private_router)


@user_private_router.message(CommandStart())
async def start(message: Message, dialog_manager: DialogManager, session: AsyncSession):
    await message.delete()

    if message.from_user.language_code in LANGUAGES:
        language = message.from_user.language_code
    else:
        language = settings.DEFAULT_LANGUAGE

    data = {
        "tg_id": message.from_user.id,
        "language": language
    }

    try:
        await db_add_user(session, data)
    except Exception as e:
        print(f"Error = {e}.")








