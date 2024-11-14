from aiogram import types
from aiogram.fsm.context import FSMContext
import logging
import betterlogging as bl
import re
from tgbot.states.states import UserStages
from tgbot.keyboards.keyboards import get_add_token_keyboard, get_category_keyboard, get_yes_no_keyboard, get_get_links_category_keyboard, get_priority_keyboard
from aiogram.types import ReplyKeyboardRemove
log_level = logging.INFO
bl.basic_colorized_config(level=log_level)
logger = logging.getLogger(__name__)
logger.info("Starting bot")

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
            keyboard = get_add_token_keyboard()
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
            await message.answer("Токен не прошел проверку и запрос был отклонен.\n\n<b>Совет: попробуйте создать страницу с названием (linksinbot) и убедитесь в том что подключили токен</b>",parse_mode='HTML')

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

            keyboard = get_category_keyboard(categories)

            await message.answer(f'В какую категорию вы хотите сохранить выбранные ссылки?', reply_markup=keyboard)
            forword_data = await get_forward(message)
            await state.update_data(selected_links=unique_links, forward_from= forword_data)
            await state.set_state(UserStages.category_selection)
            return
        links_message = "Найдены ссылки:\n" + "\n\n".join([f"{i + 1}. {link}" for i, link in enumerate(unique_links)])
        links_message += "\n\nВведите номера ссылок через пробел, которые хотите сохранить например: 1 2 4..."
        await message.answer(links_message)
        forword_data = await get_forward(message)
        await state.update_data(links=unique_links, forward_from = forword_data)
        await state.set_state(UserStages.link_selection)
    except Exception as e:
        logger.error(f'error742865: {e}')

async def get_forward(message):
    try:
        if not message.forward_origin:
            return
        if message.forward_origin.type == 'user':
            data = message.forward_from.username, message.forward_from.full_name, message.forward_origin.type
            return data
        elif message.forward_origin.type == 'channel' or message.forward_origin.type == 'chat':
            data = message.forward_from_chat.username, message.forward_from_chat.title, message.forward_origin.type
            return data
    except Exception as e:
        logger.error(f'error425y7224: {e}')

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

        keyboard = get_category_keyboard(categories)
        await message.answer(f'В какую категорию вы хотите сохранить выбранные ссылки?', reply_markup=keyboard)
        await state.update_data(selected_links=selected_links)
        await state.set_state(UserStages.category_selection)
    except Exception as e:
        logger.error(f'error742864: {e}')
        await message.answer("Произошла ошибка при обработке вашего выбора.")


async def handle_category_selection(message: types.Message, state: FSMContext, dispatcher):
    usermodel = dispatcher['usermodel']
    user_id = message.from_user.id

    is_waiting = await usermodel.is_waiting(user_id)
    if is_waiting:
        await message.answer('Пожалуйста, дождитесь ответа на предыдущий запрос.')
        return

    try:
        category = message.text

        if category == 'создать новую':
            await message.answer("Введите название новой категории:", reply_markup=ReplyKeyboardRemove())
            await state.set_state(UserStages.new_category)
        else:
            await state.update_data(category=category)
            await message.answer('Выберите важность (priority)', reply_markup=get_priority_keyboard())
            await state.set_state(UserStages.select_priority)

    except Exception as e:
        logger.error(f'error356263254: {e}')


async def handle_new_category(message: types.Message, state: FSMContext, dispatcher):
    usermodel = dispatcher['usermodel']
    user_id = message.from_user.id

    is_waiting = await usermodel.is_waiting(user_id)
    if is_waiting:
        await message.answer('Пожалуйста, дождитесь ответа на предыдущий запрос.')
        return
    try:
        new_category = message.text
        if len(new_category) > 16:
            await message.answer(f"Введите другое название максимальная длина названия - 16 символов.", reply_markup=ReplyKeyboardRemove())
            await state.set_state(UserStages.new_category)
            return

        await state.update_data(category=new_category)
        await message.answer('Выберите важность (priority)', reply_markup=get_priority_keyboard())
        await state.set_state(UserStages.select_priority)

    except Exception as e:
        logger.error(f'error7486542444: {e}')


