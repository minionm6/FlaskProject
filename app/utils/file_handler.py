# app/utils/file_handler.py
import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app


def allowed_file(filename):
    """Проверяет, разрешено ли расширение файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def ensure_upload_folder():
    """Создает папку для загрузок, если её нет"""
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        # Создаем .gitkeep чтобы папка сохранялась в git
        with open(os.path.join(upload_folder, '.gitkeep'), 'w') as f:
            pass
    return upload_folder


def save_uploaded_images(files, station_id):
    """Сохраняет изображения и возвращает относительный путь к папке"""
    if not files or not any(f.filename for f in files):
        return None
    
    # Убеждаемся, что папка uploads существует
    ensure_upload_folder()
    
    # Создаем уникальную папку для этой загрузки
    folder_name = f"station_{station_id}_{uuid.uuid4().hex[:8]}"
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder_name)
    
    # Создаем папку, если её нет
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)
    
    # Сохраняем файлы
    saved_count = 0
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Добавляем уникальный префикс для избежания конфликтов
            unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
            file.save(os.path.join(upload_path, unique_filename))
            saved_count += 1
    
    # Если ни один файл не был сохранен, удаляем пустую папку
    if saved_count == 0:
        os.rmdir(upload_path)
        return None
    
    return folder_name