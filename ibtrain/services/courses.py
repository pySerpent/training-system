"""Курсы, модули, вопросы и варианты ответов."""
from sqlalchemy import func, select

from .. import config
from ..database import session_scope
from ..models import Answer, Assignment, Course, Module, Question, Test, User
from . import journal
from .users import ValidationError


# ---------- курсы ----------

def list_courses(only_active: bool = False) -> list[dict]:
    """Курсы с числом модулей и вопросов."""
    with session_scope() as s:
        q = select(Course).order_by(Course.title)
        if only_active:
            q = q.where(Course.is_active.is_(True))
        rows = []
        for c in s.scalars(q):
            questions = sum(len(m.questions) for m in c.modules)
            rows.append({"id": c.id, "title": c.title,
                         "description": c.description,
                         "active": c.is_active, "modules": len(c.modules),
                         "questions": questions})
        return rows


def save_course(title: str, description: str, active: bool,
                course_id: int | None, actor_id: int) -> int:
    """Создаёт или изменяет курс."""
    title = title.strip()
    if len(title) < 3:
        raise ValidationError("Название курса должно быть не короче 3 символов")
    with session_scope() as s:
        same = s.scalar(select(Course).where(Course.title == title))
        if same is not None and same.id != course_id:
            raise ValidationError("Курс с таким названием уже есть")
        course = Course(author_id=actor_id) if course_id is None \
            else s.get(Course, course_id)
        course.title, course.description = title, description.strip()
        course.is_active = active
        if course_id is None:
            s.add(course)
        s.flush()
        cid = course.id
    journal.write("course_edit", f"курс «{title}»", actor_id)
    return cid


def delete_course(course_id: int, actor_id: int):
    """Удаляет курс, по которому ещё не было попыток."""
    with session_scope() as s:
        if s.scalar(select(func.count(Test.id)).where(Test.course_id == course_id)):
            raise ValidationError("По курсу уже есть попытки. "
                                  "Снимите отметку «Активен» вместо удаления")
        for a in s.scalars(select(Assignment).where(Assignment.course_id == course_id)):
            s.delete(a)
        course = s.get(Course, course_id)
        title = course.title
        s.delete(course)
    journal.write("course_edit", f"удалён курс «{title}»", actor_id)


# ---------- модули ----------

def list_modules(course_id: int) -> list[dict]:
    """Модули курса по порядку."""
    with session_scope() as s:
        q = select(Module).where(Module.course_id == course_id) \
            .order_by(Module.position)
        return [{"id": m.id, "title": m.title, "content": m.content,
                 "position": m.position, "questions": len(m.questions)}
                for m in s.scalars(q)]


def save_module(course_id: int, title: str, content: str,
                module_id: int | None, actor_id: int) -> int:
    """Создаёт или изменяет модуль курса."""
    if len(title.strip()) < 2:
        raise ValidationError("Укажите название модуля")
    with session_scope() as s:
        if module_id is None:
            last = s.scalar(select(func.max(Module.position))
                            .where(Module.course_id == course_id)) or 0
            module = Module(course_id=course_id, position=last + 1)
            s.add(module)
        else:
            module = s.get(Module, module_id)
        module.title, module.content = title.strip(), content.strip()
        s.flush()
        mid = module.id
    journal.write("course_edit", f"модуль «{title.strip()}»", actor_id)
    return mid


def delete_module(module_id: int, actor_id: int):
    """Удаляет модуль вместе с его вопросами."""
    with session_scope() as s:
        module = s.get(Module, module_id)
        title = module.title
        s.delete(module)
    journal.write("course_edit", f"удалён модуль «{title}»", actor_id)


def module_content(module_id: int) -> dict:
    """Учебный материал модуля для окна чтения."""
    with session_scope() as s:
        m = s.get(Module, module_id)
        return {"title": m.title, "course": m.course.title, "content": m.content}


# ---------- вопросы ----------

def list_questions(module_id: int) -> list[dict]:
    """Вопросы модуля с вариантами ответов."""
    with session_scope() as s:
        q = select(Question).where(Question.module_id == module_id) \
            .order_by(Question.id)
        return [{"id": x.id, "text": x.text, "qtype": x.qtype,
                 "type_title": config.QTYPE_TITLES[x.qtype],
                 "weight": x.weight,
                 "answers": [(a.text, a.is_correct) for a in x.answers]}
                for x in s.scalars(q)]


def validate_question(text: str, qtype: str, answers: list) -> list[str]:
    """Проверяет вопрос: текст, не меньше двух вариантов, правильные ответы."""
    errors = []
    if len(text.strip()) < 5:
        errors.append("Текст вопроса слишком короткий")
    filled = [(t.strip(), ok) for t, ok in answers if t.strip()]
    if len(filled) < 2:
        errors.append("Нужно не меньше двух вариантов ответа")
    correct = sum(1 for _t, ok in filled if ok)
    if correct == 0:
        errors.append("Отметьте правильный ответ")
    if qtype == config.QTYPE_SINGLE and correct > 1:
        errors.append("В вопросе с одиночным выбором правильный ответ один")
    if len({t.lower() for t, _ok in filled}) != len(filled):
        errors.append("Варианты ответа повторяются")
    return errors


def save_question(module_id: int, text: str, qtype: str, weight: float,
                  answers: list, question_id: int | None, actor_id: int):
    """Сохраняет вопрос и полностью заменяет его варианты ответов."""
    errors = validate_question(text, qtype, answers)
    if not 0.5 <= weight <= 5:
        errors.append("Вес вопроса от 0,5 до 5")
    if errors:
        raise ValidationError("\n".join(errors))
    with session_scope() as s:
        if question_id is None:
            question = Question(module_id=module_id)
            s.add(question)
        else:
            question = s.get(Question, question_id)
            question.answers.clear()
        question.text, question.qtype = text.strip(), qtype
        question.weight = weight
        for answer_text, ok in answers:
            if answer_text.strip():
                question.answers.append(Answer(text=answer_text.strip(),
                                               is_correct=bool(ok)))
    journal.write("question_edit", text.strip()[:80], actor_id)


def delete_question(question_id: int, actor_id: int):
    """Удаляет вопрос."""
    with session_scope() as s:
        question = s.get(Question, question_id)
        text = question.text
        s.delete(question)
    journal.write("question_edit", f"удалён: {text[:80]}", actor_id)


# ---------- назначения ----------

def assign_course(course_id: int, department: str, due, actor_id: int) -> int:
    """Назначает курс всем сотрудникам подразделения (или всем, если пусто)."""
    count = 0
    with session_scope() as s:
        q = select(User).where(User.is_blocked.is_(False))
        users = [u for u in s.scalars(q)
                 if u.role.code == config.ROLE_EMPLOYEE and
                 (not department or (u.department and u.department.name == department))]
        for user in users:
            exists = s.scalar(select(Assignment).where(
                Assignment.user_id == user.id, Assignment.course_id == course_id))
            if exists is None:
                s.add(Assignment(user_id=user.id, course_id=course_id, due_date=due))
                count += 1
    journal.write("course_edit", f"назначение курса {course_id}: {count} чел.",
                  actor_id)
    return count
