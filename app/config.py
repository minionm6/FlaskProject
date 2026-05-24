import os
from datetime import datetime as dt

# Конфигурация приложения
class Config:
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Настройки пинг-мониторинга
    PING_INTERVAL = 30  # Секунд
    LOG_COUNT = 6        # Количество последних логов
    TARGET_IP = "192.168.42.1"
    LOG_FILE = "ping_log.txt"
    
    # Время запуска приложения
    APP_START_TIME = dt.now()

    # Настройки базы данных SQLite
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.dirname(__file__), '..', 'db1.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

     # Папка для загрузки изображений
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB максимум
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}