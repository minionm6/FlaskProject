from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime as dt
from app.main import bp
from app import db
from app.models import Station, Status, Equipment
from app.utils.ping_monitor import ping_device, validate_ip, get_logs


@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Главная страница со станциями"""
    stations = Station.query.all()
    selected_station = None
    station_id = request.args.get('station_id', type=int)
    if station_id:
        selected_station = Station.query.get(station_id)

    # Для формы добавления
    statuses = Status.query.all()
    equipments = Equipment.query.all()

    return render_template('index.html',
                           stations=stations,
                           selected_station=selected_station,
                           statuses=statuses,
                           equipments=equipments,
                           now=dt.utcnow())


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
    """Страница с формой пинга и пинг-мониторинга"""
    now = dt.now()
    output = ""
    if request.method == 'POST':
        ip = request.form.get('ip')
        if ip and validate_ip(ip):
            output = ping_device(ip)
        else:
            output = "Invalid IP address"
    logs = get_logs()
    return render_template('log.html', logs=logs, user=current_user, output=output, now=now)