"""Логика тестирования: выбор вопросов, подсчёт баллов, статистика."""
import random
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select

from .. import config
from ..database import session_scope
from ..utils import fmt_pct, round_half_up
from ..models import Assignment, Course, Module, Question, Result, Test, User
from . import journal, settings
from .users import ValidationError


@dataclass
class TestQuestion:
    """Вопрос в том виде, в каком он показывается сотруднику."""
    id: int
    text: str
    qtype: str
    weight: float
    options: list = field(default_factory=list)  # [(answer_id, text)]


@dataclass
class TestSession:
    """Текущая попытка: вопросы, ответы сотрудника и ограничение по времени."""
    test_id: int
    course_title: str
    questions: list
    time_limit_sec: int
    answers: dict = field(default_factory=dict)  # question_id -> set(answer_id)


def available_courses(user_id: int) -> list[dict]:
    """Активные курсы для сотрудника с отметкой о назначении и попытках."""
    limit = settings.get_int("max_attempts", 3)
    with session_scope() as s:
        assigned = {a.course_id: a.due_date for a in
                    s.scalars(select(Assignment).where(Assignment.user_id == user_id))}
        rows = []
        for c in s.scalars(select(Course).where(Course.is_active.is_(True))
                           .order_by(Course.title)):
            qcount = s.scalar(select(func.count(Question.id)).join(Module)
                              .where(Module.course_id == c.id))
            if not qcount:
                continue  # курс без вопросов пройти нельзя
            tries = s.scalar(select(func.count(Test.id)).where(
                Test.user_id == user_id, Test.course_id == c.id,
                Test.finished_at.is_not(None)))
            best = s.scalar(select(func.max(Test.percent)).where(
                Test.user_id == user_id, Test.course_id == c.id)) or 0
            due = assigned.get(c.id)
            rows.append({"id": c.id, "title": c.title,
                         "description": c.description, "questions": qcount,
                         "assigned": c.id in assigned,
                         "due": due.strftime("%d.%m.%Y") if due else "",
                         "tries": tries, "tries_left": max(limit - tries, 0),
                         "best": round_half_up(best, 1)})
        return rows


def start_test(user_id: int, course_id: int) -> TestSession:
    """Создаёт попытку и случайно выбирает вопросы из всех модулей курса."""
    count = settings.get_int("questions_per_test", 10)
    minutes = settings.get_int("test_time_min", 15)
    limit = settings.get_int("max_attempts", 3)
    with session_scope() as s:
        tries = s.scalar(select(func.count(Test.id)).where(
            Test.user_id == user_id, Test.course_id == course_id,
            Test.finished_at.is_not(None)))
        if tries >= limit:
            raise ValidationError("Число попыток по курсу исчерпано. "
                                  "Обратитесь к преподавателю")
        pool = list(s.scalars(select(Question).join(Module)
                              .where(Module.course_id == course_id)))
        if not pool:
            raise ValidationError("В курсе пока нет вопросов")
        # рандомизация: порядок вопросов и вариантов ответа у каждого свой
        chosen = random.sample(pool, min(count, len(pool)))
        questions = []
        for q in chosen:
            options = [(a.id, a.text) for a in q.answers]
            random.shuffle(options)
            questions.append(TestQuestion(q.id, q.text, q.qtype, q.weight, options))
        test = Test(user_id=user_id, course_id=course_id,
                    max_score=sum(q.weight for q in chosen))
        s.add(test)
        s.flush()
        session = TestSession(test.id, s.get(Course, course_id).title,
                              questions, minutes * 60)
    journal.write("test_start", f"курс «{session.course_title}»", user_id)
    return session


