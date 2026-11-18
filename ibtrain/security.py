"""Хеширование паролей и проверка их стойкости.

Используется алгоритм PBKDF2-HMAC-SHA256 из стандартного модуля hashlib.
В базе хранится строка вида «pbkdf2$итерации$соль$хеш», открытый пароль
нигде не сохраняется.
"""
import hashlib
import hmac
import re
import secrets

ITERATIONS = 120_000


def hash_password(password: str, salt: str | None = None) -> str:
    """Возвращает строку с солью и хешем пароля."""
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 salt.encode("ascii"), ITERATIONS)
    return f"pbkdf2${ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Сравнивает введённый пароль с сохранённым хешем."""
    try:
        _algo, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                salt.encode("ascii"), int(iterations))
    # compare_digest защищает от атаки по времени сравнения
    return hmac.compare_digest(check.hex(), digest)


def password_problems(password: str) -> list[str]:
    """Проверяет пароль по корпоративным правилам и возвращает список замечаний."""
    problems = []
    if len(password) < 8:
        problems.append("не короче 8 символов")
    if not re.search(r"[A-Za-zА-Яа-я]", password):
        problems.append("хотя бы одна буква")
    if not re.search(r"\d", password):
        problems.append("хотя бы одна цифра")
    if not re.search(r"[^\w\s]", password):
        problems.append("хотя бы один специальный символ")
    return problems
