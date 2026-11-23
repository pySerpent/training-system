"""Выгрузка протоколов тестирования в Word и Excel (форма 12)."""
import os
from datetime import datetime, timedelta
from tkinter import filedialog

import customtkinter as ctk

from .. import config
from ..services import courses, journal, reports, testing, users
from .widgets import FONT, FONT_BOLD, DataTable, PageHeader, show_error, show_info


class ExportView(ctk.CTkFrame):
    """Отбор попыток по курсу, подразделению и периоду, предпросмотр и выгрузка."""

    PERIODS = {"За всё время": None, "За 7 дней": 7, "За 30 дней": 30, "За 90 дней": 90}

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app, self.rows = app, []
        PageHeader(self, "Отчёты", "Протокол тестирования в форматах .docx и .xlsx").pack(anchor="w")
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=10)
        self.course_list = courses.list_courses()
        self.course = ctk.CTkOptionMenu(bar, width=300, command=lambda _v: self.preview(),
                                        values=["Все курсы"] + [c["title"] for c in self.course_list])
        self.course.pack(side="left")
        self.department = ctk.CTkOptionMenu(bar, width=230, command=lambda _v: self.preview(),
                                            values=["Все подразделения"] + users.departments())
        self.department.pack(side="left", padx=8)
        self.period = ctk.CTkOptionMenu(bar, width=150, values=list(self.PERIODS),
                                        command=lambda _v: self.preview())
        self.period.pack(side="left")
        self.only_failed = ctk.CTkCheckBox(bar, text="Только несданные", font=FONT,
                                           command=self.preview)
        self.only_failed.pack(side="left", padx=12)

        self.table = DataTable(self, [("date", "Дата", 130), ("user", "Сотрудник", 230),
                                      ("department", "Подразделение", 200),
                                      ("course", "Курс", 320), ("percent", "%", 60),
                                      ("status", "Итог", 80)], height=14)
        self.table.pack(fill="both", expand=True)
        self.count = ctk.CTkLabel(self, text="", font=FONT)
        self.count.pack(anchor="w", pady=6)

        out = ctk.CTkFrame(self)
        out.pack(fill="x", pady=4)
        ctk.CTkLabel(out, text="Выгрузка", font=FONT_BOLD).grid(row=0, column=0, padx=14, pady=10, sticky="w")
        self.details = ctk.CTkCheckBox(out, text="Добавить в Word разбор ответов", font=FONT)
        self.details.grid(row=0, column=1, padx=8)
        ctk.CTkButton(out, text="Сохранить .docx", width=150,
                      command=lambda: self.export("docx")).grid(row=0, column=2, padx=6)
        ctk.CTkButton(out, text="Сохранить .xlsx", width=150,
                      command=lambda: self.export("xlsx")).grid(row=0, column=3, padx=6)
        ctk.CTkButton(out, text="Открыть папку отчётов", width=190, fg_color="gray50",
                      command=self.open_folder).grid(row=0, column=4, padx=6)
        self.preview()

    def _filtered(self) -> list:
        """Применяет фильтры формы к списку завершённых попыток."""
        course_id = next((c["id"] for c in self.course_list
                          if c["title"] == self.course.get()), None)
        rows = testing.list_results(None, course_id)
        dep = self.department.get()
        if dep != "Все подразделения":
            rows = [r for r in rows if r["department"] == dep]
        days = self.PERIODS[self.period.get()]
        if days:
            since = datetime.now() - timedelta(days=days)
            rows = [r for r in rows
                    if datetime.strptime(r["date"], "%d.%m.%Y %H:%M") >= since]
        if self.only_failed.get():
            rows = [r for r in rows if r["status"] != "Сдан"]
        return rows

    def preview(self):
        self.rows = self._filtered()
        self.table.load(self.rows)
        self.count.configure(text=f"В отчёт попадёт попыток: {len(self.rows)}")

    def export(self, ext: str):
        if not self.rows:
            show_info("Нет данных для выгрузки, измените условия отбора", self)
            return
        config.ensure_dirs()
        path = filedialog.asksaveasfilename(
            parent=self, initialdir=config.REPORTS_DIR, initialfile=reports.default_name(ext),
            defaultextension=f".{ext}",
            filetypes=[("Документ Word", "*.docx")] if ext == "docx" else [("Книга Excel", "*.xlsx")])
        if not path:
            return
        try:
            if ext == "docx":
                reports.export_docx(self.rows, path, self.app.user.id, bool(self.details.get()))
            else:
                reports.export_xlsx(self.rows, path, self.app.user.id)
        except PermissionError:
            show_error("Файл открыт в другой программе. Закройте его и повторите", self)
            return
        except Exception as exc:
            journal.error(f"выгрузка {ext}: {exc}", self.app.user.id)
            show_error(f"Не удалось сохранить отчёт: {exc}", self)
            return
        show_info(f"Отчёт сохранён:\n{path}", self)

    def open_folder(self):
        config.ensure_dirs()
        try:
            os.startfile(config.REPORTS_DIR)  # только Windows
        except OSError as exc:
            show_error(f"Папка не открылась: {exc}", self)
