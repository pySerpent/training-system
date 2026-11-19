"""Начальное заполнение базы: роли, учётные записи и демонстрационные курсы.

Вызывается при первом запуске, когда в таблице roles ещё нет записей.
Демонстрационные сотрудники и попытки нужны только для показа отчётов.
"""
import os
import random
from datetime import datetime, timedelta

from sqlalchemy import func, select

from . import config
from .database import engine, init_db, session_scope
from .models import (Answer, Assignment, Base, Course, Department, Module, Question,
                     Log, Result, Role, Setting, Test, User)
from .utils import fmt_pct, round_half_up
from .security import hash_password
from .services.settings import backup_database

# Учётные записи по ролям (логин, пароль, ФИО, роль, подразделение, должность)
DEMO_USERS = [
    ("admin", "Admin#2026", "Администратор системы", config.ROLE_ADMIN,
     "Отдел программной инженерии", "Администратор"),
    ("teacher", "Teach#2026", "Смирнова Анна Викторовна", config.ROLE_TEACHER,
     "Отдел программной инженерии", "Специалист по обучению"),
    ("employee", "Empl#2026", "Петров Олег Игоревич", config.ROLE_EMPLOYEE,
     "Отдел программной инженерии", "Инженер-программист"),
    ("kuznetsova", "Empl#2026", "Кузнецова Мария Сергеевна", config.ROLE_EMPLOYEE,
     "Техническая поддержка", "Специалист поддержки"),
    ("sokolov", "Empl#2026", "Соколов Денис Андреевич", config.ROLE_EMPLOYEE,
     "Техническая поддержка", "Системный администратор"),
    ("lebedeva", "Empl#2026", "Лебедева Ольга Павловна", config.ROLE_EMPLOYEE,
     "Административный отдел", "Офис-менеджер"),
]

