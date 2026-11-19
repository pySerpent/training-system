"""Создание и редактирование вопросов теста (форма 7)."""
from tkinter import filedialog

import customtkinter as ctk

from .. import config
from ..services import courses, question_io
from .widgets import (FONT, FONT_BOLD, ConfirmDialog, DataTable, PageHeader,
                      show_error, show_info)

MAX_OPTIONS = 6


class QuestionsView(ctk.CTkFrame):
    """Слева выбор курса, модуля и список вопросов, справа редактор вопроса."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app, self.question_id = app, None
        PageHeader(self, "Вопросы тестов",
                   "Одиночный и множественный выбор, отметка правильных ответов").pack(anchor="w")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, pady=10)

        left = ctk.CTkFrame(body, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)
        self.course_list = courses.list_courses()
        self.course_menu = ctk.CTkOptionMenu(
            left, values=[c["title"] for c in self.course_list] or ["нет курсов"],
            command=lambda _v: self.load_modules(), width=360)
        self.course_menu.pack(anchor="w")
        self.module_menu = ctk.CTkOptionMenu(left, values=["-"], width=360,
                                             command=lambda _v: self.load_questions())
        self.module_menu.pack(anchor="w", pady=6)
        self.table = DataTable(left, [("text", "Вопрос", 380), ("type_title", "Тип", 150)],
                               height=14)
        self.table.pack(fill="both", expand=True)
        self.table.tree.bind("<<TreeviewSelect>>", lambda _e: self.edit_selected())
        lb = ctk.CTkFrame(left, fg_color="transparent")
        lb.pack(fill="x", pady=6)
        ctk.CTkButton(lb, text="Новый вопрос", command=self.clear_form).pack(side="left")
        ctk.CTkButton(lb, text="Удалить", fg_color="#c0392b",
                      command=self.delete).pack(side="left", padx=6)
        ctk.CTkButton(lb, text="Импорт из Excel", fg_color="gray50",
                      command=self.import_xlsx).pack(side="left")
        ctk.CTkButton(lb, text="Шаблон", width=80, fg_color="gray50",
                      command=self.save_template).pack(side="left", padx=6)

        right = ctk.CTkFrame(body)
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))
        ctk.CTkLabel(right, text="Текст вопроса", font=FONT_BOLD).pack(anchor="w", padx=14, pady=(12, 2))
        self.text = ctk.CTkTextbox(right, height=80, font=FONT, wrap="word")
        self.text.pack(fill="x", padx=14)
        row = ctk.CTkFrame(right, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=8)
        self.qtype = ctk.CTkSegmentedButton(row, values=list(config.QTYPE_TITLES.values()))
        self.qtype.set(config.QTYPE_TITLES[config.QTYPE_SINGLE])
        self.qtype.pack(side="left")
        ctk.CTkLabel(row, text="Вес", font=FONT).pack(side="left", padx=(16, 4))
        self.weight = ctk.CTkEntry(row, width=60)
        self.weight.pack(side="left")
        ctk.CTkLabel(right, text="Варианты ответа (отметьте правильные)",
                     font=FONT_BOLD).pack(anchor="w", padx=14)
        self.options = []
        for _ in range(MAX_OPTIONS):
            line = ctk.CTkFrame(right, fg_color="transparent")
            line.pack(fill="x", padx=14, pady=2)
            check = ctk.CTkCheckBox(line, text="", width=24)
            check.pack(side="left")
            entry = ctk.CTkEntry(line, font=FONT)
            entry.pack(side="left", fill="x", expand=True)
            self.options.append((entry, check))
        ctk.CTkButton(right, text="Сохранить вопрос",
                      command=self.save).pack(anchor="w", padx=14, pady=10)
        self.clear_form()
        self.load_modules()

    def _course_id(self):
        title = self.course_menu.get()
        return next((c["id"] for c in self.course_list if c["title"] == title), None)

    def load_modules(self):
        course_id = self._course_id()
        self.modules = courses.list_modules(course_id) if course_id else []
        titles = [m["title"] for m in self.modules] or ["-"]
        self.module_menu.configure(values=titles)
        self.module_menu.set(titles[0])
        self.load_questions()

    def _module_id(self):
        title = self.module_menu.get()
        return next((m["id"] for m in self.modules if m["title"] == title), None)

    def load_questions(self):
        module_id = self._module_id()
        self.table.load(courses.list_questions(module_id) if module_id else [])
        self.clear_form()

    def clear_form(self):
        self.question_id = None
        self.text.delete("1.0", "end")
        self.weight.delete(0, "end")
        self.weight.insert(0, "1")
        for entry, check in self.options:
            entry.delete(0, "end")
            check.deselect()

    def edit_selected(self):
        row = self.table.selected()
        if not row:
            return
        self.clear_form()
        self.question_id = row["id"]
        self.text.insert("1.0", row["text"])
        self.qtype.set(config.QTYPE_TITLES[row["qtype"]])
        self.weight.delete(0, "end")
        self.weight.insert(0, f"{row['weight']:g}")
        for (entry, check), (text, ok) in zip(self.options, row["answers"]):
            entry.insert(0, text)
            check.select() if ok else check.deselect()

    def save(self):
        module_id = self._module_id()
        if module_id is None:
            show_info("Сначала создайте модуль в разделе «Курсы и модули»", self)
            return
        qtype = next(c for c, t in config.QTYPE_TITLES.items() if t == self.qtype.get())
        try:
            weight = float(self.weight.get().replace(",", "."))
        except ValueError:
            show_error("Вес вопроса должен быть числом", self)
            return
        answers = [(e.get(), bool(c.get())) for e, c in self.options]
        try:
            courses.save_question(module_id, self.text.get("1.0", "end"), qtype,
                                  weight, answers, self.question_id, self.app.user.id)
        except courses.ValidationError as exc:
            show_error(str(exc), self)
            return
        except Exception as exc:
            show_error(f"Ошибка базы данных: {exc}", self)
            return
        self.load_questions()
        show_info("Вопрос сохранён", self)

    def save_template(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".xlsx",
                                            initialfile="shablon_voprosov.xlsx",
                                            filetypes=[("Книга Excel", "*.xlsx")])
        if not path:
            return
        try:
            question_io.save_template(path)
        except OSError as exc:
            show_error(f"Файл не сохранён: {exc}", self)
            return
        show_info("Шаблон сохранён. Правильные варианты отметьте звёздочкой «*»", self)

    def import_xlsx(self):
        module_id = self._module_id()
        if module_id is None:
            show_info("Выберите модуль, в который нужно добавить вопросы", self)
            return
        path = filedialog.askopenfilename(parent=self, title="Файл с вопросами",
                                          filetypes=[("Книга Excel", "*.xlsx")])
        if not path:
            return
        try:
            added, problems = question_io.import_questions(module_id, path, self.app.user.id)
        except courses.ValidationError as exc:
            show_error(str(exc), self)
            return
        self.load_questions()
        text = f"Добавлено вопросов: {added}"
        if problems:
            text += "\nПропущены:\n" + "\n".join(problems[:10])
        show_info(text, self)

    def delete(self):
        row = self.table.selected()
        if row and ConfirmDialog.ask(self, "Удаление вопроса", "Удалить выбранный вопрос?"):
            courses.delete_question(row["id"], self.app.user.id)
            self.load_questions()
