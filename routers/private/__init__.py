from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import CommandStart, Command

from routers.private.setup import start_language, language_setup
from routers.private.main_menu import change_language, main_menu

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)

router.include_router(language_setup)
router.message.register(start_language, CommandStart())

router.include_router(main_menu)
router.message.register(change_language, Command("language"))


