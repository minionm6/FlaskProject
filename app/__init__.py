from flask import Flask
from app.models import db
from flask_login import LoginManager
from app.config import Config
from app.utils.ping_monitor import start_ping_monitoring
from app.utils.db_init import create_admin, create_roles, create_equipments, create_statuses
from app.utils.file_handler import ensure_upload_folder

login_manager = LoginManager()

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

def create_app():
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    
    app.config.from_object(Config)
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
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
        ensure_upload_folder()
    
    init_template_filters(app)
    
    # Запуск фонового мониторинга всех станций
    start_ping_monitoring(app)
    
    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))