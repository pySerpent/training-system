"""Чтение и сохранение настроек системы (таблица settings)."""
import os
import shutil
from datetime import datetime

from sqlalchemy import select

from .. import config
from ..database import session_scope
from ..models import Setting


def get_all() -> dict:
    """Все настройки; отсутствующие ключи берутся из значений по умолчанию."""
    values = dict(config.DEFAULT_SETTINGS)
    with session_scope() as s:
        for item in s.scalars(select(Setting)):
            values[item.key] = item.value
    return values


def get(key: str) -> str:
    """Одна настройка по ключу."""
    return get_all().get(key, "")


def get_int(key: str, default: int) -> int:
    """Числовая настройка; при ошибке формата возвращается значение по умолчанию."""
    try:
        return int(get(key))
    except ValueError:
        return default


def save(values: dict):
    """Сохраняет переданные пары ключ - значение."""
    with session_scope() as s:
        for key, value in values.items():
            item = s.scalar(select(Setting).where(Setting.key == key))
            if item is None:
                s.add(Setting(key=key, value=str(value)))
            else:
                item.value = str(value)


def validate(values: dict) -> list[str]:
    """Проверяет введённые администратором значения."""
    errors = []
    if not values.get("company_name", "").strip():
        errors.append("Название компании не может быть пустым")
    limits = {"pass_threshold": (1, 100, "Проходной балл"),
              "test_time_min": (1, 180, "Время на тест"),
              "questions_per_test": (1, 100, "Число вопросов"),
              "max_attempts": (1, 20, "Число попыток")}
    for key, (low, high, title) in limits.items():
        try:
            number = int(values.get(key, ""))
        except ValueError:
            errors.append(f"{title}: нужно целое число")
            continue
        if not low <= number <= high:
            errors.append(f"{title}: допустимо от {low} до {high}")
    logo = values.get("logo_path", "")
    if logo and not os.path.isfile(logo):
        errors.append("Файл логотипа не найден")
    return errors


def backup_database(target_dir: str | None = None) -> str:
    """Копирует файл базы в папку резервных копий и возвращает путь копии."""
    target_dir = target_dir or config.BACKUP_DIR
    os.makedirs(target_dir, exist_ok=True)
    name = f"ib_training_{datetime.now():%Y%m%d_%H%M%S}.db"
    path = os.path.join(target_dir, name)
    shutil.copy2(config.DB_PATH, path)
    return path
