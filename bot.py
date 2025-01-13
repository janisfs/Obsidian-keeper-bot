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

def extract_title(text: str) -> str:
    """Извлекает заголовок из первой строки текста"""
    lines = text.strip().split('\n')
    title = lines[0] if lines else "Untitled"
    return title.strip()


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
    try:
        current_state = await state.get_state()
        logger.info(f"Текущее состояние: {current_state}")
        
        if current_state == NoteStates.waiting_for_tags.state:
            data = await state.get_data()
            note_text = data.get('note_text', '')
            
            if not note_text:
                await message.reply("❌ Ошибка: текст заметки пустой")
                await state.clear()
                return
            
            # Извлекаем заголовок из первой строки
            title = extract_title(note_text)
            
            # Получаем теги из сообщения
            tags = [tag.strip() for tag in message.text.split() if tag.strip().startswith('#')]
            obsidian_tags = [f"[[{tag.replace('#', '').capitalize()}]]" for tag in tags]
            
            # Создаем безопасное имя файла из заголовка
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            filename = os.path.join(NOTES_DIR, f"{safe_title}.md")
            
            
            content = f"""tags: {' '.join(obsidian_tags)}
                date: {datetime.now().strftime('%Y-%m-%d')}

                    {note_text}"""
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Сохранен файл: {filename}")
            await message.reply(f"✅ Заметка '{safe_title}' сохранена")
            await state.clear()
            
        else:
            text = get_message_text(message)
            if not text:
                await message.reply("❌ Пожалуйста, отправьте текстовое сообщение")
                return
            
            await state.update_data(note_text=text)
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