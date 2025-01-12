from aiogram import Bot, Dispatcher, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from config import API_TOKEN
import asyncio
import os
from datetime import datetime
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Путь к директории с заметками
NOTES_DIR = r"C:\Users\janis\my_obsidian_stuff"
os.makedirs(NOTES_DIR, exist_ok=True)

class NoteStates(StatesGroup):
    waiting_for_tags = State()

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_message_text(message: types.Message) -> str:
    """Извлекает текст из различных типов сообщений"""
    if message.text:
        return message.text
    elif message.caption:
        return message.caption
    elif message.forward_from:
        return message.text or message.caption or ""
    return ""

@dp.message()
async def handle_message(message: types.Message, state: FSMContext):
    """Обработчик входящих сообщений"""
    try:
        current_state = await state.get_state()
        logger.info(f"Текущее состояние: {current_state}")
        
        if current_state == NoteStates.waiting_for_tags.state:
            # Обработка тегов
            data = await state.get_data()
            note_text = data.get('note_text', '')
            
            logger.info(f"Получены теги: {message.text}")
            logger.info(f"Сохраненный текст: {note_text}")
            
            if not note_text:
                await message.reply("❌ Ошибка: текст заметки пустой")
                await state.clear()
                return
            
            # Получаем теги из сообщения
            tags = [tag.strip() for tag in message.text.split() if tag.strip().startswith('#')]
            obsidian_tags = [f"[[{tag.replace('#', '').capitalize()}]]" for tag in tags]

            
            # Создаем имя файла
            timestamp = datetime.now().strftime('%Y%m%d')
            filename = os.path.join(NOTES_DIR, f"note_{timestamp}.md")
            
            # Формируем содержимое
            content = f"""
tags: {' '.join(obsidian_tags)}
date: {datetime.now().strftime('%Y-%m-%d')}

{note_text}"""
            
            # Сохраняем файл
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Сохранен файл: {filename}")
            logger.info(f"Содержимое файла: {content[:100]}...")  # Логируем начало содержимого
            
            # Отправляем подтверждение
            await message.reply(f"✅ Заметка сохранена: {os.path.basename(filename)}")
            await state.clear()
            
        else:
            # Получаем текст сообщения
            text = get_message_text(message)
            if not text:
                await message.reply("❌ Пожалуйста, отправьте текстовое сообщение")
                return
                
            logger.info(f"Получено сообщение: {text[:100]}...")
            
            # Сохраняем текст в состояние
            await state.update_data(note_text=text)
            
            # Запрашиваем теги
            await message.reply("Введите теги через пробел (например: #работа #идеи)")
            await state.set_state(NoteStates.waiting_for_tags)
            logger.info("Ожидание тегов...")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await message.reply("❌ Произошла ошибка при обработке сообщения")
        await state.clear()

async def main():
    logger.info("Запуск бота...")
    try:
        # Запускаем бота
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        logger.info("Завершение работы бота")
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)