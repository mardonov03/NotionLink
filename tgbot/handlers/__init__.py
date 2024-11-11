from aiogram import Router
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.types import ContentType
from tgbot.handlers.commands import (
    start_command_handler,
    handle_add_token,
    handle_start,
    UserStages,
    command_token,
    handle_link_selection,
    handle_message_with_links
)

def setup() -> Router:
    router = Router()

    router.message.register(start_command_handler, CommandStart())
    router.message.register(handle_start, StateFilter(UserStages.start))
    router.message.register(handle_add_token, StateFilter(UserStages.token))
    router.message.register(command_token, Command('token'))

    router.message.register(handle_link_selection, StateFilter(UserStages.link_selection))

    router.message.register(
        handle_message_with_links,
        lambda message: message.content_type in {ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO}
    )

    return router

