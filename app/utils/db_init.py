
from app.models import db, Role, User

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