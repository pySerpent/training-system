"""Общие настройки приложения: пути к файлам, имена ролей, параметры тестирования.

Все пути вычисляются относительно каталога программы, поэтому проект
можно переносить на другой компьютер без правки исходного кода.
"""
import os
import sys

# Каталог, из которого запущена программа. Для собранного exe (PyInstaller)
# берётся папка исполняемого файла, для исходников - корень проекта.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Папка с базой данных SQLite. Переменная окружения IBTRAIN_DATA позволяет
# указать другую папку, например временную для автоматических тестов.
DATA_DIR = os.environ.get("IBTRAIN_DATA") or os.path.join(BASE_DIR, "data")
# Файл базы данных
DB_PATH = os.path.join(DATA_DIR, "ib_training.db")
# Папка для выгружаемых отчётов по умолчанию
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
# Папка для резервных копий базы
BACKUP_DIR = os.path.join(BASE_DIR, "backup")
# Текстовый журнал ошибок (дублирует таблицу logs для аварийных ситуаций)
LOG_FILE = os.path.join(DATA_DIR, "app.log")

# Название приложения в заголовках окон
APP_TITLE = "Корпоративная система обучения и контроля знаний по ИБ"
APP_VERSION = "1.0.0"

# Автор работы (выводится в окне «Справка»)
AUTHOR_NAME = "Зверев Евгений Александрович"

# Коды ролей. Названия ролей хранятся в таблице roles.
ROLE_ADMIN = "admin"
ROLE_TEACHER = "teacher"
ROLE_EMPLOYEE = "employee"

ROLE_TITLES = {
    ROLE_ADMIN: "Администратор",
    ROLE_TEACHER: "Преподаватель",
    ROLE_EMPLOYEE: "Сотрудник",
}

# Типы вопросов
QTYPE_SINGLE = "single"
QTYPE_MULTI = "multi"
QTYPE_TITLES = {
    QTYPE_SINGLE: "Одиночный выбор",
    QTYPE_MULTI: "Множественный выбор",
}

# Значения настроек по умолчанию (таблица settings)
DEFAULT_SETTINGS = {
    "company_name": "ООО «ГМС ИТ»",
    "logo_path": "",
    "theme": "light",
    "color_theme": "blue",
    "pass_threshold": "70",
    "test_time_min": "15",
    "questions_per_test": "10",
    "max_attempts": "3",
}

# Количество неудачных попыток входа до временной блокировки
MAX_LOGIN_FAILS = 5


def ensure_dirs():
    """Создаёт рабочие папки, если их ещё нет."""
    for path in (DATA_DIR, REPORTS_DIR, BACKUP_DIR):
        os.makedirs(path, exist_ok=True)
