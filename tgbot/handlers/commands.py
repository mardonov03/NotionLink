from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import logging
import betterlogging as bl
from notion_client import Client
import re

log_level = logging.INFO
bl.basic_colorized_config(level=log_level)
logger = logging.getLogger(__name__)
logger.info("Starting bot")


class UserStages(StatesGroup):
    start = State()
    token = State()
    link_selection = State()
    category_selection = State()
    new_category = State()


async def start_command_handler(message: types.Message, state: FSMContext, dispatcher):
    from_user = message.from_user

    usermodel = dispatcher['usermodel']
    is_waiting = await usermodel.is_waiting(from_user.id)
    if is_waiting:
        await message.answer('Пожалуйста, дождитесь ответа на предыдущий запрос.')
        return

    token = await usermodel.check_token_db(from_user)
    try:
        if token is None:
            keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Добавить')], [KeyboardButton(text='Пропустить')]],resize_keyboard=True)
            await message.answer(
                f'Привет {from_user.first_name}\n\n'
                'Вы можете добавить свой токен и управлять своим аккаунтом через бот',
                reply_markup=keyboard
            )
            await state.set_state(UserStages.start)
        else:
            await message.answer(f'Привет {from_user.first_name}\n\nРад тебя видет сново)', )
    except Exception as e:
        logger.error(f'error764265454: {e}')

async def handle_start(message: types.Message, state: FSMContext):
    try:
        if message.text == 'Пропустить':
            await message.answer("Хорошо, вы можете добавить токен в любой момент через /token",
                                 reply_markup=ReplyKeyboardRemove())
            await state.clear()
        elif message.text == 'Добавить':
            await message.answer("Отправь нам токен", reply_markup=ReplyKeyboardRemove())
            await state.set_state(UserStages.token)
    except Exception as e:
        logger.error(f'error573645: {e}')


async def command_token(message: types.Message, state: FSMContext):
    try:
        await message.answer("Отправь нам токен", reply_markup=ReplyKeyboardRemove())
        await state.set_state(UserStages.token)
    except Exception as e:
        logger.error(f'error12345: {e}')


async def handle_add_token(message: types.Message, state: FSMContext, dispatcher):
    usermodel = dispatcher['usermodel']
    tokenmodel = dispatcher['tokenmodel']

    is_waiting = await usermodel.is_waiting(message.from_user.id)
    if is_waiting:
        await message.answer('Пожалуйста, дождитесь ответа на предыдущий запрос.')
        return

    try:
        await usermodel.update_waiting(message.from_user.id)
        await message.answer('Мы передали токен на проверку, пожалуйста, подождите.')

        result = await tokenmodel.add_token(message.from_user.id, message.text)
        if result:
            await message.answer("Токен успешно добавлен.")
        else:
            await message.answer("Токен не прошел проверку и запрос был отклонен.")
    except Exception as e:
        logger.error(f'error98472652: {e}')
    finally:
        await usermodel.update_waiting(message.from_user.id)
        await state.clear()


async def handle_message_with_links(message: types.Message, state: FSMContext, dispatcher):
    usermodel = dispatcher['usermodel']

    is_waiting = await usermodel.is_waiting(message.from_user.id)
    if is_waiting:
        await message.answer('Пожалуйста, дождитесь ответа на предыдущий запрос.')
        return
    try:
        text_content = message.text or message.caption

        link_pattern = r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)'

        links = re.findall(link_pattern, text_content)

        unique_links = list(dict.fromkeys(links))

        if not unique_links:
            await message.answer("В сообщении не найдено ссылок.")
            return

        if len(unique_links) == 1:
            categories = await usermodel.get_user_categories(message.from_user.id)

            keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=f'{i}') for i in categories], [KeyboardButton(text='создать новую')]],
                resize_keyboard=True
            )

            await message.answer(f'В какую категорию вы хотите сохранить выбранные ссылки?', reply_markup=keyboard)
            await state.update_data(selected_links=unique_links)
            await state.set_state(UserStages.category_selection)
            return
        links_message = "Найдены ссылки:\n" + "\n".join([f"{i + 1}. {link}" for i, link in enumerate(unique_links)])
        links_message += "\n\nВведите номера ссылок через пробел, которые хотите сохранить например: 1 2 4..."
        await message.answer(links_message)

        await state.update_data(links=unique_links)
        await state.set_state(UserStages.link_selection)
    except Exception as e:
        logger.error(f'error742865: {e}')

async def handle_link_selection(message: types.Message, state: FSMContext, dispatcher):
    usermodel = dispatcher['usermodel']
    user_id = message.from_user.id

    is_waiting = await usermodel.is_waiting(user_id)
    if is_waiting:
        await message.answer('Пожалуйста, дождитесь ответа на предыдущий запрос.')
        return

    data = await state.get_data()
    links = data.get("links", [])

    try:
        selected_indexes = message.text.split()
        selected_links = []
        for index in selected_indexes:
            if index.isdigit():
                idx = int(index) - 1
                if 0 <= idx < len(links):
                    selected_links.append(links[idx])

        if not selected_links:
            await message.answer("Вы не выбрали ссылки для сохранения.")
            await state.clear()
            return

        categories = await usermodel.get_user_categories(user_id)

        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=f'{i}') for i in categories], [KeyboardButton(text='создать новую')]],
            resize_keyboard=True
        )

        await message.answer(f'В какую категорию вы хотите сохранить выбранные ссылки?', reply_markup=keyboard)
        await state.update_data(selected_links=selected_links)
        await state.set_state(UserStages.category_selection)
    except Exception as e:
        logger.error(f'error742864: {e}')
        await message.answer("Произошла ошибка при обработке вашего выбора.")


async def handle_category_selection(message: types.Message, state: FSMContext, dispatcher):
    usermodel = dispatcher['usermodel']
    linksmodel = dispatcher['linksmodel']
    user_id = message.from_user.id

    is_waiting = await usermodel.is_waiting(user_id)
    if is_waiting:
        await message.answer('Пожалуйста, дождитесь ответа на предыдущий запрос.')
        return
    try:
        data = await state.get_data()
        selected_links = data.get("selected_links", [])

        category = message.text
        if category == 'создать новую':
            await message.answer("Введите название новой категории:", reply_markup=ReplyKeyboardRemove())
            await state.set_state(UserStages.new_category)
        else:
            for link in selected_links:
                await linksmodel.add_link(user_id, link, category)
            await message.answer(f"Выбранные ссылки успешно сохранены в категорию '{category}'.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
    except Exception as e:
        logger.error(f'error356263254: {e}')


async def handle_new_category(message: types.Message, state: FSMContext, dispatcher):
    usermodel = dispatcher['usermodel']
    linksmodel = dispatcher['linksmodel']
    user_id = message.from_user.id

    is_waiting = await usermodel.is_waiting(user_id)
    if is_waiting:
        await message.answer('Пожалуйста, дождитесь ответа на предыдущий запрос.')
        return
    try:
        new_category = message.text
        data = await state.get_data()
        selected_links = data.get("selected_links", [])

        for link in selected_links:
            await linksmodel.add_link(user_id, link, new_category)

        await message.answer(f"Выбранные ссылки успешно сохранены в новую категорию '{new_category}'.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
    except Exception as e:
        logger.error(f'error7486542444: {e}')