from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy  # <-- Импортируем SQLAlchemy
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
import re
import requests
from dotenv import load_dotenv

load_dotenv()

# --- Конфигурация Flask ---
app = Flask(__name__)

# --- Конфигурация SQLAlchemy ---
# Указываем Flask, где находится наша база данных
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Инициализация расширений ---
db = SQLAlchemy(app)      # <-- Создаем объект БД
#migrate = Migrate(app, db)  # <-- Создаем объект для миграций


DATABASE = os.getenv('DATABASE_PATH', 'database.db') # 'database.db' - значение по умолчанию
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

# --- Проверка, что обязательные переменные загружены ---
if not BOT_TOKEN:
    app.logger.critical("BOT_TOKEN не найден в переменных окружения!")
    # Здесь можно либо завершить приложение, либо использовать заглушку, но лучше завершить
    # raise ValueError("BOT_TOKEN не найден в переменных окружения!")
if not ADMIN_ID:
    app.logger.critical("ADMIN_ID не найден в переменных окружения!")
    # raise ValueError("ADMIN_ID не найден в переменных окружения!")
else:
    try:
        ADMIN_ID = int(ADMIN_ID) # Преобразуем ADMIN_ID в int
    except ValueError:
        app.logger.critical(f"ADMIN_ID '{ADMIN_ID}' не является корректным числом!")
        # raise ValueError(f"ADMIN_ID '{ADMIN_ID}' не является корректным числом!")




# ===>>> ОПРЕДЕЛЕНИЕ МОДЕЛИ БАЗЫ ДАННЫХ <<<===
# Теперь наша таблица описывается как Python-класс
class Callback(db.Model):
    __tablename__ = 'callbacks' # Явно указываем имя таблицы
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=False)
    lesson_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f'<Callback {self.name} - {self.phone}>'

