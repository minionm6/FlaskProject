from collections import deque
from app.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Глобальные переменные
logs_for_site = deque(maxlen=Config.LOG_COUNT)
_ping_thread_started = False

# Класс роли
class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    users = db.relationship("User", backref="role", lazy=True)

    def __repr__(self):
        return f"<Role {self.name}>"
    

# Класс пользователя
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def role_name(self):
        return self.role.name if self.role else None
    
    def is_admin(self):
        return self.role_name == 'admin'
    
    def is_operator(self):
        return self.role_name == 'operator'
    

# Класс станции 
class Station(db.Model):
    __tablename__ = "stations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45))                     
    locationstr = db.Column(db.String(200))                   
    latitude = db.Column(db.Float)                            
    longitude = db.Column(db.Float)                           

    status_id = db.Column(db.Integer, db.ForeignKey("statuses.id"), index=True)
    status = db.relationship("Status", backref="stations")

    measurements = db.relationship(
        "Measurement", backref="station", lazy=True,
        cascade="all, delete-orphan"
    )

    equipment = db.relationship(
        "Equipment", secondary="station_equipment",
        backref=db.backref("stations", lazy="dynamic")
    )

    def __repr__(self):
        return f"<Station {self.name}>"
    

# Класс статуса станции
class Status(db.Model):
    __tablename__ = "statuses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Status {self.name}>"


# Класс оборудования станции
class Equipment(db.Model):
    __tablename__ = "equipments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Equipment {self.name}>"


station_equipment = db.Table(
    "station_equipment",
    db.Column("station_id", db.Integer, db.ForeignKey("stations.id"), primary_key=True),
    db.Column("equipment_id", db.Integer, db.ForeignKey("equipments.id"), primary_key=True)
)


# Класс измерения
class Measurement(db.Model):
    __tablename__ = "measurements"

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(
        db.Integer, db.ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    timestamp = db.Column(db.DateTime, index=True, nullable=False)

    temperature = db.Column(db.Float)

    __table_args__ = (
        db.UniqueConstraint("station_id", "timestamp", name="_station_time_uc"),
    )

    def __repr__(self):
        return f"<Measurement station={self.station_id} time={self.timestamp}>"