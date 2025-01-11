from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

API_TOKEN = 'ВАШ_ТОКЕН_БОТА'  # Замените на токен вашего бота

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Отправьте мне сообщение, чтобы сохранить его.")

@dp.message_handler()
async def save_message(message: types.Message):
    # Заглушка для сохранения сообщения
    await message.reply(f"Вы отправили: {message.text}\n(Скоро добавим сохранение!)")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
