import os

from aiogram.filters import Filter
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()


class ChatTypeFilter(Filter):
    def __init__(self, chat_type: str) -> None:
        self.chat_types = chat_type

    async def __call__(self, message: Message) -> bool:
        return message.chat.type in self.chat_types


class AdminFilter(Filter):
    def __init__(self) -> None:
        self.admins = set(map(int, os.getenv('ADMIN', "").split(",")))

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in self.admins
