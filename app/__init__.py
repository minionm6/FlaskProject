from flask import Flask
from app.config import Config
from app.utils.ping_monitor import start_ping_monitoring
from app.main import bp as main_bp
from app.auth import bp as auth_bp


def create_app():
    """Фабрика создания приложения Flask"""
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    
    # Загрузка конфигурации
    app.config.from_object(Config)
    
    # Инициализация расширений (если будут)
    # ...
    
    # Регистрация blueprint'ов
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Запуск мониторинга пинга
    start_ping_monitoring()
    
    return app