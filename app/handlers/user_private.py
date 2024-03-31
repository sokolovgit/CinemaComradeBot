import json


from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart


with open('app/translations.json', 'r', encoding='utf-8') as file:
    translations = json.load(file)

user_private_router = Router()


@user_private_router.message(CommandStart())
async def start(message: Message):
    await message.answer(translations["en"]["hello_world"])
    await message.delete()
