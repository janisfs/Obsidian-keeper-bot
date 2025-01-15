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
import aiohttp
from urllib.parse import urlparse
import hashlib
import re


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


class MessageData:
    def __init__(self):
        self.title = ""
        self.text = ""
        self.urls = []
        self.image_links = []


# Пути к директориям
NOTES_DIR = r"C:\Users\janis\my_obsidian_stuff"
CACHE_DIR = os.path.join(NOTES_DIR, "Cache")
os.makedirs(NOTES_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


class NoteStates(StatesGroup):
    waiting_for_tags = State()


# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


def find_urls(text: str) -> list[str]:
    """Находит URL в тексте"""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)


def format_message_with_urls(text: str, urls: list[str]) -> str:
    """Форматирует текст сообщения, добавляя ссылки в конец"""
    # Основной текст
    formatted_text = text

    # Если есть ссылки, добавляем их в конец
    if urls:
        formatted_text += "\n\n🔗 Ссылки:\n"
        for url in urls:
            parsed_url = urlparse(url)
            name = parsed_url.netloc
            formatted_text += f"- [{name}]({url})\n"

    return formatted_text


async def download_image(file: types.File) -> tuple[str, str]:
    """Скачивает изображение и возвращает путь к сохраненному файлу и имя файла"""
    try:
        file_path = await bot.get_file(file.file_id)
        file_url = file_path.file_path
        logger.info(f"Получен файл: {file_url}")

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.telegram.org/file/bot{API_TOKEN}/{file_url}") as response:
                if response.status != 200:
                    logger.error(f"Ошибка при скачивании: статус {response.status}")
                    raise Exception(f"Ошибка скачивания: {response.status}")
                
                content = await response.read()
                logger.info(f"Скачано {len(content)} байт")
                
                file_hash = hashlib.md5(content).hexdigest()
                _, ext = os.path.splitext(file_url)
                if not ext:
                    ext = '.jpg'
                
                filename = f"{file_hash}{ext}"
                filepath = os.path.join(CACHE_DIR, filename)
                
                try:
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    logger.info(f"Файл сохранен: {filepath}")
                except Exception as e:
                    logger.error(f"Ошибка при сохранении файла: {e}")
                    raise
                
                return filepath, filename
    except Exception as e:
        logger.error(f"Ошибка при скачивании изображения: {e}")
        raise


def extract_title(text: str) -> str:
    """Извлекает заголовок из первой строки текста"""
    lines = text.strip().split('\n')
    title = lines[0] if lines else "Untitled"
    return title.strip()


async def process_message(message: types.Message) -> MessageData:
    """Обрабатывает сообщение и возвращает структурированные данные"""
    data = MessageData()
    
    # Получаем текст сообщения
    text = message.caption if message.caption else message.text if message.text else "Untitled"
    
    # Находим URL в тексте
    urls = find_urls(text)
    if urls:
        logger.info(f"Найдены URL: {urls}")
        data.urls = urls
    
    # Обрабатываем фотографии
    if message.photo:
        logger.info("Обработка фотографии из сообщения")
        photo = message.photo[-1]
        filepath, filename = await download_image(photo)
        relative_path = os.path.relpath(filepath, NOTES_DIR).replace('\\', '/')
        image_link = f"![[{relative_path}]]"
        logger.info(f"Создана ссылка на изображение: {image_link}")
        data.image_links.append(image_link)
    
    # Форматируем текст с учётом ссылок
    data.text = format_message_with_urls(text, urls)
    data.title = extract_title(text)
    
    return data


@dp.message()
async def handle_message(message: types.Message, state: FSMContext):
    try:
        current_state = await state.get_state()
        logger.info(f"Текущее состояние: {current_state}")
        
        if current_state == NoteStates.waiting_for_tags.state:
            data = await state.get_data()
            note_text = data.get('note_text', '')
            image_links = data.get('image_links', [])
            
            if not note_text and not image_links:
                await message.reply("❌ Ошибка: текст заметки пустой")
                await state.clear()
                return
            
            # Получаем теги из сообщения
            tags = [tag.strip() for tag in message.text.split() if tag.strip().startswith('#')]
            obsidian_tags = [f"[[{tag.replace('#', '').capitalize()}]]" for tag in tags]
            
            # Создаем безопасное имя файла из заголовка
            title = extract_title(note_text)
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            filename = os.path.join(NOTES_DIR, f"{safe_title}.md")
            
            content = f"""tags: {' '.join(obsidian_tags)}
date: {datetime.now().strftime('%Y-%m-%d')}

{note_text}

{''.join(f'\n{link}' for link in image_links)}"""
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Сохранен файл: {filename}")
            logger.info(f"Содержимое заметки: {content}")
            await message.reply(f"✅ Заметка '{safe_title}' сохранена")
            await state.clear()
            
        else:
            # Обрабатываем новое сообщение
            message_data = await process_message(message)
            
            # Сохраняем данные в состояние
            await state.update_data(
                note_text=message_data.text,
                image_links=message_data.image_links
            )
            
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