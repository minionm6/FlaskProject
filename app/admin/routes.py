from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.admin import bp
from app import db
from app.models import User, Role, Station, Status, Equipment

def admin_required(func):
    """Декоратор для ограничения доступа только администраторам"""
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Доступ запрещен. Требуются права администратора.', 'danger')
            return redirect(url_for('main.index'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@bp.route('/settings')
@login_required
@admin_required
def settings():
    users = User.query.all()
    stations = Station.query.all()
    statuses = Status.query.all()
    equipments = Equipment.query.all()
    roles = Role.query.all()
    return render_template('admin/settings.html',
                           users=users, stations=stations,
                           statuses=statuses, equipments=equipments,
                           roles=roles)

@bp.route('/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    username = request.form.get('username')
    password = request.form.get('password')
    role_id = request.form.get('role_id')
    if not username or not password:
        flash('Имя пользователя и пароль обязательны', 'danger')
        return redirect(url_for('admin.settings'))
    if User.query.filter_by(username=username).first():
        flash('Пользователь с таким именем уже существует', 'danger')
        return redirect(url_for('admin.settings'))
    user = User(username=username)
    user.set_password(password)
    if role_id:
        user.role_id = int(role_id)
    db.session.add(user)
    db.session.commit()
    flash(f'Пользователь {username} добавлен', 'success')
    return redirect(url_for('admin.settings'))

@bp.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    role_id = request.form.get('role_id')
    if user.id == current_user.id and role_id and int(role_id) != user.role_id:
        flash('Нельзя изменить свою роль', 'danger')
        return redirect(url_for('admin.settings'))
    if role_id:
        user.role_id = int(role_id)
    db.session.commit()
    flash(f'Роль пользователя {user.username} обновлена', 'success')
    return redirect(url_for('admin.settings'))

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Нельзя удалить самого себя', 'danger')
        return redirect(url_for('admin.settings'))
    db.session.delete(user)
    db.session.commit()
    flash(f'Пользователь {user.username} удален', 'success')
    return redirect(url_for('admin.settings'))

@bp.route('/stations/add', methods=['POST'])
@login_required
@admin_required
def add_station():
    name = request.form.get('name')
    ip_address = request.form.get('ip_address')
    locationstr = request.form.get('locationstr')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    status_id = request.form.get('status_id')
    equipment_ids = request.form.getlist('equipment')
    if not name:
        flash('Название станции обязательно', 'danger')
        return redirect(url_for('admin.settings'))
    station = Station(
        name=name,
        ip_address=ip_address or None,
        locationstr=locationstr or None,
        latitude=float(latitude) if latitude else None,
        longitude=float(longitude) if longitude else None,
        status_id=int(status_id) if status_id else None
    )
    if equipment_ids:
        selected_equipment = Equipment.query.filter(Equipment.id.in_(equipment_ids)).all()
        station.equipment.extend(selected_equipment)
    db.session.add(station)
    db.session.commit()
    flash(f'Станция "{name}" успешно добавлена', 'success')
    return redirect(url_for('admin.settings'))

@bp.route('/stations/<int:station_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_station(station_id):
    station = Station.query.get_or_404(station_id)
    station.name = request.form.get('name', station.name)
    station.ip_address = request.form.get('ip_address') or None
    station.locationstr = request.form.get('locationstr') or None
    lat = request.form.get('latitude')
    lng = request.form.get('longitude')
    station.latitude = float(lat) if lat else None
    station.longitude = float(lng) if lng else None
    status_id = request.form.get('status_id')
    station.status_id = int(status_id) if status_id else None
    equipment_ids = request.form.getlist('equipment')
    station.equipment.clear()
    if equipment_ids:
        selected_equipment = Equipment.query.filter(Equipment.id.in_(equipment_ids)).all()
        station.equipment.extend(selected_equipment)
    db.session.commit()
    flash(f'Станция {station.name} обновлена', 'success')
    return redirect(url_for('admin.settings'))

@bp.route('/stations/<int:station_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_station(station_id):
    station = Station.query.get_or_404(station_id)
    db.session.delete(station)
    db.session.commit()
    flash(f'Станция {station.name} удалена', 'success')
    return redirect(url_for('admin.settings'))