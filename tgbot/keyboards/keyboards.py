from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

def get_add_token_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Добавить')],
            [KeyboardButton(text='Пропустить')]
        ],
        resize_keyboard=True
    )

def get_category_keyboard(categories):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f'{i}') for i in categories[j:j + 2]]
            for j in range(0, len(categories), 2)
        ] + [[KeyboardButton(text='создать новую')]],
        resize_keyboard=True
    )

def get_yes_no_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Да')],
            [KeyboardButton(text='Нет')]
        ],
        resize_keyboard=True
    )

def get_get_links_category_keyboard(categories):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f'{i}') for i in categories[j:j + 2]]
            for j in range(0, len(categories), 2)
        ] + [[KeyboardButton(text='все')]],
        resize_keyboard=True
    )
