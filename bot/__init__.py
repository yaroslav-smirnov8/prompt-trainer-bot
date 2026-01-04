from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import config

# Initialize bot and dispatcher
bot = Bot(token=config.bot.token, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

__all__ = ["bot", "dp"]