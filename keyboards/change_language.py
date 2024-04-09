# from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
# from aiogram.utils.keyboard import InlineKeyboardBuilder
# from aiogram_i18n import I18nContext
# from enums.language import Language
#
#
# def built_language_keyboard(builder: InlineKeyboardBuilder, i18n: I18nContext) -> None:
#     for language in Language.__members__.values():
#         builder.button(text=i18n.get(language), callback_data=f"change_language:{language}")
#
#
# def change_language_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
#     builder = InlineKeyboardBuilder()
#     built_language_keyboard(builder, i18n)
#
#     return builder.as_markup()