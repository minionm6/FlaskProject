import os
from datetime import datetime as dt

# Конфигурация приложения
class Config:
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Настройки пинг-мониторинга
    PING_INTERVAL = 600  # Секунд
    LOG_COUNT = 6        # Количество последних логов
    TARGET_IP = "10.10.0.187"
    LOG_FILE = "ping_log.txt"
    
    # Время запуска приложения
    APP_START_TIME = dt.now()

    # Настройки базы данных SQLite
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.dirname(__file__), '..', 'db1.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False