import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest # Для обработки ошибок редактирования
from aiogram.filters.callback_data import CallbackData
import os
from dotenv import load_dotenv

load_dotenv()

# --- Константы ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID_STR = os.getenv('ADMIN_ID')
DATABASE = os.getenv('DATABASE_PATH', 'database.db')
CALLBACKS_PER_PAGE = 10 # Количество заявок на одной странице

ADMIN_ID = None
if not BOT_TOKEN:
    logging.critical("BOT_TOKEN не найден в переменных окружения для бота!")
    # Можно добавить sys.exit(1) если бот не может работать без токена
if not ADMIN_ID_STR:
    logging.critical("ADMIN_ID не найден в переменных окружения для бота!")
else:
    try:
        ADMIN_ID = int(ADMIN_ID_STR)
    except ValueError:
        logging.critical(f"ADMIN_ID '{ADMIN_ID_STR}' не является корректным числом для бота!")

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Инициализация бота и диспетчера ---
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# --- CallbackData Фабрики ---
class CallbackAction(CallbackData, prefix="cb"):
    action: str # 'toggle_status' или 'page'
    item_id: int # ID заявки (для toggle_status) или 0 (для page)
    page: int # Текущая или целевая страница
    current_status: int # Текущий статус (0 или 1) (для toggle_status)

# --- Функции для работы с БД ---
def get_db_connection():
    """Создает и возвращает соединение с БД."""
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        return None

def get_callbacks(offset=0, limit=CALLBACKS_PER_PAGE):
    """Получает список заявок из БД с пагинацией."""
    conn = get_db_connection()
    if not conn: return [], 0 # Возвращаем пустой список и 0, если нет соединения
    try:
        cursor = conn.cursor()
        # Получаем общее количество записей
        cursor.execute("SELECT COUNT(*) FROM callbacks")
        total_count = cursor.fetchone()[0]
        # Получаем записи для текущей страницы
        cursor.execute("SELECT id, name, phone, processed, timestamp FROM callbacks ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset))
        callbacks = cursor.fetchall()
        conn.close()
        return callbacks, total_count
    except sqlite3.Error as e:
        logger.error(f"Error fetching callbacks: {e}")
        if conn: conn.close()
        return [], 0

def update_callback_status(callback_id: int, status: int):
    """Обновляет статус processed для заявки."""
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE callbacks SET processed = ? WHERE id = ?", (status, callback_id))
        conn.commit()
        conn.close()
        logger.info(f"Callback ID {callback_id} status updated to {status}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error updating callback status for ID {callback_id}: {e}")
        if conn: conn.close()
        return False

# --- Клавиатуры ---
def create_callbacks_keyboard(callbacks: list, current_page: int, total_count: int) -> InlineKeyboardMarkup:
    """Создает инлайн-клавиатуру для списка заявок с пагинацией."""
    builder = InlineKeyboardBuilder()
    if not callbacks:
        builder.row(InlineKeyboardButton(text="Нет необработанных заявок", callback_data=CallbackAction(action="noop", item_id=0, page=0, current_status=0).pack())) # Пустая кнопка
        return builder.as_markup()

    # Кнопки для каждой заявки
    for cb in callbacks:
        status_icon = "✅" if cb['processed'] == 1 else "❌"
        button_text = f"{status_icon} {cb['name']} - {cb['phone']}"
        # Передаем ID заявки, текущую страницу и ТЕКУЩИЙ статус
        callback_data = CallbackAction(
            action="toggle_status",
            item_id=cb['id'],
            page=current_page,
            current_status=cb['processed']
        ).pack()
        builder.row(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    # Кнопки пагинации
    total_pages = (total_count + CALLBACKS_PER_PAGE - 1) // CALLBACKS_PER_PAGE
    pagination_buttons = []
    if current_page > 0:
        pagination_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=CallbackAction(action="page", item_id=0, page=current_page - 1, current_status=0).pack())
        )
    if current_page < total_pages - 1:
        pagination_buttons.append(
            InlineKeyboardButton(text="Вперед ➡️", callback_data=CallbackAction(action="page", item_id=0, page=current_page + 1, current_status=0).pack())
        )

    if pagination_buttons:
        builder.row(*pagination_buttons) # Добавляем кнопки пагинации в один ряд

    return builder.as_markup()

