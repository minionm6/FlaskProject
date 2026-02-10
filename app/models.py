from collections import deque
from config import LOG_COUNT

# Глобальные данные (можно заменить на БД в будущем)
logs_for_site = deque(maxlen=LOG_COUNT)
_ping_thread_started = False