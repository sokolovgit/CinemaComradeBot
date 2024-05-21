from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram_i18n import I18nContext
from enums.language import Language


def main_keyboard(i18n: I18nContext):
    kb = [
            [
             KeyboardButton(text=i18n.get("language")),
             KeyboardButton(text=i18n.get("random")),
            ],
    ]

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True,
                                   keyboard=kb,
                                   input_field_placeholder=i18n.get("choose-action"))

    return keyboard