# --- Обработчики команд и колбэков ---

# Декоратор для проверки ID админа
def admin_only(handler):
    async def wrapper(event: types.Message | types.CallbackQuery, *args, **kwargs):
        if event.from_user.id != ADMIN_ID:
            logger.warning(f"Unauthorized access attempt by user {event.from_user.id}")
            if isinstance(event, types.Message):
                await event.answer("Извините, эта команда доступна только администратору.")
            elif isinstance(event, types.CallbackQuery):
                await event.answer("Доступ запрещен.", show_alert=True)
            return
        return await handler(event, *args, **kwargs)
    return wrapper


async def show_page(event: types.Message | types.CallbackQuery, page: int = 0):
    """Отображает страницу со списком заявок."""
    offset = page * CALLBACKS_PER_PAGE
    callbacks, total_count = get_callbacks(offset=offset, limit=CALLBACKS_PER_PAGE)
    total_pages = (total_count + CALLBACKS_PER_PAGE - 1) // CALLBACKS_PER_PAGE

    text = f"<b>Список заявок</b> (Страница {page + 1}/{total_pages}, Всего: {total_count}):\n\n"
    if not callbacks and total_count > 0:
         text += "На этой странице заявок нет."
    elif not callbacks and total_count == 0:
         text += "Новых заявок нет."
    # Текст заявки теперь в кнопках

    keyboard = create_callbacks_keyboard(callbacks, page, total_count)

    if isinstance(event, types.Message):
        await event.answer(text, reply_markup=keyboard)
    elif isinstance(event, types.CallbackQuery) and event.message:
        try:
            # Пытаемся отредактировать сообщение
            await event.message.edit_text(text, reply_markup=keyboard)
            await event.answer() # Убираем часики на кнопке
        except TelegramBadRequest as e:
            # Если сообщение не изменилось, просто убираем часики
            if "message is not modified" in str(e):
                await event.answer("Статус обновлен.")
            else:
                logger.error(f"Error editing message: {e}")
                await event.answer("Не удалось обновить список.", show_alert=True)


@dp.message(CommandStart())
@dp.message(Command("callbacks"))
@admin_only
async def handle_start_or_callbacks(message: types.Message, **kwargs): # <-- Добавили **kwargs
    """Обработчик команды /start или /callbacks."""
    # kwargs будет содержать все "лишние" аргументы, которые мы просто игнорируем
    logger.info(f"Admin {message.from_user.id} requested callbacks list.")
    await show_page(message, page=0)


@dp.callback_query(CallbackAction.filter(F.action == "page"))
@admin_only
async def handle_page_callback(query: types.CallbackQuery, callback_data: CallbackAction, **kwargs): # <-- Добавили **kwargs
    """Обработчик нажатия на кнопки пагинации."""
    logger.info(f"Admin {query.from_user.id} requested page {callback_data.page}")
    await show_page(query, page=callback_data.page)


@dp.callback_query(CallbackAction.filter(F.action == "toggle_status"))
@admin_only
async def handle_toggle_status_callback(query: types.CallbackQuery, callback_data: CallbackAction, **kwargs): # <-- Добавили **kwargs
    """Обработчик нажатия на кнопку заявки (смена статуса)."""
    # kwargs будет содержать все "лишние" аргументы, которые мы просто игнорируем
    callback_id = callback_data.item_id
    current_status = callback_data.current_status
    new_status = 1 if current_status == 0 else 0 # Инвертируем статус
    current_page = callback_data.page

    logger.info(f"Admin {query.from_user.id} toggling status for callback ID {callback_id} to {new_status}")

    success = update_callback_status(callback_id, new_status)

    if success:
        # Обновляем сообщение с той же страницей
        await show_page(query, page=current_page)
    else:
        await query.answer("Ошибка при обновлении статуса в БД.", show_alert=True)

# --- Запуск бота ---
async def main():
    logger.info("Starting bot...")
    # Можно добавить проверку/создание БД здесь, если бот запускается отдельно
    # init_db_bot() # По аналогии с init_db в app.py
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())