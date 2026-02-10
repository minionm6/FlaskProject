from flask import render_template
from app.auth import bp


@bp.route('/login')
def login():
    """Страница входа (заглушка)"""
    return render_template('auth/login.html')


@bp.route('/register')
def register():
    """Страница регистрации (заглушка)"""
    return render_template('auth/register.html')