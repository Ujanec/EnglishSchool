import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Базовый класс конфигурации."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'database.db'
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    ADMIN_ID = os.environ.get('ADMIN_ID')

class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = True

class ProductionConfig(Config):
    """Конфигурация для продакшена."""
    DEBUG = False
    # Здесь могут быть другие настройки, например, другой путь к БД