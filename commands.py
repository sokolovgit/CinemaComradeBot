from aiogram import Bot
from aiogram.types import BotCommand
from aiogram_i18n import I18nContext


async def set_bot_commands(bot: Bot, i18n: I18nContext) -> None:

    commands = [
        BotCommand(command="language", description=i18n.get("command-language")),
        BotCommand(command="random", description=i18n.get("command-random")),
        BotCommand(command="movies_on_genre", description=i18n.get("command-movies-on-genre")),
    ]

    await bot.set_my_commands(commands)