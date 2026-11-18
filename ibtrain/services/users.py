"""Управление учётными записями сотрудников (раздел администратора)."""
import re

from sqlalchemy import func, select

from ..database import session_scope
from ..models import Department, Role, Test, User
from ..security import hash_password, password_problems
from . import journal

LOGIN_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.]{2,29}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


class ValidationError(Exception):
    """Ошибка данных формы со списком замечаний."""


def list_users(text: str = "", role_code: str = "") -> list[dict]:
    """Список пользователей для таблицы с фильтром по ФИО, логину и роли."""
    with session_scope() as s:
        q = select(User).join(Role).order_by(User.full_name)
        if role_code:
            q = q.where(Role.code == role_code)
        if text:
            pattern = f"%{text.strip()}%"
            q = q.where(User.full_name.like(pattern) | User.login.like(pattern))
        return [{
            "id": u.id, "full_name": u.full_name, "login": u.login,
            "role": u.role.title, "role_code": u.role.code,
            "department": u.department.name if u.department else "",
            "position": u.position, "email": u.email,
            "status": "Заблокирован" if u.is_blocked else "Активен",
            "last_login": u.last_login.strftime("%d.%m.%Y %H:%M")
            if u.last_login else "-",
        } for u in s.scalars(q)]


def roles() -> list[tuple[str, str]]:
    """Пары (код, название) всех ролей."""
    with session_scope() as s:
        return [(r.code, r.title) for r in s.scalars(select(Role).order_by(Role.id))]


def departments() -> list[str]:
    """Названия подразделений по алфавиту."""
    with session_scope() as s:
        return list(s.scalars(select(Department.name).order_by(Department.name)))


def _department_id(s, name: str) -> int | None:
    """Находит подразделение по имени или создаёт новое."""
    name = name.strip()
    if not name:
        return None
    dep = s.scalar(select(Department).where(Department.name == name))
    if dep is None:
        dep = Department(name=name)
        s.add(dep)
        s.flush()
    return dep.id


def validate(data: dict, new: bool) -> list[str]:
    """Проверяет поля карточки пользователя."""
    errors = []
    if len(data.get("full_name", "").split()) < 2:
        errors.append("ФИО: укажите фамилию и имя")
    if not LOGIN_RE.match(data.get("login", "")):
        errors.append("Логин: латиница, цифры, точка или _, от 3 до 30 символов")
    if data.get("email") and not EMAIL_RE.match(data["email"]):
        errors.append("E-mail указан в неверном формате")
    password = data.get("password", "")
    if new or password:
        errors += [f"Пароль: {p}" for p in password_problems(password)]
    if not data.get("role_code"):
        errors.append("Не выбрана роль")
    return errors


def save_user(data: dict, user_id: int | None, actor_id: int) -> int:
    """Создаёт или изменяет пользователя. Возвращает его идентификатор."""
    errors = validate(data, user_id is None)
    if errors:
        raise ValidationError("\n".join(errors))
    with session_scope() as s:
        same = s.scalar(select(User).where(User.login == data["login"]))
        if same is not None and same.id != user_id:
            raise ValidationError("Пользователь с таким логином уже есть")
        role = s.scalar(select(Role).where(Role.code == data["role_code"]))
        user = User() if user_id is None else s.get(User, user_id)
        user.full_name = data["full_name"].strip()
        user.login = data["login"].strip()
        user.position = data.get("position", "").strip()
        user.email = data.get("email", "").strip()
        user.role_id = role.id
        user.department_id = _department_id(s, data.get("department", ""))
        if data.get("password"):
            user.password_hash = hash_password(data["password"])
        if user_id is None:
            s.add(user)
        s.flush()
        new_id = user.id
    journal.write("user_create" if user_id is None else "user_edit",
                  f"логин {data['login']}", actor_id)
    return new_id


def set_blocked(user_id: int, blocked: bool, actor_id: int):
    """Блокирует или разблокирует учётную запись."""
    if user_id == actor_id and blocked:
        raise ValidationError("Нельзя заблокировать собственную учётную запись")
    with session_scope() as s:
        user = s.get(User, user_id)
        user.is_blocked = blocked
        user.failed_logins = 0
        login = user.login
    journal.write("user_block", f"{login}: {'блок' if blocked else 'разблок'}",
                  actor_id)


def delete_user(user_id: int, actor_id: int):
    """Удаляет пользователя, если у него нет попыток тестирования."""
    if user_id == actor_id:
        raise ValidationError("Нельзя удалить собственную учётную запись")
    with session_scope() as s:
        used = s.scalar(select(func.count(Test.id)).where(Test.user_id == user_id))
        if used:
            raise ValidationError("У пользователя есть результаты тестов. "
                                  "Заблокируйте запись вместо удаления")
        user = s.get(User, user_id)
        login = user.login
        s.delete(user)
    journal.write("user_delete", f"логин {login}", actor_id)


def get_user(user_id: int) -> dict:
    """Данные одного пользователя для формы редактирования."""
    with session_scope() as s:
        u = s.get(User, user_id)
        return {"full_name": u.full_name, "login": u.login,
                "position": u.position, "email": u.email,
                "role_code": u.role.code,
                "department": u.department.name if u.department else "",
                "last_login": u.last_login.strftime("%d.%m.%Y %H:%M")
                if u.last_login else ""}
