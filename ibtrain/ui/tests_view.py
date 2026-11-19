"""Выбор курса (форма 8), прохождение теста (форма 9), итог попытки (форма 10)."""
import customtkinter as ctk

from .. import config
from ..services import courses, journal, testing
from .courses_view import MaterialWindow
from ..utils import fmt_pct
from .widgets import (FONT, FONT_BOLD, ConfirmDialog, DataTable, PageHeader,
                      show_error)


class TestsView(ctk.CTkFrame):
    """Курсы, доступные сотруднику, с материалами и запуском теста."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        PageHeader(self, "Обучение и тесты",
                   "Изучите материалы модулей, затем пройдите тест").pack(anchor="w")
        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.pack(fill="both", expand=True, pady=10)
        self.reload()

    def reload(self):
        for child in self.list.winfo_children():
            child.destroy()
        rows = testing.available_courses(self.app.user.id)
        if not rows:
            ctk.CTkLabel(self.list, text="Доступных курсов пока нет", font=FONT).pack()
        for row in rows:
            self._card(row)

    def _card(self, row: dict):
        card = ctk.CTkFrame(self.list, corner_radius=10)
        card.pack(fill="x", pady=6)
        head = row["title"] + ("   • назначен" if row["assigned"] else "")
        ctk.CTkLabel(card, text=head, font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(10, 0))
        ctk.CTkLabel(card, text=row["description"], font=FONT, wraplength=820,
                     justify="left").pack(anchor="w", padx=16)
        info = (f"Вопросов в банке: {row['questions']}   Попыток: {row['tries']}"
                f" (осталось {row['tries_left']})   Лучший результат: {fmt_pct(row['best'])}")
        if row["due"]:
            info += f"   Срок: {row['due']}"
        ctk.CTkLabel(card, text=info, font=("Segoe UI", 12),
                     text_color=("gray35", "gray70")).pack(anchor="w", padx=16, pady=4)
        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.pack(anchor="w", padx=16, pady=(0, 12))
        for module in courses.list_modules(row["id"]):
            ctk.CTkButton(buttons, text=module["title"], width=10, height=28,
                          fg_color=("gray70", "gray35"), text_color=("gray10", "gray90"),
                          command=lambda m=module["id"]: MaterialWindow(self, m)
                          ).pack(side="left", padx=(0, 6))
        state = "normal" if row["tries_left"] > 0 else "disabled"
        ctk.CTkButton(buttons, text="Начать тест", font=FONT_BOLD, state=state,
                      command=lambda c=row: self.start(c)).pack(side="left", padx=(10, 0))

    def start(self, course: dict):
        try:
            session = testing.start_test(self.app.user.id, course["id"])
        except testing.ValidationError as exc:
            show_error(str(exc), self)
            return
        except Exception as exc:
            journal.error(f"старт теста: {exc}", self.app.user.id)
            show_error(f"Не удалось начать тест: {exc}", self)
            return
        TestWindow(self, self.app, session, on_close=self.reload)


class TestWindow(ctk.CTkToplevel):
    """Окно теста: один вопрос на экране, таймер, переход по вопросам."""

    def __init__(self, master, app, session: testing.TestSession, on_close=None):
        super().__init__(master)
        self.app, self.session, self.on_close = app, session, on_close
        self.index, self.left, self.finished = 0, session.time_limit_sec, False
        self.title(f"Тест: {session.course_title}")
        self.geometry("820x560")
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(14, 0))
        self.counter = ctk.CTkLabel(top, text="", font=FONT_BOLD)
        self.counter.pack(side="left")
        self.timer = ctk.CTkLabel(top, text="", font=("Segoe UI", 16, "bold"))
        self.timer.pack(side="right")
        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(fill="x", padx=20, pady=8)
        self.question = ctk.CTkLabel(self, text="", font=("Segoe UI", 17), wraplength=760,
                                     justify="left")
        self.question.pack(anchor="w", padx=20, pady=(10, 4))
        self.hint = ctk.CTkLabel(self, text="", font=("Segoe UI", 12), text_color="gray50")
        self.hint.pack(anchor="w", padx=20)
        self.options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.options_frame.pack(fill="both", expand=True, padx=20, pady=8)
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=20, pady=14)
        ctk.CTkButton(nav, text="< Назад", width=110, command=lambda: self.go(-1)).pack(side="left")
        ctk.CTkButton(nav, text="Далее >", width=110, command=lambda: self.go(1)).pack(side="left", padx=8)
        ctk.CTkButton(nav, text="Завершить тест", fg_color="#2e8b57",
                      command=self.ask_finish).pack(side="right")
        self.protocol("WM_DELETE_WINDOW", self.ask_finish)
        # клавиатура: стрелки листают вопросы, цифры 1-6 выбирают вариант
        self.bind("<Left>", lambda _e: self.go(-1))
        self.bind("<Right>", lambda _e: self.go(1))
        for digit in range(1, 7):
            self.bind(str(digit), lambda _e, n=digit: self.pick(n - 1))
        self.transient(master.winfo_toplevel())
        self.after(50, self.grab_set)
        self.after(60, self.focus_force)
        self.show()
        self.tick()

    def tick(self):
        """Обратный отсчёт; по истечении времени тест завершается сам."""
        if self.finished:
            return
        minutes, seconds = divmod(self.left, 60)
        self.timer.configure(text=f"Осталось {minutes:02d}:{seconds:02d}",
                             text_color="#c0392b" if self.left < 60 else ("gray10", "gray90"))
        if self.left <= 0:
            self.finish(timeout=True)
            return
        self.left -= 1
        self.after(1000, self.tick)

    def show(self):
        q = self.session.questions[self.index]
        total = len(self.session.questions)
        self.counter.configure(text=f"Вопрос {self.index + 1} из {total}")
        self.progress.set((self.index + 1) / total)
        self.question.configure(text=q.text)
        self.hint.configure(text=("Выберите один вариант" if q.qtype == config.QTYPE_SINGLE
                                  else "Выберите все правильные варианты")
                            + " (клавиши 1-6, стрелки - переход)")
        for child in self.options_frame.winfo_children():
            child.destroy()
        chosen = self.session.answers.get(q.id, set())
        if q.qtype == config.QTYPE_SINGLE:
            var = ctk.IntVar(value=next(iter(chosen), 0))
            for n, (answer_id, text) in enumerate(q.options, 1):
                ctk.CTkRadioButton(self.options_frame, text=f"{n}. {text}", value=answer_id,
                                   variable=var, font=FONT,
                                   command=lambda: self.session.answers.__setitem__(
                                       q.id, {var.get()})).pack(anchor="w", pady=6)
        else:
            for n, (answer_id, text) in enumerate(q.options, 1):
                box = ctk.CTkCheckBox(self.options_frame, text=f"{n}. {text}", font=FONT,
                                      command=lambda a=answer_id: self.toggle(q.id, a))
                if answer_id in chosen:
                    box.select()
                box.pack(anchor="w", pady=6)

    def pick(self, position: int):
        """Выбор варианта по номеру на клавиатуре."""
        q = self.session.questions[self.index]
        if position >= len(q.options):
            return
        answer_id = q.options[position][0]
        if q.qtype == config.QTYPE_SINGLE:
            self.session.answers[q.id] = {answer_id}
        else:
            self.toggle(q.id, answer_id)
        self.show()

    def toggle(self, question_id: int, answer_id: int):
        chosen = self.session.answers.setdefault(question_id, set())
        chosen.symmetric_difference_update({answer_id})

    def go(self, step: int):
        self.index = max(0, min(len(self.session.questions) - 1, self.index + step))
        self.show()

    def ask_finish(self):
        empty = sum(1 for q in self.session.questions if not self.session.answers.get(q.id))
        text = "Завершить тест и отправить ответы?"
        if empty:
            text += f"\nБез ответа осталось вопросов: {empty}."
        if ConfirmDialog.ask(self, "Завершение теста", text):
            self.finish()

    def finish(self, timeout: bool = False):
        self.finished = True
        try:
            summary = testing.finish_test(self.session, self.app.user.id, timeout)
        except Exception as exc:
            journal.error(f"сохранение теста: {exc}", self.app.user.id)
            show_error(f"Не удалось сохранить результат: {exc}", self)
            return
        master = self.master
        self.destroy()
        ResultWindow(master, summary)
        if self.on_close:
            self.on_close()


class ResultWindow(ctk.CTkToplevel):
    """Итог попытки и разбор ответов."""

    def __init__(self, master, summary: dict):
        super().__init__(master)
        self.title("Результат теста")
        self.geometry("760x520")
        ok = summary["passed"]
        ctk.CTkLabel(self, text="Тест сдан" if ok else "Тест не сдан",
                     font=("Segoe UI", 24, "bold"),
                     text_color="#2e8b57" if ok else "#c0392b").pack(pady=(18, 4))
        ctk.CTkLabel(self, text=f"«{summary['course']}»", font=FONT).pack()
        ctk.CTkLabel(self, text=(f"Баллы: {summary['score']:g} из {summary['max_score']:g}   "
                                 f"Результат: {fmt_pct(summary['percent'])} (порог {summary['threshold']} %)   "
                                 f"Время: {summary['duration']}"),
                     font=FONT).pack(pady=6)
        table = DataTable(self, [("question", "Вопрос", 380), ("answer", "Ваш ответ", 220),
                                 ("mark", "Оценка", 80)], height=10)
        table.pack(fill="both", expand=True, padx=16, pady=8)
        details = testing.test_details(summary["test_id"])
        table.load([{"question": d["question"], "answer": "; ".join(d["chosen"]) or "нет ответа",
                     "mark": "верно" if d["ok"] else "неверно"} for d in details])
        ctk.CTkButton(self, text="Закрыть", command=self.destroy).pack(pady=(0, 14))
