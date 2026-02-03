from flask import Flask, render_template, request
import subprocess
from datetime import datetime as dt
import time
from collections import deque
import threading

app = Flask(__name__)

def ping_device(ip: str):
    """Пингует айпи адрес или сайт"""
    try:
        result = subprocess.run(
            ["ping", "-c", "4", ip],
            capture_output=True,
            text=True,
            timeout=15
        )
        print(f"Command executed: {result.args}")
        print(f"Return code: {result.returncode}")
        print(f"Standard output:\n{result.stdout}")
        print(f"Standard error:\n{result.stderr}")
        if result.returncode == 0:
            
            return f"--- {ip} is reachable ---{result.stdout}\n"
            
        else:
            return f"--- {ip} is unreachable ---{result.stderr}\n"

    except subprocess.TimeoutExpired:
        return f"--- {ip} timed out ---"
    except Exception as e:
        return f"--- Error with {ip}: {e} ---"

logs_for_site = deque(maxlen=6)
def ping_log():
    """Пингует 10.10.0.187 каждые 10 минут и записывает в файл и на сайт"""
    while True:
        log_now = f"Time - {dt.now()}\n{ping_device('10.10.0.187')}\n\n"
        with open("ping_log.txt", "a", encoding="utf-8") as f:
            f.write(log_now)
        logs_for_site.appendleft(log_now)
        time.sleep(600)
    

threading.Thread(target=ping_log, daemon=True).start()

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
    app.run(debug = True)
