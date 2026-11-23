"""Импорт вопросов из книги Excel и выгрузка шаблона для заполнения.

Формат листа: Вопрос | Тип | Вес | Вариант 1 ... Вариант 6.
Тип: «один» или «несколько». Правильный вариант помечается звёздочкой
в начале ячейки, например «*Сообщить в службу ИБ».
"""
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from .. import config
from . import courses, journal
from .users import ValidationError

HEADER = ["Вопрос", "Тип", "Вес"] + [f"Вариант {i}" for i in range(1, 7)]
TYPES = {"один": config.QTYPE_SINGLE, "несколько": config.QTYPE_MULTI}


def save_template(path: str) -> str:
    """Создаёт пустой шаблон с одной строкой-примером."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Вопросы"
    ws.append(HEADER)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.append(["Как поступить с письмом, в котором просят срочно сообщить пароль?",
               "один", 1, "*Не отвечать и сообщить в службу ИБ",
               "Ответить, если письмо от руководителя", "Переслать коллегам"])
    ws.column_dimensions["A"].width = 60
    for col in "DEFGHI":
        ws.column_dimensions[col].width = 32
    wb.save(path)
    return path


def parse_row(row: tuple) -> tuple:
    """Разбирает строку листа в (текст, тип, вес, [(вариант, верный)])."""
    text = str(row[0] or "").strip()
    qtype = TYPES.get(str(row[1] or "один").strip().lower())
    if qtype is None:
        raise ValidationError("тип должен быть «один» или «несколько»")
    try:
        weight = float(str(row[2] or 1).replace(",", "."))
    except ValueError:
        raise ValidationError("вес должен быть числом") from None
    answers = []
    for value in row[3:9]:
        value = str(value or "").strip()
        if value:
            answers.append((value.lstrip("*").strip(), value.startswith("*")))
    return text, qtype, weight, answers


def import_questions(module_id: int, path: str, actor_id: int) -> tuple[int, list[str]]:
    """Добавляет вопросы из файла в модуль.

    Строки с ошибками пропускаются, их номера и причины возвращаются,
    чтобы преподаватель мог исправить файл и загрузить его снова.
    """
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
        # в режиме read_only файл остаётся открытым, поэтому строки читаются сразу
        rows = list(wb.active.iter_rows(min_row=2, values_only=True))
        wb.close()
    except Exception as exc:
        raise ValidationError(f"Файл не читается как книга Excel: {exc}") from None
    added, problems = 0, []
    for number, row in enumerate(rows, start=2):
        row = tuple(row) + (None,) * (9 - len(row))
        if not any(row):
            continue
        try:
            text, qtype, weight, answers = parse_row(row)
            courses.save_question(module_id, text, qtype, weight, answers, None, actor_id)
            added += 1
        except ValidationError as exc:
            problems.append(f"строка {number}: {str(exc).replace(chr(10), '; ')}")
    journal.write("question_edit", f"импорт из Excel: добавлено {added}, "
                                   f"пропущено {len(problems)}", actor_id)
    return added, problems
