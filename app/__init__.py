from flask import Flask
from app.models import db
from flask_login import LoginManager
from app.config import Config
from app.utils.ping_monitor import start_ping_monitoring
from app.utils.db_init import create_admin, create_roles, create_equipments, create_statuses




def init_template_filters(app):

    @app.template_test('admin')
    def is_admin(user):
        if not user or not user.is_authenticated:
            return False
        return user.role and user.role.name == "admin"

    @app.template_test('operator_or_admin')
    def is_operator_or_admin(user):
        if not user or not user.is_authenticated:
            return False
        return user.role and user.role.name in ("admin", "operator")



login_manager = LoginManager()


def create_app():
    """Фабрика создания приложения Flask"""
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    
    # Загрузка конфигурации
    app.config.from_object(Config)
    
    # Инициализация базы данных
    db.init_app(app)

    # Логин менеджер для проверки регистрации
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    # ...
    
    # Регистрация blueprint'ов
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    with app.app_context():
        db.create_all()        
        create_roles()         
        create_admin() 
        create_statuses()
        create_equipments() 
    
    init_template_filters(app)
    
    # Запуск мониторинга пинга
    start_ping_monitoring()
    
    return app


@login_manager.user_loader
def load_user(user_id):
    """Возвращает объект пользователя по его id"""
    from app.models import User
    return User.query.get(int(user_id))