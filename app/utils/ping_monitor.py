import subprocess
import re
import ipaddress
import threading
import time
import json
import os
from datetime import datetime as dt, timezone
from collections import deque

from app.config import Config
from app import db
from app.models import Station, Measurement, Status

# Глобальные переменные
logs_for_site = deque(maxlen=Config.LOG_COUNT)
_ping_thread_started = False

REMOTE_DB_PATH = "/root/station_data.db"

# Путь к SSH-ключу
SSH_KEY_PATH = os.path.expanduser("~/.ssh/id_rsa_station")
SSH_USERNAME = "root"


def write_log_to_file(log_text: str):
    """Дописывает лог-запись в файл. Записи разделяются пустой строкой."""
    try:
        with open(Config.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_text.strip() + "\n\n")
    except Exception as e:
        print(f"[ERROR] Cannot write to log file: {e}")

def read_logs_from_file(count: int = None) -> list:
    if count is None:
        count = Config.LOG_COUNT
    try:
        if not os.path.exists(Config.LOG_FILE):
            return []
        with open(Config.LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        entries = content.strip().split("\n\n")
        return list(reversed(entries[-count:]))
    except Exception as e:
        print(f"[ERROR] Cannot read log file: {e}")
        return []


def validate_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def ping_device(ip: str) -> tuple:
    if not validate_ip(ip):
        return ("INVALID_IP", "Invalid IP address format")
    if not re.match(r'^[\d\.]+$', ip):
        return ("INVALID_IP", "Invalid characters in IP address")

    try:
        result = subprocess.run(
            ["ping", "-c", "4", ip],
            capture_output=True, text=True, timeout=15
        )
        stats_match = re.search(r"(\d+ packets transmitted.*)", result.stdout)
        stats_line = stats_match.group(1) if stats_match else "No stats found"

        if result.returncode == 0:
            status = "REACHABLE"
        elif result.returncode == 1:
            status = "UNREACHABLE"
        else:
            status = f"ERROR_{result.returncode}"

        return (status, stats_line)
    except subprocess.TimeoutExpired:
        return ("TIMEOUT", "Device did not respond in time")
    except Exception as e:
        return ("ERROR", str(e))


def test_ssh_connection(ip: str, username: str = None, timeout: int = 10) -> tuple:
    """Проверяет SSH-подключение с использованием ключа."""
    if username is None:
        username = SSH_USERNAME
    
    try:
        result = subprocess.run(
            ["ssh", 
             "-i", SSH_KEY_PATH,  # Используем ключ
             "-o", "ConnectTimeout=5", 
             "-o", "StrictHostKeyChecking=accept-new",
             "-o", "BatchMode=yes",  # Не запрашивать пароль
             "-o", "PasswordAuthentication=no",  # Запретить вход по паролю
             f"{username}@{ip}", 
             "echo 'SSH_OK'"],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0 and "SSH_OK" in result.stdout:
            return (True, "SSH connection successful")
        else:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            return (False, f"SSH failed: {error_msg}")
    except subprocess.TimeoutExpired:
        return (False, "SSH connection timed out")
    except Exception as e:
        return (False, str(e))


def find_station_by_ip(ip: str):
    return Station.query.filter_by(ip_address=ip).first()


def fetch_measurements_by_ssh(ip: str, username: str = None, limit: int = 200) -> list:
    """Забирает измерения с удаленной станции."""
    if username is None:
        username = SSH_USERNAME
    
    sql_query = f"""
    sqlite3 {REMOTE_DB_PATH} "
    SELECT station_id, timestamp, temperature, humidity, pressure, 
           wind_speed, wind_direction, precipitation
    FROM measurements
    ORDER BY timestamp DESC
    LIMIT {limit};
    "
    """
    try:
        result = subprocess.run(
            ["ssh", 
             "-i", SSH_KEY_PATH,
             "-o", "ConnectTimeout=10", 
             "-o", "StrictHostKeyChecking=accept-new",
             "-o", "BatchMode=yes",
             f"{username}@{ip}", 
             sql_query],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # Пробуем распарсить CSV (старый формат)
                return _parse_csv_output(result.stdout)
        else:
            if result.stderr:
                print(f"[SSH ERROR] {result.stderr.strip()}")
            return []
    except subprocess.TimeoutExpired:
        print(f"[SSH TIMEOUT] Connection to {ip} timed out")
        return []
    except Exception as e:
        print(f"[SSH ERROR] {e}")
        return []


def _parse_csv_output(output: str) -> list:
    """Парсит CSV вывод sqlite (старый формат без -json)."""
    results = []
    for line in output.strip().split("\n"):
        parts = line.split("|")
        if len(parts) >= 4:
            try:
                measurement = {
                    "station_id": int(parts[0].strip()),
                    "timestamp": parts[1].strip(),
                    "temperature": float(parts[2]) if parts[2].strip() else None,
                    "humidity": float(parts[3]) if len(parts) > 3 and parts[3].strip() else None,
                    "pressure": float(parts[4]) if len(parts) > 4 and parts[4].strip() else None,
                    "wind_speed": float(parts[5]) if len(parts) > 5 and parts[5].strip() else None,
                    "wind_direction": float(parts[6]) if len(parts) > 6 and parts[6].strip() else None,
                    "precipitation": float(parts[7]) if len(parts) > 7 and parts[7].strip() else None,
                }
                results.append(measurement)
            except (ValueError, IndexError) as e:
                continue
    return results


def push_measurements_to_local_db(station_id: int, measurements: list) -> int:
    """Сохраняет измерения в локальную БД."""
    new_count = 0
    for m in measurements:
        try:
            ts_str = m.get("timestamp", "")
            if not ts_str:
                continue
            
            # Пробуем разные форматы даты
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]:
                try:
                    ts = dt.strptime(ts_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                continue
            
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            
            existing = Measurement.query.filter_by(
                station_id=station_id, timestamp=ts
            ).first()
            
            if existing is None:
                measurement = Measurement(
                    station_id=station_id, 
                    timestamp=ts,
                    temperature=m.get("temperature"),
                    humidity=m.get("humidity"),
                    pressure=m.get("pressure"),
                    wind_speed=m.get("wind_speed"),
                    wind_direction=m.get("wind_direction"),
                    precipitation=m.get("precipitation")
                )
                db.session.add(measurement)
                new_count += 1
        except Exception as e:
            print(f"[ERROR] Failed to save measurement: {e}")
            continue
    
    if new_count > 0:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Failed to commit measurements: {e}")
    
    return new_count


def update_station_status(station_id: int, reachable: bool):
    """Обновляет статус станции."""
    try:
        station = db.session.get(Station, station_id)
        if not station:
            return
        status_name = "Online" if reachable else "Offline"
        status_obj = Status.query.filter_by(name=status_name).first()
        if not status_obj:
            status_obj = Status(name=status_name)
            db.session.add(status_obj)
            db.session.commit()
        station.status_id = status_obj.id
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] update_station_status: {e}")


def process_single_station(station) -> str:
    """Обрабатывает одну станцию: пинг, SSH, забор данных."""
    if not station.ip_address:
        return None

    log_time = dt.now().strftime("%d-%m-%Y %H:%M:%S")
    ping_status, ping_stats = ping_device(station.ip_address)
    reachable = (ping_status == "REACHABLE")

    log_entry = f"Time - {log_time}\n[{ping_status}] {ping_stats}\n"

    if not reachable:
        update_station_status(station.id, False)
        log_entry += f"Station {station.name} is offline.\n"
    else:
        ssh_ok, ssh_msg = test_ssh_connection(station.ip_address)
        if not ssh_ok:
            update_station_status(station.id, False)
            log_entry += f"[SSH ERROR] {ssh_msg}\n"
        else:
            update_station_status(station.id, True)
            measurements = fetch_measurements_by_ssh(station.ip_address)
            if measurements:
                new_count = push_measurements_to_local_db(station.id, measurements)
                log_entry += f"[DATA] Received {len(measurements)} measurements, {new_count} new.\n"
            else:
                log_entry += "[DATA] No measurements received.\n"

    write_log_to_file(log_entry.strip())
    logs_for_site.appendleft(log_entry)

    return log_entry


def process_all_stations():
    """Основная логика одного цикла проверки всех станций."""
    stations = Station.query.all()
    for station in stations:
        log_entry = process_single_station(station)
        if log_entry:
            print(log_entry.strip())


def background_monitoring_loop(app):
    """Фоновый цикл мониторинга."""
    while True:
        try:
            with app.app_context():
                process_all_stations()
        except Exception as e:
            error_log = (
                f"Time - {dt.now().strftime('%d-%m-%Y %H:%M:%S')}\n"
                f"[ERROR] Monitoring cycle error: {e}\n"
            )
            write_log_to_file(error_log.strip())
            logs_for_site.appendleft(error_log)
            print(error_log.strip())
        time.sleep(Config.PING_INTERVAL)


def start_ping_monitoring(app):
    """Безопасный запуск фонового мониторинга."""
    global _ping_thread_started
    if not _ping_thread_started:
        thread = threading.Thread(
            target=lambda: background_monitoring_loop(app), 
            daemon=True
        )
        thread.start()
        _ping_thread_started = True
        print("[PING SERVICE] Background monitoring of all stations started.")


def get_logs(count: int = None):
    """Возвращает последние логи."""
    if count is None:
        count = Config.LOG_COUNT
    return read_logs_from_file(count)


def manual_ping(ip: str) -> str:
    """Ручной пинг с использованием ключа."""
    if not validate_ip(ip):
        result = "[ERROR] Invalid IP address format"
        write_log_to_file(result)
        logs_for_site.appendleft(result)
        return result

    log_time = dt.now().strftime("%d-%m-%Y %H:%M:%S")
    ping_status, ping_stats = ping_device(ip)
    result = f"Time - {log_time}\n[{ping_status}] {ping_stats}\n"

    station = find_station_by_ip(ip)

    if ping_status == "REACHABLE":
        if station:
            result += f"[INFO] IP belongs to station: {station.name}\n"
            ssh_ok, ssh_msg = test_ssh_connection(ip)
            if ssh_ok:
                result += "[SSH] Connection successful (key auth).\n"
                measurements = fetch_measurements_by_ssh(ip, limit=10)
                if measurements:
                    new_count = push_measurements_to_local_db(station.id, measurements)
                    result += f"[DATA] Fetched {len(measurements)} measurements, {new_count} new.\n"
                else:
                    result += "[DATA] No data received from station.\n"
                update_station_status(station.id, True)
            else:
                result += f"[SSH ERROR] {ssh_msg}\n"
                update_station_status(station.id, False)
        else:
            result += "[INFO] This IP does not belong to any known station.\n"
    else:
        result += "[INFO] Device is unreachable.\n"
        if station:
            update_station_status(station.id, False)
            result += f"[INFO] Station '{station.name}' marked as offline.\n"

    write_log_to_file(result.strip())
    logs_for_site.appendleft(result)

    return result