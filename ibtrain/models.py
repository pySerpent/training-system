"""ORM-модели SQLAlchemy. Каждая модель соответствует одной таблице базы.

Таблиц двенадцать: роли, подразделения, пользователи, курсы, модули,
вопросы, варианты ответов, назначения курсов, попытки тестирования,
детализация ответов, журнал действий и настройки.
"""
from datetime import datetime

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer, String,
                        Text, UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс всех моделей."""


class Role(Base):
    """Роль пользователя: администратор, преподаватель, сотрудник."""
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    title: Mapped[str] = mapped_column(String(50))

    users = relationship("User", back_populates="role")


class Department(Base):
    """Подразделение, в котором работает сотрудник."""
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)

    users = relationship("User", back_populates="department")


class User(Base):
    """Учётная запись. Пароль хранится только в виде хеша с солью."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150))
    login: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    position: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    role = relationship("Role", back_populates="users")
    department = relationship("Department", back_populates="users")
    tests = relationship("Test", back_populates="user")


class Course(Base):
    """Учебный курс, например «Основы информационной безопасности»."""
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(150), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    modules = relationship("Module", back_populates="course",
                           cascade="all, delete-orphan",
                           order_by="Module.position")


class Module(Base):
    """Модуль курса с учебным материалом и набором вопросов."""
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    title: Mapped[str] = mapped_column(String(150))
    content: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(Integer, default=1)

    course = relationship("Course", back_populates="modules")
    questions = relationship("Question", back_populates="module",
                             cascade="all, delete-orphan")


class Question(Base):
    """Вопрос теста с одиночным или множественным выбором."""
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"))
    text: Mapped[str] = mapped_column(Text)
    qtype: Mapped[str] = mapped_column(String(10), default="single")
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    module = relationship("Module", back_populates="questions")
    answers = relationship("Answer", back_populates="question",
                           cascade="all, delete-orphan")


class Answer(Base):
    """Вариант ответа на вопрос с признаком правильности."""
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    question = relationship("Question", back_populates="answers")


class Assignment(Base):
    """Назначение курса сотруднику со сроком прохождения."""
    __tablename__ = "assignments"
    __table_args__ = (UniqueConstraint("user_id", "course_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    user = relationship("User")
    course = relationship("Course")


class Test(Base):
    """Попытка прохождения теста по курсу."""
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    max_score: Mapped[float] = mapped_column(Float, default=0.0)
    percent: Mapped[float] = mapped_column(Float, default=0.0)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    comment: Mapped[str] = mapped_column(Text, default="")

    user = relationship("User", back_populates="tests")
    course = relationship("Course")
    results = relationship("Result", back_populates="test",
                           cascade="all, delete-orphan")


class Result(Base):
    """Детализация попытки: какой вариант выбран на какой вопрос."""
    __tablename__ = "results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    answer_id: Mapped[int | None] = mapped_column(
        ForeignKey("answers.id"), nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    test = relationship("Test", back_populates="results")
    question = relationship("Question")
    answer = relationship("Answer")


class Log(Base):
    """Запись журнала действий пользователей."""
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    details: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[str] = mapped_column(String(10), default="INFO")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    user = relationship("User")


class Setting(Base):
    """Настройка системы в виде пары ключ - значение."""
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True)
    value: Mapped[str] = mapped_column(Text, default="")
