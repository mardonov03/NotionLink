from aiogram import Router
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.types import ContentType
from tgbot.handlers.commands import (
    start_command_handler,
    handle_add_token,
    handle_start,
    command_token,
    handle_link_selection,
    handle_message_with_links,
    handle_category_selection,
    handle_new_category, handle_get_links, handle_get_category, handle_refresh2, handle_refresh, handle_delete, handle_priority_selection
)
from tgbot.states.states import UserStages

def setup() -> Router:
    router = Router()

    router.message.register(start_command_handler, CommandStart())
    router.message.register(handle_start, StateFilter(UserStages.start))
    router.message.register(handle_add_token, StateFilter(UserStages.token))
    router.message.register(command_token, Command('token'))
    router.message.register(handle_get_links, Command('links'))
    router.message.register(handle_refresh, Command('refresh'))
    router.message.register(handle_delete, Command('deletelinks'))
    router.message.register(handle_link_selection, StateFilter(UserStages.link_selection))
    router.message.register(handle_category_selection, StateFilter(UserStages.category_selection))
    router.message.register(handle_new_category, StateFilter(UserStages.new_category))
    router.message.register(handle_get_category, StateFilter(UserStages.get_category))
    router.message.register(handle_refresh2, StateFilter(UserStages.yes_no))
    router.message.register(handle_priority_selection, UserStages.select_priority)


    router.message.register(
        handle_message_with_links,
        lambda message: message.content_type in {ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO}
    )
    return router