# --- Функция отправки уведомления в Telegram ---
def send_telegram_notification(chat_id, text):
    """Отправляет сообщение в Telegram чат."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML' # Можно использовать HTML для форматирования
    }
    try:
        response = requests.post(url, json=payload, timeout=5) # Ставим таймаут
        response.raise_for_status() # Проверяем на HTTP ошибки
        app.logger.info(f"Telegram notification sent to {chat_id}. Response: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Failed to send Telegram notification to {chat_id}: {e}")
        return False
    except Exception as e:
        app.logger.error(f"An unexpected error occurred sending Telegram notification: {e}")
        return False


# --- Настройка логирования ---
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, 'app.log')

# Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
log_level = logging.INFO

# Форматтер для сообщений лога
log_formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)

pricing_data = {
    "individual_online": {
        "title": "Персональное", # Новое название
        "description": "Персональные онлайн-уроки через Zoom, MTS-link, Вебинар, WhatsApp или другие платформы. Максимальное внимание преподавателя и гибкий график.",
        "price": "3500", # Актуальная цена
        "old_price": "5000", # Старая цена (для зачеркивания)
        "unit": "руб./час" # Единица измерения
    },
    "group_online": {
        "title": "Групповое занятие", # Новое название
        "description": "Динамичные онлайн-занятия в небольшой группе (до 6 человек). Интерактивное обучение и общение.",
        "price": "2500", # Актуальная цена
        "old_price": "3500", # Старая цена
        "unit": "руб./час" # Единица измерения
    }
}

# Обработчик для записи логов в файл с ротацией
# maxBytes - максимальный размер файла лога перед ротацией
# backupCount - количество хранимых старых файлов лога
file_handler = RotatingFileHandler(
    log_file, maxBytes=1024*1024*5, backupCount=5, encoding='utf-8' # 5 MB
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(log_level)

# Обработчик для вывода логов в консоль (для отладки)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(log_level) # Можно поставить DEBUG для разработки

# Добавляем обработчики к логгеру Flask
app.logger.addHandler(file_handler)
app.logger.addHandler(console_handler) # Убрать для продакшена, если не нужен вывод в консоль
app.logger.setLevel(log_level)

# Убираем стандартный обработчик Flask, если он есть
app.logger.removeHandler(app.logger.handlers[0])

app.logger.info('Приложение English School запущено')

# --- Данные о ценах (пример, замените актуальными) ---
# Лучше вынести это в отдельный файл конфигурации или базу данных в будущем

# --- Маршруты (Routes) ---
@app.route('/submit_callback', methods=['POST'])
def submit_callback():
    app.logger.info(f'Получен POST-запрос на /submit_callback с IP: {request.remote_addr}')
    required_fields = ['name', 'full_phone', 'lesson_type', 'consent']
    missing_fields = [field for field in required_fields if field not in request.form or not request.form[field]]

    if missing_fields:
        error_message = f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"
        app.logger.warning(f"Ошибка валидации формы: {error_message}")
        return jsonify({"success": False, "error": "Пожалуйста, заполните все обязательные поля и дайте согласие."}), 400

    name = request.form['name'].strip()
    phone = request.form['full_phone'].strip()
    lesson_type = request.form['lesson_type'].strip()
    email = request.form.get('email', '').strip()
    consent = request.form['consent']

    if len(name) < 1: return jsonify({"success": False, "error": "Имя слишком короткое."}), 400
    if not re.match(r"^\+\d{10,}$", phone): return jsonify({"success": False, "error": "Некорректный формат телефона."}), 400
    if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email): return jsonify({"success": False, "error": "Некорректный формат email."}), 400
    if consent != 'on': return jsonify({"success": False, "error": "Необходимо согласие на обработку данных."}), 400

    try:
        new_callback = Callback(
            name=name,
            email=email if email else None,
            phone=phone,
            lesson_type=lesson_type
        )
        db.session.add(new_callback)  # Добавляем новый объект в сессию
        db.session.commit()  # Сохраняем изменения в БД

        new_callback_id = new_callback.id  # Получаем ID после коммита
        app.logger.info(
            f"Новая заявка сохранена (ID: {new_callback_id}): Имя={name}, Телефон={phone}, Тип={lesson_type}, Email={email}")

        # ===>>> ОТПРАВКА УВЕДОМЛЕНИЯ В TELEGRAM <<<===
        notification_text = (
            f"🔔 <b>Новая заявка на обратный звонок!</b>\n\n"
            f"<b>ID:</b> {new_callback_id}\n"
            f"<b>Имя:</b> {name}\n"
            f"<b>Телефон:</b> {phone}\n"
            f"<b>Email:</b> {email if email else 'Не указан'}\n"
            f"<b>Тип занятия:</b> {lesson_type}\n\n"
            f"Для просмотра списка заявок используйте команду /callbacks"
        )
        send_telegram_notification(ADMIN_ID, notification_text)
        # ===>>> КОНЕЦ ОТПРАВКИ УВЕДОМЛЕНИЯ <<<===

        return jsonify({"success": True, "message": "Заявка успешно отправлена!"})


    except Exception as e:  # Ловим более общую ошибку, т.к. теперь это не sqlite3.Error

        db.session.rollback()  # Откатываем транзакцию в случае ошибки

        app.logger.error(f"Ошибка при записи в БД: {e}")

        return jsonify({"success": False, "error": "Произошла ошибка на сервере. Попробуйте позже."}), 500

@app.route('/')
def index():
    """Главная страница"""
    app.logger.info(f'Запрос к главной странице с IP: {request.remote_addr}')
    current_year = datetime.now().year
    return render_template('index.html', current_year=current_year)

@app.route('/pricing')
def pricing():
    """Страница с ценами"""
    app.logger.info(f'Запрос к странице цен с IP: {request.remote_addr}')
    current_year = datetime.now().year
    return render_template('pricing.html', prices=pricing_data, current_year=current_year)

@app.route('/about')
def about():
    """Страница 'О нас'"""
    app.logger.info(f'Запрос к странице "О нас" с IP: {request.remote_addr}')
    current_year = datetime.now().year
    # Здесь можно передать доп. данные, если нужно (напр., список преподавателей из БД)
    # team_data = [...]
    return render_template('about.html', current_year=current_year) #, team=team_data)

# Обработчик ошибок 404 (Страница не найдена)
@app.errorhandler(404)
def page_not_found(error):
    app.logger.warning(f'Ошибка 404 - Страница не найдена: {request.url} (IP: {request.remote_addr})')
    current_year = datetime.now().year
    return render_template('404.html', current_year=current_year), 404 # Важно вернуть статус 404

# Обработчик общих ошибок сервера 500
@app.errorhandler(Exception)
def handle_exception(e):
    # Логируем полную информацию об ошибке
    app.logger.error(f'Произошла ошибка сервера (500): {e}', exc_info=True)
    current_year = datetime.now().year
    # Показываем пользователю общую страницу ошибки
    return render_template('500.html', current_year=current_year), 500

# --- Запуск приложения ---
if __name__ == '__main__':
    if not BOT_TOKEN or not ADMIN_ID: # Дополнительная проверка перед запуском
        print("Ошибка: BOT_TOKEN или ADMIN_ID не установлены. Проверьте переменные окружения.")
    else:
        app.run(debug=False, host='0.0.0.0', port=5000)