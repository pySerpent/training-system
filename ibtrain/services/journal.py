"""Журнал действий пользователей: запись в таблицу logs и в текстовый файл."""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from .. import config
from ..database import session_scope
from ..models import Log, User

# Файловый журнал нужен на случай, когда сама база недоступна
logging.basicConfig(filename=config.LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s",
                    encoding="utf-8")
_file_log = logging.getLogger("ibtrain")

# Коды действий, которые фиксируются в журнале
ACTIONS = {
    "login": "Вход в систему",
    "login_fail": "Неудачный вход",
    "logout": "Выход из системы",
    "test_start": "Начало теста",
    "test_finish": "Завершение теста",
    "user_create": "Создание пользователя",
    "user_edit": "Изменение пользователя",
    "user_block": "Блокировка пользователя",
    "user_delete": "Удаление пользователя",
    "course_edit": "Изменение курса",
    "question_edit": "Изменение вопроса",
    "comment": "Комментарий к результату",
    "export": "Выгрузка отчёта",
    "settings": "Изменение настроек",
    "backup": "Резервная копия БД",
    "error": "Ошибка",
}


def write(action: str, details: str = "", user_id: int | None = None,
          level: str = "INFO"):
    """Добавляет запись в журнал. Сбой записи не должен ронять программу."""
    _file_log.log(logging.ERROR if level == "ERROR" else logging.INFO,
                  "%s user=%s %s", action, user_id, details)
    try:
        with session_scope() as s:
            s.add(Log(user_id=user_id, action=action, details=details[:1000],
                      level=level))
    except Exception as exc:  # база может быть заблокирована
        _file_log.error("не удалось записать журнал: %s", exc)


def error(details: str, user_id: int | None = None):
    """Короткая запись об ошибке."""
    write("error", details, user_id, "ERROR")


def fetch(days: int = 30, action: str | None = None,
          text: str = "") -> list[dict]:
    """Возвращает записи журнала за период с необязательными фильтрами."""
    since = datetime.now() - timedelta(days=days)
    with session_scope() as s:
        q = (select(Log, User.login).outerjoin(User, Log.user_id == User.id)
             .where(Log.created_at >= since).order_by(Log.created_at.desc()))
        if action:
            q = q.where(Log.action == action)
        rows = []
        for log, login in s.execute(q).all():
            if text and text.lower() not in (log.details or "").lower() \
                    and text.lower() not in (login or "").lower():
                continue
            rows.append({
                "time": log.created_at.strftime("%d.%m.%Y %H:%M:%S"),
                "login": login or "-",
                "action": ACTIONS.get(log.action, log.action),
                "level": log.level,
                "details": log.details,
            })
        return rows
