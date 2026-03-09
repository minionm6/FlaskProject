from collections import deque
from app.config import Config
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Глобальные данные
logs_for_site = deque(maxlen=Config.LOG_COUNT)
_ping_thread_started = False

# Класс пользователя
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(80), unique = True, nullable = False)
    password_hash = db.Column(db.String(200), nullable = False)

    def set_password(self, password):
        """Сохраняет хэш пароля"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Проверяет совпадение пароля с хэшем"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
