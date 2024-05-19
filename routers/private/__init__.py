from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import CommandStart, Command
from filters.review_filter import IsReview

from routers.private.setup import start_language, start
from routers.private.main_menu import change_language, main_menu, add_movie, get_users_review

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)

router.include_router(start)
router.message.register(start_language, CommandStart())

router.include_router(main_menu)
router.message.register(change_language, Command("language"))

#here i need to check if the user is in the state of leaving a review

router.message.register(add_movie)
router.message.register(get_users_review)





