"""Авторизация и проверка прав доступа."""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from .. import config
from ..database import session_scope
from ..models import User
from ..security import hash_password, password_problems, verify_password
from . import journal


class AuthError(Exception):
    """Ошибка входа с понятным пользователю текстом."""


@dataclass
class CurrentUser:
    """Сведения о вошедшем пользователе, которые нужны интерфейсу."""
    id: int
    login: str
    full_name: str
    role: str
    role_title: str
    department: str


# Права ролей. Интерфейс показывает только разрешённые разделы.
PERMISSIONS = {
    config.ROLE_ADMIN: {"dashboard", "users", "courses", "questions", "tests",
                        "results", "export", "settings", "logs", "profile",
                        "help", "comment"},
    config.ROLE_TEACHER: {"dashboard", "courses", "questions", "tests",
                          "results", "export", "profile", "help", "comment"},
    config.ROLE_EMPLOYEE: {"dashboard", "tests", "results", "profile", "help"},
}


def can(user: CurrentUser, permission: str) -> bool:
    """Проверяет, разрешено ли действие роли пользователя."""
    return permission in PERMISSIONS.get(user.role, set())


def login(login_name: str, password: str) -> CurrentUser:
    """Проверяет логин и пароль, возвращает текущего пользователя."""
    login_name = login_name.strip()
    if not login_name or not password:
        raise AuthError("Введите логин и пароль")
    with session_scope() as s:
        user = s.scalar(select(User).where(User.login == login_name))
        if user is None:
            journal.write("login_fail", f"неизвестный логин {login_name}")
            raise AuthError("Неверный логин или пароль")
        if user.is_blocked:
            journal.write("login_fail", "учётная запись заблокирована", user.id)
            raise AuthError("Учётная запись заблокирована. "
                            "Обратитесь к администратору")
        if verify_password(password, user.password_hash):
            user.failed_logins = 0
            user.last_login = datetime.now()
            current = CurrentUser(user.id, user.login, user.full_name,
                                  user.role.code, user.role.title,
                                  user.department.name if user.department else "")
        else:
            # Счётчик меняется внутри сессии, а исключение поднимается после
            # выхода из неё: иначе откат транзакции отменил бы и счётчик.
            current = None
            user.failed_logins += 1
            fails, user_id = user.failed_logins, user.id
            # после серии неудачных попыток запись блокируется
            if fails >= config.MAX_LOGIN_FAILS:
                user.is_blocked = True
    if current is None:
        if fails >= config.MAX_LOGIN_FAILS:
            journal.write("user_block", f"автоблокировка после {fails} попыток", user_id)
        journal.write("login_fail", "неверный пароль", user_id)
        raise AuthError("Неверный логин или пароль")
    journal.write("login", "успешный вход", current.id)
    return current


def change_password(user_id: int, old: str, new: str, repeat: str):
    """Смена пароля из личного кабинета."""
    if new != repeat:
        raise AuthError("Новый пароль и повтор не совпадают")
    problems = password_problems(new)
    if problems:
        raise AuthError("Пароль должен содержать: " + ", ".join(problems))
    with session_scope() as s:
        user = s.get(User, user_id)
        if user is None or not verify_password(old, user.password_hash):
            raise AuthError("Текущий пароль введён неверно")
        user.password_hash = hash_password(new)
    journal.write("user_edit", "смена пароля", user_id)
