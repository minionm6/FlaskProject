
from app.models import db, Role, User, Equipment, Status


def create_roles():
    """Создание базовых ролей, если их нет."""
    roles = ["admin", "operator", "viewer"]
    for r in roles:
        role = Role.query.filter_by(name=r).first()
        if not role:
            role = Role(name=r)
            db.session.add(role)
    db.session.commit()


def create_admin():
    """Создание администратора, если его нет."""
    
    admin_role = Role.query.filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin")
        db.session.add(admin_role)
        db.session.commit()

    user = User.query.filter_by(username="admin").first()
    if not user:
        admin = User(username="admin")
        
        admin.set_password("admin123")
        admin.role = admin_role
        db.session.add(admin)
        db.session.commit()


def create_statuses():
    """Создаёт базовые статусы станций"""

    statuses = ['Online', 'Offline']
    for name in statuses:
        if not Status.query.filter_by(name=name).first():
            db.session.add(Status(name=name))
    db.session.commit()

def create_equipments():
    """Создаёт базовые типы оборудования"""

    equipments = ['Термометр', 'Барометр']
    for name in equipments:
        if not Equipment.query.filter_by(name=name).first():
            db.session.add(Equipment(name=name))
    db.session.commit()