def finish_test(session: TestSession, user_id: int, timeout: bool = False) -> dict:
    """Проверяет ответы, сохраняет детализацию и итоговую оценку."""
    threshold = settings.get_int("pass_threshold", 70)
    with session_scope() as s:
        test = s.get(Test, session.test_id)
        score = 0.0
        for tq in session.questions:
            question = s.get(Question, tq.id)
            right = {a.id for a in question.answers if a.is_correct}
            chosen = session.answers.get(tq.id, set())
            ok = chosen == right  # частично верный ответ баллов не даёт
            if ok:
                score += question.weight
            if not chosen:
                s.add(Result(test_id=test.id, question_id=tq.id,
                             answer_id=None, is_correct=False))
            for answer_id in chosen:
                s.add(Result(test_id=test.id, question_id=tq.id,
                             answer_id=answer_id, is_correct=ok))
        test.finished_at = datetime.now()
        test.score = score
        test.percent = round_half_up(score / test.max_score * 100, 1) if test.max_score else 0
        test.passed = test.percent >= threshold
        if timeout:
            test.comment = "Время теста истекло"
        summary = {"test_id": test.id, "course": session.course_title,
                   "score": score, "max_score": test.max_score,
                   "percent": test.percent, "passed": test.passed,
                   "threshold": threshold,
                   "answered": sum(1 for q in session.questions
                                   if session.answers.get(q.id)),
                   "total": len(session.questions),
                   "duration": str(test.finished_at - test.started_at).split(".")[0]}
    journal.write("test_finish", f"«{session.course_title}»: {fmt_pct(summary['percent'])}"
                  + (" (по таймеру)" if timeout else ""), user_id)
    return summary


def list_results(user_id: int | None = None, course_id: int | None = None,
                 text: str = "") -> list[dict]:
    """Завершённые попытки для таблицы результатов и отчётов."""
    with session_scope() as s:
        # условия соединения указаны явно: у курса есть ещё связь с автором
        q = (select(Test).join(User, Test.user_id == User.id)
             .join(Course, Test.course_id == Course.id)
             .where(Test.finished_at.is_not(None))
             .order_by(Test.finished_at.desc()))
        if user_id:
            q = q.where(Test.user_id == user_id)
        if course_id:
            q = q.where(Test.course_id == course_id)
        if text:
            q = q.where(User.full_name.like(f"%{text.strip()}%"))
        return [{"id": t.id, "user": t.user.full_name,
                 "department": t.user.department.name if t.user.department else "",
                 "course": t.course.title,
                 "date": t.finished_at.strftime("%d.%m.%Y %H:%M"),
                 "score": f"{t.score:g} из {t.max_score:g}",
                 "percent": t.percent,
                 "status": "Сдан" if t.passed else "Не сдан",
                 "comment": t.comment} for t in s.scalars(q)]


def test_details(test_id: int) -> list[dict]:
    """Ответы по вопросам одной попытки."""
    with session_scope() as s:
        test = s.get(Test, test_id)
        grouped = {}
        for r in test.results:
            item = grouped.setdefault(r.question_id, {
                "question": r.question.text, "chosen": [], "ok": r.is_correct,
                "right": [a.text for a in r.question.answers if a.is_correct]})
            if r.answer is not None:
                item["chosen"].append(r.answer.text)
        return list(grouped.values())


def set_comment(test_id: int, comment: str, actor_id: int):
    """Комментарий преподавателя к оценке."""
    with session_scope() as s:
        s.get(Test, test_id).comment = comment.strip()[:500]
    journal.write("comment", f"комментарий к попытке {test_id}", actor_id)


def dashboard_stats(user_id: int | None = None) -> dict:
    """Показатели для виджетов главного окна."""
    with session_scope() as s:
        base = select(Test).where(Test.finished_at.is_not(None))
        if user_id:
            base = base.where(Test.user_id == user_id)
        tests = list(s.scalars(base))
        users = s.scalar(select(func.count(User.id)))
        courses = s.scalar(select(func.count(Course.id))
                           .where(Course.is_active.is_(True)))
        passed = sum(1 for t in tests if t.passed)
        overdue = 0
        q = select(Assignment)
        if user_id:
            q = q.where(Assignment.user_id == user_id)
        for a in s.scalars(q):
            done = any(t.passed for t in tests if t.user_id == a.user_id
                       and t.course_id == a.course_id)
            if not done and a.due_date and a.due_date < datetime.now():
                overdue += 1
        by_course = {}
        for t in tests:
            by_course.setdefault(t.course.title, []).append(t.percent)
        return {"users": users, "courses": courses, "tests": len(tests),
                "pass_rate": round_half_up(passed / len(tests) * 100, 1) if tests else 0,
                "avg": round_half_up(sum(t.percent for t in tests) / len(tests), 1)
                if tests else 0,
                "overdue": overdue,
                "by_course": {k: round_half_up(sum(v) / len(v), 1)
                              for k, v in sorted(by_course.items())}}


def role_of(user_id: int) -> str:
    """Код роли пользователя (нужен отчётам)."""
    with session_scope() as s:
        user = s.get(User, user_id)
        return user.role.code if user else config.ROLE_EMPLOYEE
