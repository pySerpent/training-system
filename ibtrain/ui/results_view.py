"""Результаты тестирования (форма 11) и диалог комментария преподавателя."""
import customtkinter as ctk

from .. import config
from ..services import auth, courses, journal, testing
from ..utils import fmt_pct, round_half_up
from .widgets import (FONT, FONT_BOLD, DataTable, PageHeader, TextInputDialog,
                      show_error, show_info)


class DetailsWindow(ctk.CTkToplevel):
    """Разбор попытки: ответ сотрудника и правильный ответ по каждому вопросу."""

    def __init__(self, master, row: dict):
        super().__init__(master)
        self.title("Разбор попытки")
        self.geometry("1100x560")
        ctk.CTkLabel(self, text=f"{row['user']} - {row['course']}",
                     font=FONT_BOLD).pack(anchor="w", padx=16, pady=(14, 0))
        ctk.CTkLabel(self, text=f"{row['date']}   баллы {row['score']}   "
                                f"{fmt_pct(row['percent'])}   {row['status']}",
                     font=FONT).pack(anchor="w", padx=16)
        table = DataTable(self, [("question", "Вопрос", 420), ("chosen", "Ответ сотрудника", 270),
                                 ("right", "Правильный ответ", 270), ("mark", "Оценка", 80)],
                          height=12)
        table.pack(fill="both", expand=True, padx=16, pady=10)
        table.load([{"question": d["question"],
                     "chosen": "; ".join(d["chosen"]) or "нет ответа",
                     "right": "; ".join(d["right"]),
                     "mark": "верно" if d["ok"] else "неверно"}
                    for d in testing.test_details(row["id"])])
        if row.get("comment"):
            ctk.CTkLabel(self, text=f"Комментарий: {row['comment']}", font=FONT,
                         wraplength=850, justify="left").pack(anchor="w", padx=16)
        ctk.CTkButton(self, text="Закрыть", command=self.destroy).pack(pady=12)


class ResultsView(ctk.CTkFrame):
    """Сотрудник видит свои попытки, преподаватель и администратор - все."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.own_only = app.user.role == config.ROLE_EMPLOYEE
        PageHeader(self, "Результаты тестирования",
                   "Мои попытки" if self.own_only else "Попытки всех сотрудников").pack(anchor="w")
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=10)
        self.course_list = courses.list_courses()
        self.course_menu = ctk.CTkOptionMenu(
            bar, values=["Все курсы"] + [c["title"] for c in self.course_list],
            width=320, command=lambda _v: self.reload())
        self.course_menu.pack(side="left")
        if not self.own_only:
            self.search = ctk.CTkEntry(bar, placeholder_text="ФИО сотрудника", width=220)
            self.search.pack(side="left", padx=8)
            self.search.bind("<KeyRelease>", lambda _e: self.reload())
        if auth.can(app.user, "comment"):
            ctk.CTkButton(bar, text="Комментарий", width=130,
                          command=self.comment).pack(side="right")
        ctk.CTkButton(bar, text="Разбор попытки", width=140,
                      command=self.details).pack(side="right", padx=6)
        columns = [("date", "Дата", 130), ("user", "Сотрудник", 220),
                   ("department", "Подразделение", 190), ("course", "Курс", 300),
                   ("score", "Баллы", 80), ("percent", "%", 60), ("status", "Итог", 80),
                   ("comment", "Комментарий", 220)]
        if self.own_only:
            # свои попытки: ФИО и подразделение одинаковы во всех строках
            columns = [c for c in columns if c[0] not in ("user", "department")]
        self.table = DataTable(self, columns, height=18)
        self.table.pack(fill="both", expand=True)
        self.table.on_double_click(self.details)
        self.summary = ctk.CTkLabel(self, text="", font=FONT)
        self.summary.pack(anchor="w", pady=6)
        self.reload()

    def reload(self):
        title = self.course_menu.get()
        course_id = next((c["id"] for c in self.course_list if c["title"] == title), None)
        text = "" if self.own_only else self.search.get()
        try:
            self.rows = testing.list_results(self.app.user.id if self.own_only else None,
                                             course_id, text)
        except Exception as exc:
            journal.error(f"результаты: {exc}", self.app.user.id)
            show_error(f"Не удалось загрузить результаты: {exc}", self)
            return
        self.table.load(self.rows)
        if self.rows:
            avg = round_half_up(sum(r["percent"] for r in self.rows) / len(self.rows), 1)
            passed = sum(1 for r in self.rows if r["status"] == "Сдан")
            self.summary.configure(text=f"Попыток: {len(self.rows)}   сдано: {passed}   "
                                        f"средний результат: {fmt_pct(avg)}")
        else:
            self.summary.configure(text="Попыток не найдено")

    def _row(self):
        row = self.table.selected()
        if row is None:
            show_info("Выберите попытку в таблице", self)
        return row

    def details(self):
        row = self._row()
        if row:
            DetailsWindow(self, row)

    def comment(self):
        row = self._row()
        if not row:
            return
        text = TextInputDialog.ask(self, "Комментарий к результату",
                                   f"{row['user']}, курс «{row['course']}»",
                                   row.get("comment") or "")
        if text is None:
            return
        testing.set_comment(row["id"], text, self.app.user.id)
        self.reload()
