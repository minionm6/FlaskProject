from flask import Flask, render_template, request
import subprocess
from datetime import datetime as dt
import time
from collections import deque
import threading
import re

app = Flask(__name__)


def ping_device(ip: str):
    """Пингует IP и возвращает статус + одну строку статистики"""

    try:
        
        result = subprocess.run(
            ["ping", "-c", "4", ip],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        # Выводит только строку со статистикой пакетов
        stats_match = re.search(r"(\d+ packets transmitted.*)", result.stdout)  
        stats_line = stats_match.group(1) if stats_match else "No stats found"

        match result.returncode:
            case 0: # Код 0 - адрес доступен
                status = "REACHABLE"
            case 1: # Код 1 - адрес недоступен
                status = "UNREACHABLE"
            case 2: # Код 2 - ошибка, причина в stderr
                status = f"SYSTEM ERROR ({result.stderr.strip()})"
            case _: # Неопознанный код
                status = f"UNKNOWN CODE {result.returncode}"

        return f"[{status}] {stats_line}"

    except subprocess.TimeoutExpired:
        return "[TIMEOUT] Device did not respond in time"
    except Exception as e:
        return f"[ERROR] {e}"


logs_for_site = deque(maxlen=6) # Дэк для вывода последних логов на сайт
_ping_thread_started = False    # Проверяет, запущен ли поток логирования или нет


def process_ping_logging():
    """Пингует 10.10.0.187 каждые 10 минут и записывает в файл и на сайт"""
    
    while True:
        
        ping_result = ping_device('10.10.0.187')    
        # Формирование данных
        log_now = f"\nTime - {dt.now().strftime('%d-%m-%Y %H:%M:%S')}\n{ping_result}\n"   
        
        
        try:
            # Запись в файл
            with open("ping_log.txt", "a", encoding="utf-8") as f:
                f.write(log_now)
            
            # Передача данных на сайт
            logs_for_site.appendleft(log_now)
        except Exception as e:
            print(f"Ошибка записи лога: {e}")

        time.sleep(5)


def start_ping_monitoring():
    """Безопасный запуск мониторинга в отдельном потоке"""

    global _ping_thread_started
    # Для исключения дублирования потоков
    if not _ping_thread_started:    
        thread = threading.Thread(target=process_ping_logging, daemon=True)
        thread.start()
        _ping_thread_started = True
    

@app.route('/', methods=['GET', 'POST'])
def index():
    output = ""
    if request.method == 'POST':
        ip = request.form.get('ip')
        if ip:
            output = ping_device(ip)
    return render_template('index.html', output=output)


@app.route('/log', methods=['GET', 'POST'])
def log():
    return render_template('log.html', logs=list(logs_for_site))


if __name__ == '__main__':
    start_ping_monitoring()
    app.run(debug = True, use_reloader=False)
