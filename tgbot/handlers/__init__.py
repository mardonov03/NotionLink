from aiogram import Router
from aiogram.filters import CommandStart

from tgbot.handlers.commands import start_command_handler


def setup() -> Router:
    router = Router()

    router.message.register(start_command_handler, CommandStart())

    return router
