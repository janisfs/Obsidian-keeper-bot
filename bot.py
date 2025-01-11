from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
import asyncio
from config import API_TOKEN


async def main():
    # Проверяем наличие токена
    if not API_TOKEN:
        raise ValueError("API_TOKEN не найден! Проверьте файл config.py или переменные окружения.")

    # Создаем экземпляры бота и диспетчера
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    # Обработчик для команды /start
    @dp.message(Command(commands=["start"]))
    async def send_welcome(message: Message):
        await message.answer("Привет! Я бот для хранения заметок в Obsidian!")

    # Запускаем бота
    try:
        print("Бот запущен...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