# Курс -> модули -> (текст материала, вопросы). В вопросе правильные
# варианты помечены звёздочкой в начале строки.
COURSES = {
    ("Основы информационной безопасности",
     "Базовые правила для всех сотрудников: пароли, фишинг, персональные данные"): [
        ("Пароли и учётные записи",
         "Пароль защищает учётную запись только тогда, когда его трудно подобрать "
         "и он известен одному владельцу. Используйте не менее 8 символов: буквы, "
         "цифры и специальные знаки. Не повторяйте один пароль на разных сервисах, "
         "не записывайте его на стикерах и не сообщайте коллегам, в том числе "
         "сотрудникам ИТ-службы. При подозрении на компрометацию пароль меняют сразу "
         "и сообщают администратору. Там, где это возможно, включают второй фактор "
         "подтверждения входа.",
         [("Какой пароль надёжнее?", "single",
           ["qwerty123", "*Tr7#mLq2!vB", "Ivanov1985", "пароль"]),
          ("Кому можно сообщить свой пароль?", "single",
           ["Руководителю отдела", "Сотруднику ИТ-службы по телефону",
            "*Никому", "Коллеге на время отпуска"]),
          ("Что делать, если пароль мог стать известен посторонним?", "multi",
           ["*Сразу сменить пароль", "*Сообщить администратору",
            "Подождать до плановой смены", "Удалить учётную запись самостоятельно"]),
          ("Какие требования входят в корпоративную парольную политику?", "multi",
           ["*Длина не меньше 8 символов", "*Использование цифр и спецсимволов",
            "Одинаковый пароль для всех систем", "Хранение пароля в файле на рабочем столе"]),
          ]),
        ("Фишинг и социальная инженерия",
         "Фишинговое письмо выдаёт себя за сообщение банка, руководителя или "
         "сервиса и подталкивает открыть вложение, перейти по ссылке или срочно "
         "ввести пароль. Признаки: чужой или похожий адрес отправителя, давление "
         "сроками, ошибки в тексте, ссылка, ведущая не на тот домен. Подозрительное "
         "письмо не открывают и пересылают в ИТ-службу. По телефону злоумышленник "
         "может представиться сотрудником поддержки, поэтому личность звонящего "
         "проверяют через официальный номер.",
         [("Какой признак указывает на фишинговое письмо?", "multi",
           ["*Требование срочно ввести пароль", "*Адрес отправителя похож на настоящий, но отличается",
            "Письмо пришло от коллеги по внутренней почте с ожидаемым документом",
            "*Ссылка ведёт на незнакомый домен"]),
          ("Что сделать с подозрительным вложением?", "single",
           ["Открыть, чтобы проверить содержимое", "Переслать коллегам для совета",
            "*Не открывать и сообщить в ИТ-службу", "Сохранить на флешку"]),
          ("Звонящий представился сотрудником поддержки и просит код из СМС. Как поступить?", "single",
           ["Продиктовать код", "*Отказать и перезвонить по официальному номеру поддержки",
            "Отправить код по почте", "Сообщить код, если звонящий знает ваше имя"]),
          ]),
        ("Персональные данные",
         "Персональные данные - любая информация, относящаяся к прямо или косвенно "
         "определённому физическому лицу (152-ФЗ). Обрабатывать их можно только в "
         "рамках служебных задач. Документы с персональными данными не оставляют "
         "на столе, не пересылают на личную почту и не публикуют в мессенджерах. "
         "При утечке сотрудник сразу сообщает ответственному за обработку данных.",
         [("Что относится к персональным данным?", "multi",
           ["*Фамилия и номер телефона сотрудника", "*Паспортные данные",
            "Курс валют на сегодня", "Название города, где находится офис"]),
          ("Можно ли отправить список сотрудников с телефонами на личную почту?", "single",
           ["Да, если работать из дома", "Да, если файл заархивирован",
            "*Нет", "Да, с разрешения коллеги"]),
          ("Какой закон регулирует обработку персональных данных в России?", "single",
           ["*Федеральный закон № 152-ФЗ", "Федеральный закон № 44-ФЗ",
            "Гражданский кодекс, часть 4", "Закон о рекламе"]),
          ]),
    ],
    ("Безопасная работа с ИТ-инфраструктурой",
     "Правила работы с рабочими станциями, съёмными носителями и удалённым доступом"): [
        ("Рабочее место и съёмные носители",
         "Уходя от компьютера, блокируйте экран сочетанием Win+L. Неизвестные "
         "флешки к рабочему компьютеру не подключают: на них может быть вредоносная "
         "программа. Программы устанавливает только ИТ-служба. Антивирус не "
         "отключают, даже если он мешает работе.",
         [("Что сделать, отходя от рабочего места?", "single",
           ["Выключить монитор", "*Заблокировать экран (Win+L)",
            "Оставить как есть", "Закрыть почту"]),
          ("Найдена флешка у входа в офис. Ваши действия?", "single",
           ["Подключить и найти владельца по файлам", "*Передать в ИТ-службу, не подключая",
            "Отформатировать и пользоваться", "Выбросить"]),
          ("Кто устанавливает программы на рабочий компьютер?", "single",
           ["Любой сотрудник", "*ИТ-служба", "Руководитель отдела", "Поставщик программы"]),
          ]),
        ("Удалённая работа",
         "К внутренним системам из дома подключаются только через корпоративный VPN. "
         "Общественные сети Wi-Fi без VPN для работы не используют. Рабочие файлы "
         "хранят на корпоративных ресурсах, а не на личных облачных дисках.",
         [("Как подключаться к внутренним системам из дома?", "single",
           ["Через удалённый рабочий стол без пароля", "*Через корпоративный VPN",
            "Через личный облачный диск", "Через общедоступный Wi-Fi"]),
          ("Где хранить рабочие файлы при удалённой работе?", "multi",
           ["*На корпоративном файловом ресурсе", "*В корпоративной системе документооборота",
            "На личном облачном диске", "В личном мессенджере"]),
          ]),
    ],
}


def _add_questions(module, items):
    """Добавляет вопросы модуля из компактного описания."""
    for text, qtype, options in items:
        q = Question(text=text, qtype=qtype, weight=1.0)
        for option in options:
            q.answers.append(Answer(text=option.lstrip("*"),
                                    is_correct=option.startswith("*")))
        module.questions.append(q)


