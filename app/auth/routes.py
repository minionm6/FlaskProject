from flask import render_template, redirect, url_for, flash, request
from app import db
from app.models import User
from flask_login import login_user, logout_user, login_required
from app.auth import bp


@bp.route('/login', methods = ['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(username = username).first()
        if not user or not user.check_password(password):
            flash('Неправильное имя или пароль')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=remember)
        return redirect(url_for('main.index'))
    
    return render_template('auth/login.html')


@bp.route('/register', methods = ['GET', 'POST'])
def register():
    """Страница регистрации"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Проверка уникальности логина
        user_by_name = User.query.filter_by(username=username).first()
        if user_by_name:
            flash('Логин уже используется')
            return redirect(url_for('auth.register'))

        # Создание пользователя
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Вы зарегестрированы, войдите')
        return redirect(url_for('auth.login'))

    
    return render_template('auth/register.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы')
    return redirect(url_for('main.index'))