async def handle_priority_selection(message: types.Message, state: FSMContext, dispatcher):
    usermodel = dispatcher['usermodel']
    user_id = message.from_user.id

    is_waiting = await usermodel.is_waiting(user_id)
    if is_waiting:
        await message.answer('Пожалуйста, дождитесь ответа на предыдущий запрос.')
        return

    try:
        priority = message.text
        if not priority.isdigit() or not (1 <= int(priority) <= 10):
            await message.answer("Пожалуйста, выберите приоритет числом от 1 до 10.")
            return

        await usermodel.update_waiting(user_id)

        data = await state.get_data()
        selected_links = data.get("selected_links", [])
        forward_from = data.get("forward_from", [])
        category = data.get("category")
        priority = int(priority)

        await message.answer('Мы передали ссылку на проверку, пожалуйста, подождите.',reply_markup=ReplyKeyboardRemove())

        for link in selected_links:
            await usermodel.add_link(message.from_user, link, category, dispatcher, forward_from, priority=priority)

        await message.answer(f"Выбранные ссылки успешно сохранены в категорию '{category}' с приоритетом {priority}.",reply_markup=ReplyKeyboardRemove())

        await state.clear()
        await usermodel.update_waiting(user_id)

    except Exception as e:
        logger.error(f'error653672: {e}')


async def handle_get_links(message: types.Message, state: FSMContext, dispatcher):
    userid = message.from_user.id
    usermodel = dispatcher['usermodel']

    is_waiting = await usermodel.is_waiting(userid)
    if is_waiting:
        await message.answer('Пожалуйста, дождитесь ответа на предыдущий запрос.')
        return

    try:
        categories = await usermodel.get_user_categories(userid)

        keyboard = get_get_links_category_keyboard(categories)
        await message.answer(f'Из какой категории вы хотите получит ссылки?', reply_markup=keyboard)
        await state.set_state(UserStages.get_category)
    except Exception as e:
        logger.error(f'error215853: {e}')


async def handle_get_category(message: types.Message, state: FSMContext, dispatcher):
    userid = message.from_user.id
    usermodel = dispatcher['usermodel']

    is_waiting = await usermodel.is_waiting(userid)
    if is_waiting:
        await message.answer('Пожалуйста, дождитесь ответа на предыдущий запрос.')
        return

    try:
        category = message.text
        links = await usermodel.get_user_links_with_info(userid, category)
        if links:
            links_count = len(links)
            links_text = f"Общее количество ссылок: {links_count}\n\n"
            links_text += "\n\n".join([
                f"{idx + 1}. "
                f"{f'({", ".join(filter(None, [link.get("fullname", ""), link.get("username", ""), link.get("type", "")]))})' if any([link.get('fullname'), link.get('username'), link.get('type')]) else '(Вы)'}\n"
                f"{link['link']}"
                for idx, link in enumerate(links)
                if any([link.get('fullname'), link.get('username'), link.get('type')]) or link.get('link')
            ])
        else:
            links_text = "Нет доступных ссылок в этой категории."

        await message.answer(links_text, reply_markup=ReplyKeyboardRemove())
        await state.clear()
    except Exception as e:
        logger.error(f'error9427642: {e}')



async def handle_refresh(message: types.Message, state: FSMContext, dispatcher):
    userid = message.from_user.id
    usermodel = dispatcher['usermodel']

    is_waiting = await usermodel.is_waiting(userid)
    if is_waiting:
        await message.answer('Пожалуйста, дождитесь ответа на предыдущий запрос.')
        return

    try:
        keyboard = get_yes_no_keyboard()
        await message.answer('Эта команда обновит данные между вашей локальной базой данных и Notion аккаунтом. После того как процесс запустится, его нельзя будет остановить или отменить. Вы на это согласны?',reply_markup=keyboard)
        await state.set_state(UserStages.yes_no)
    except Exception as e:
        logger.error(f'error8246715524: {e}')


async def handle_refresh2(message: types.Message, state: FSMContext, dispatcher):
    userid = message.from_user.id
    usermodel = dispatcher['usermodel']

    is_waiting = await usermodel.is_waiting(userid)
    if is_waiting:
        await message.answer('Пожалуйста, дождитесь ответа на предыдущий запрос.')
        return

    if message.text == 'Нет':
        await message.answer('Команда отменена.', reply_markup=ReplyKeyboardRemove())
        return

    await usermodel.update_waiting(userid)

    try:
        res = await usermodel.refresh_data(message.from_user)
        if res is None:
            await message.answer('Нам не удалось обновить данные', reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer('Ваши данные обновлены успешно', reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        logger.error(f'error64275792: {e}')
        await message.answer('Произошла ошибка при обновлении данных. Попробуйте позже.', reply_markup=ReplyKeyboardRemove())
    finally:
        await usermodel.update_waiting(userid)
        await state.clear()

async def handle_delete(message: types.Message, state: FSMContext, dispatcher):
    pass
