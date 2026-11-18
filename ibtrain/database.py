"""Подключение к базе данных SQLite через SQLAlchemy."""
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from . import config
from .models import Base

config.ensure_dirs()

# Движок базы. Вся работа идёт в главном потоке Tk, включая таймер теста
# (after()), поэтому дополнительные настройки потоков не нужны.
engine = create_engine(f"sqlite:///{config.DB_PATH}")


@event.listens_for(engine, "connect")
def _enable_foreign_keys(dbapi_conn, _record):
    """Включает проверку внешних ключей, в SQLite она по умолчанию выключена."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db():
    """Создаёт таблицы, если их нет."""
    Base.metadata.create_all(engine)


@contextmanager
def session_scope():
    """Открывает сессию, фиксирует изменения или откатывает их при ошибке."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
