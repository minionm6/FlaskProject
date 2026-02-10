import subprocess
import time
import re
import ipaddress
from datetime import datetime as dt
from collections import deque
import threading
from app.config import Config

# Глобальные переменные для хранения состояния
logs_for_site = deque(maxlen=Config.LOG_COUNT)
_ping_thread_started = False


def validate_ip(ip: str):
    '''Проверяет на правильность ввода IP-адреса'''
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def ping_device(ip: str):
    """Пингует IP и возвращает статус + одну строку статистики"""
    if not validate_ip(ip):
        return "[ERROR] Invalid IP address format"
    
    if not re.match(r'^[\d\.]+$', ip):
        return "[ERROR] Invalid characters in IP address"
    
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
            case 0:  # Код 0 - адрес доступен
                status = "REACHABLE"
            case 1:  # Код 1 - адрес недоступен
                status = "UNREACHABLE"
            case 2:  # Код 2 - ошибка, причина в stderr
                status = f"SYSTEM ERROR ({result.stderr.strip()})"
            case _:  # Неопознанный код
                status = f"UNKNOWN CODE {result.returncode}"

        return f"[{status}] {stats_line}"

    except subprocess.TimeoutExpired:
        return "[TIMEOUT] Device did not respond in time"
    except Exception as e:
        return f"[ERROR] {e}"


def process_ping_logging():
    """Пингует целевой IP каждые N минут и записывает в файл и на сайт"""
    while True:
        ping_result = ping_device(Config.TARGET_IP)
        
        # Формирование данных
        log_now = f"\nTime - {dt.now().strftime('%d-%m-%Y %H:%M:%S')}\n{ping_result}\n"
        
        try:
            # Запись в файл
            with open(Config.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_now)
            
            # Передача данных на сайт
            logs_for_site.appendleft(log_now)
        except Exception as e:
            print(f"Ошибка записи лога: {e}")

        time.sleep(Config.PING_INTERVAL)


def start_ping_monitoring():
    """Безопасный запуск мониторинга в отдельном потоке"""
    global _ping_thread_started
    
    # Для исключения дублирования потоков
    if not _ping_thread_started:
        thread = threading.Thread(target=process_ping_logging, daemon=True)
        thread.start()
        _ping_thread_started = True
        print("Ping monitoring started")


def get_logs():
    """Возвращает текущие логи для отображения"""
    return list(logs_for_site)