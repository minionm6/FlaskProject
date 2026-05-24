# app/main/routes.py
import os
from flask import render_template, request, redirect, url_for, flash, send_from_directory, current_app
from flask_login import login_required, current_user
from datetime import datetime as dt
from app.main import bp
from app import db
from app.config import Config
from app.models import Station, Status, Equipment, MaintenanceAction
from app.utils.ping_monitor import ping_device, validate_ip, get_logs, manual_ping
from app.utils.file_handler import save_uploaded_images


@bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Отдает загруженные файлы"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Главная страница со станциями"""
    stations = Station.query.all()
    selected_station = None
    maintenance_actions = []
    
    station_id = request.args.get('station_id', type=int)
    if station_id:
        selected_station = Station.query.get(station_id)
        if selected_station:
            # Получаем последние 20 действий для выбранной станции
            maintenance_actions = MaintenanceAction.query\
                .filter_by(station_id=station_id)\
                .order_by(MaintenanceAction.action_date.desc())\
                .limit(20)\
                .all()

    # Для формы добавления
    statuses = Status.query.all()
    equipments = Equipment.query.all()

    return render_template('index.html',
                           stations=stations,
                           selected_station=selected_station,
                           maintenance_actions=maintenance_actions,
                           statuses=statuses,
                           equipments=equipments,
                           now=dt.utcnow())


