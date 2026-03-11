from flask import render_template, request
from flask_login import login_required, current_user
from datetime import datetime as dt
from app.main import bp
from app.utils.ping_monitor import ping_device, validate_ip, get_logs


@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Главная страница со станциями"""
    return render_template('index.html')


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