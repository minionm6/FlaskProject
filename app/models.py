from collections import deque
from app.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Глобальные данные
logs_for_site = deque(maxlen=Config.LOG_COUNT)
_ping_thread_started = False

# Класс роли
class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    users = db.relationship("User", backref="role", lazy=True)

    def __repr__(self):
        return f"<Role {self.name}>"
    

# Класс пользователя
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(80), unique = True, nullable = False)
    password_hash = db.Column(db.String(200), nullable = False)

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))

    def set_password(self, password):
        """Сохраняет хэш пароля"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Проверяет совпадение пароля с хэшем"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
    

# Класс станции
class Station(db.Model):
    __tablename__ = "stations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(50))
    location = db.Column(db.String(200))
    last_seen = db.Column(db.DateTime)

    measurements = db.relationship("Measurement", backref="station", lazy=True)
    logs = db.relationship("StationLog", backref="station", lazy=True)

    def __repr__(self):
        return f"<Station {self.name}>"
    

# Класс измерения
class Measurement(db.Model):
    __tablename__ = "measurements"

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey("stations.id"), nullable=False)

    timestamp = db.Column(db.DateTime, index=True)

    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    pressure = db.Column(db.Float)
    wind_speed = db.Column(db.Float)
    wind_direction = db.Column(db.Float)

    def __repr__(self):
        return f"<Measurement station={self.station_id} time={self.timestamp}>"
    

# Класс лога станции
class StationLog(db.Model):
    __tablename__ = "station_logs"

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey("stations.id"))

    timestamp = db.Column(db.DateTime)
    event = db.Column(db.String(100))
    message = db.Column(db.String(300))

    def __repr__(self):
        return f"<StationLog {self.event}>"