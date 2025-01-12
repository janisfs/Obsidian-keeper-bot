from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from config import API_TOKEN
import asyncio
import os
from datetime import datetime

NOTES_DIR = r"C:\Users\janis\my_obsidian_stuff"

class NoteStates(StatesGroup):
    waiting_for_tags = State()

async def main():
    # Инициализируем хранилище состояний
    storage = MemoryStorage()
    # Создаем один экземпляр бота и диспетчера
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(storage=storage)

    @dp.message()
    async def handle_message(message: Message, state: FSMContext):
        if message.text:
            await state.update_data(note_text=message.text)
            await message.reply("Пожалуйста, введите теги через пробел (например: #работа #идеи #проект)")
            await state.set_state(NoteStates.waiting_for_tags)

    @dp.message(NoteStates.waiting_for_tags)
    async def process_tags(message: Message, state: FSMContext):
        tags = [f"[[{tag.replace('#', '')}]]" for tag in message.text.split() if tag.startswith('#')]
        data = await state.get_data()
        
        save_note_to_obsidian(data['note_text'], tags)
        
        notification = await message.reply(f"✅ Заметка сохранена с тегами: {', '.join(tags) if tags else 'без тегов'}")
        await asyncio.sleep(3)
        await notification.delete()
        await message.delete()
        await state.clear()

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

def save_note_to_obsidian(note_text: str, tags: list):
    if not os.path.exists(NOTES_DIR):
        os.makedirs(NOTES_DIR)
    filename = os.path.join(NOTES_DIR, f"note_{datetime.now().strftime('%Y%m%d')}.md")
    with open(filename, "w", encoding="utf-8") as file:
        file.write(f"---\ntags: {' '.join(tags)}\ndate: {datetime.now().strftime('%Y-%m-%d')}\n---\n\n{note_text}")

if __name__ == "__main__":
    asyncio.run(main())