def _demo_history(s):
    """Журнал подготовки системы: учётные записи, курсы и назначения."""
    users = list(s.scalars(select(User)))
    admin = next(u for u in users if u.role.code == config.ROLE_ADMIN)
    teacher = next(u for u in users if u.role.code == config.ROLE_TEACHER)
    start = datetime.now() - timedelta(days=12, hours=3)
    s.add(Log(user_id=admin.id, action="login", details="успешный вход", created_at=start))
    for i, user in enumerate(u for u in users if u is not admin):
        s.add(Log(user_id=admin.id, action="user_create",
                  details=f"{user.login} ({user.role.title})",
                  created_at=start + timedelta(minutes=3 + 2 * i)))
    later = start + timedelta(days=1)
    s.add(Log(user_id=teacher.id, action="login", details="успешный вход", created_at=later))
    for i, course in enumerate(s.scalars(select(Course))):
        s.add(Log(user_id=teacher.id, action="course_edit",
                  details=f"курс «{course.title}», модулей: {len(course.modules)}",
                  created_at=later + timedelta(minutes=10 + 25 * i)))


def _demo_attempts(s):
    """Несколько завершённых попыток, чтобы дашборд и отчёты были не пустыми."""
    rnd = random.Random(7)
    employees = [u for u in s.scalars(select(User)) if u.role.code == config.ROLE_EMPLOYEE]
    for course in s.scalars(select(Course)):
        questions = [q for m in course.modules for q in m.questions]
        for user in employees:
            started = datetime.now() - timedelta(days=rnd.randint(1, 9),
                                                 minutes=rnd.randint(0, 600))
            test = Test(user_id=user.id, course_id=course.id, started_at=started,
                        finished_at=started + timedelta(minutes=rnd.randint(4, 14)),
                        max_score=len(questions))
            score = 0
            for q in questions:
                right = [a for a in q.answers if a.is_correct]
                ok = rnd.random() < 0.78
                chosen = right if ok else [rnd.choice([a for a in q.answers
                                                       if not a.is_correct])]
                score += ok
                for a in chosen:
                    test.results.append(Result(question_id=q.id, answer_id=a.id,
                                               is_correct=ok))
            test.score = score
            test.percent = round_half_up(score / len(questions) * 100, 1)
            test.passed = test.percent >= 70
            s.add(test)
            # записи журнала, которые оставила бы такая попытка
            pct = fmt_pct(test.percent)
            for when, action, details in (
                    (started - timedelta(minutes=2), "login", "успешный вход"),
                    (started, "test_start", f"курс «{course.title}»"),
                    (test.finished_at, "test_finish", f"«{course.title}»: {pct}")):
                s.add(Log(user_id=user.id, action=action, details=details,
                          created_at=when))


def seed_if_empty():
    """Заполняет пустую базу. Повторный вызов ничего не меняет."""
    with session_scope() as s:
        if s.scalar(select(func.count(Role.id))):
            return False
        roles = {}
        for code, title in config.ROLE_TITLES.items():
            roles[code] = Role(code=code, title=title)
            s.add(roles[code])
        deps = {}
        for login, password, name, role, dep, position in DEMO_USERS:
            if dep not in deps:
                deps[dep] = Department(name=dep)
                s.add(deps[dep])
            s.add(User(login=login, password_hash=hash_password(password),
                       full_name=name, role=roles[role], department=deps[dep],
                       position=position))
        for key, value in config.DEFAULT_SETTINGS.items():
            s.add(Setting(key=key, value=value))
        s.flush()
        for (title, description), modules in COURSES.items():
            course = Course(title=title, description=description)
            for pos, (mtitle, content, items) in enumerate(modules, 1):
                module = Module(title=mtitle, content=content, position=pos)
                _add_questions(module, items)
                course.modules.append(module)
            s.add(course)
        s.flush()
        due = datetime.now() + timedelta(days=14)
        for user in s.scalars(select(User)):
            if user.role.code == config.ROLE_EMPLOYEE:
                for course in s.scalars(select(Course)):
                    s.add(Assignment(user_id=user.id, course_id=course.id, due_date=due))
        s.flush()
        _demo_history(s)
        _demo_attempts(s)
    return True


def reset_demo():
    """Удаляет все данные и заново заполняет базу демонстрационным набором.

    Перед удалением делается резервная копия файла базы.
    """
    if os.path.exists(config.DB_PATH):
        backup_database()
    Base.metadata.drop_all(engine)
    init_db()
    return seed_if_empty()
