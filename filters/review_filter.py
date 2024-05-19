from aiogram.filters import Filter
from aiogram.types import Message
from aiogram_dialog import DialogManager

from states.main_menu import MainMenu


class IsReview(Filter):
    async def __call__(self, message: Message, dialog_manager: DialogManager) -> bool:
        if dialog_manager.current_context().state == MainMenu.leave_review:
            return True
        return False
