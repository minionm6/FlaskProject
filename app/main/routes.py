from flask import render_template, request
from datetime import datetime as dt
from app.main import bp
from app.utils.ping_monitor import ping_device, validate_ip, get_logs


@bp.route('/', methods=['GET', 'POST'])
def index():
    """Главная страница с формой пингования"""
    now = dt.now()
    output = ""
    
    if request.method == 'POST':
        ip = request.form.get('ip')
        if ip and validate_ip(ip):
            output = ping_device(ip)
        else:
            output = "Invalid IP address"
    
    return render_template('index.html', output=output, now=now)


@bp.route('/log')
def log():
    """Страница с логами пинг-мониторинга"""
    logs = get_logs()
    return render_template('log.html', logs=logs)