@bp.route('/station/<int:station_id>/action/add', methods=['POST'])
@login_required
def add_action(station_id):
    """Добавление действия для станции"""
    # Проверка прав доступа
    if not current_user.role or current_user.role.name not in ('admin', 'operator'):
        flash('Недостаточно прав для добавления действия', 'danger')
        return redirect(url_for('main.index', station_id=station_id))
    
    station = Station.query.get_or_404(station_id)
    
    # Получаем данные из формы
    action_date_str = request.form.get('action_date')
    description = request.form.get('description')
    
    # Валидация
    if not action_date_str:
        flash('Дата выполнения обязательна', 'danger')
        return redirect(url_for('main.index', station_id=station_id))
    
    if not description:
        flash('Описание действия обязательно', 'danger')
        return redirect(url_for('main.index', station_id=station_id))
    
    try:
        action_date = dt.strptime(action_date_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Неверный формат даты', 'danger')
        return redirect(url_for('main.index', station_id=station_id))
    
    # Сохраняем изображения
    files = request.files.getlist('images')
    images_folder = save_uploaded_images(files, station_id)
    
    # Создаем запись о действии
    action = MaintenanceAction(
        station_id=station_id,
        action_date=action_date,
        description=description,
        images_folder=images_folder
    )
    
    db.session.add(action)
    db.session.commit()
    
    flash('Действие успешно добавлено', 'success')
    return redirect(url_for('main.index', station_id=station_id))


@bp.route('/stations/add', methods=['POST'])
@login_required
def add_station():
    """Добавление новой станции (только оператор/админ)"""
    # Проверка прав доступа
    if not current_user.role or current_user.role.name not in ('admin', 'operator'):
        flash('Недостаточно прав для добавления станции', 'danger')
        return redirect(url_for('main.index'))

    name = request.form.get('name')
    ip_address = request.form.get('ip_address')
    locationstr = request.form.get('locationstr')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    status_id = request.form.get('status_id')
    equipment_ids = request.form.getlist('equipment')

    # Валидация обязательных полей
    if not name:
        flash('Название станции обязательно', 'danger')
        return redirect(url_for('main.index'))

    # Создаём станцию
    station = Station(
        name=name,
        ip_address=ip_address if ip_address else None,
        locationstr=locationstr if locationstr else None,
        latitude=float(latitude) if latitude else None,
        longitude=float(longitude) if longitude else None,
        status_id=int(status_id) if status_id else None
    )

    # Добавляем оборудование
    if equipment_ids:
        selected_equipment = Equipment.query.filter(Equipment.id.in_(equipment_ids)).all()
        station.equipment.extend(selected_equipment)

    db.session.add(station)
    db.session.commit()

    flash(f'Станция "{name}" успешно добавлена', 'success')
    return redirect(url_for('main.index', station_id=station.id))


@bp.route('/log', methods=['GET', 'POST'])
def log():
    output = None
    log_count = request.args.get('count', current_app.config['LOG_COUNT'], type=int)

    # Фильтр допустимых значений
    allowed_counts = [5, 10, 25, 50, 100]
    if log_count not in allowed_counts:
        log_count = current_app.config['LOG_COUNT']

    if request.method == 'POST':
        ip = request.form.get('ip', '').strip()
        if ip:
            output = manual_ping(ip)

    return render_template(
        'log.html',
        output=output,
        logs=get_logs(count=log_count),
        log_count=log_count,
        allowed_counts=allowed_counts,
        now=dt.now(),
        target_ip=current_app.config['TARGET_IP']
    )

@bp.route('/station/<int:station_id>/equipment/add', methods=['POST'])
@login_required
def add_equipment(station_id):
    """Добавление оборудования к станции"""
    if not current_user.role or current_user.role.name not in ('admin', 'operator'):
        flash('Недостаточно прав для добавления оборудования', 'danger')
        return redirect(url_for('main.index', station_id=station_id))
    
    station = Station.query.get_or_404(station_id)
    equipment_ids = request.form.getlist('equipment')
    
    if not equipment_ids:
        flash('Выберите хотя бы одно оборудование', 'warning')
        return redirect(url_for('main.index', station_id=station_id))
    
    selected_equipment = Equipment.query.filter(Equipment.id.in_(equipment_ids)).all()
    station.equipment.extend(selected_equipment)
    db.session.commit()
    
    flash(f'Оборудование добавлено к станции "{station.name}"', 'success')
    return redirect(url_for('main.index', station_id=station_id))

@bp.route('/station/<int:station_id>/equipment/remove', methods=['POST'])
@login_required
def remove_equipment(station_id):
    """Удаление оборудования со станции (оператор/админ)"""
    if not current_user.role or current_user.role.name not in ('admin', 'operator'):
        flash('Недостаточно прав для удаления оборудования', 'danger')
        return redirect(url_for('main.index', station_id=station_id))
    
    station = Station.query.get_or_404(station_id)
    equipment_id = request.form.get('equipment_id')
    
    if not equipment_id:
        flash('Оборудование не выбрано', 'warning')
        return redirect(url_for('main.index', station_id=station_id))
    
    equipment = Equipment.query.get_or_404(int(equipment_id))
    
    if equipment in station.equipment:
        station.equipment.remove(equipment)
        db.session.commit()
        flash(f'Оборудование "{equipment.name}" удалено со станции', 'success')
    else:
        flash('Оборудование не найдено на станции', 'warning')
    
    return redirect(url_for('main.index', station_id=station_id))

# ============ API ============

from flask import jsonify
from app.models import Measurement

@bp.route('/api/stations/<int:station_id>/measurements')
@login_required
def api_measurements(station_id):
    """API: возвращает измерения станции в JSON"""
    limit = request.args.get('limit', 200, type=int)
    
    # Ограничиваем максимальный лимит
    if limit > 1000:
        limit = 1000
    
    measurements = Measurement.query\
        .filter_by(station_id=station_id)\
        .order_by(Measurement.timestamp.desc())\
        .limit(limit)\
        .all()
    
    result = []
    for m in measurements:
        result.append({
            'id': m.id,
            'station_id': m.station_id,
            'timestamp': m.timestamp.isoformat() if m.timestamp else None,
            'temperature': m.temperature,
            'humidity': m.humidity,
            'pressure': m.pressure,
            'wind_speed': m.wind_speed,
            'wind_direction': m.wind_direction,
            'precipitation': m.precipitation
        })
    
    return jsonify(result)