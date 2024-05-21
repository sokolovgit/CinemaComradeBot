from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import CommandStart, Command, StateFilter

from states.main_menu import MainMenu
from routers.private.setup import start_language, start
from routers.private.main_menu import change_language, main_menu, add_movie, get_users_review

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)

router.include_router(start)
router.message.register(start_language, CommandStart())

router.message.register(change_language, Command("language"))
router.message.register(change_language, F.text == "🌐 Change language")

router.include_router(main_menu)

