"""Курсы и модули (форма 5), учебный материал (форма 6), назначение курса."""
from datetime import datetime, timedelta

import customtkinter as ctk

from ..services import courses, users
from .widgets import (FONT, FONT_BOLD, ConfirmDialog, DataTable, PageHeader,
                      set_entry, show_error, show_info)


class ModuleDialog(ctk.CTkToplevel):
    """Создание и редактирование модуля с учебным текстом."""

    def __init__(self, master, app, course_id: int, module: dict | None = None):
        super().__init__(master)
        self.app, self.course_id, self.module, self.saved = app, course_id, module, False
        self.title("Модуль курса")
        self.geometry("640x520")
        ctk.CTkLabel(self, text="Название модуля", font=FONT).pack(anchor="w", padx=18, pady=(14, 2))
        self.name = ctk.CTkEntry(self, font=FONT)
        self.name.pack(fill="x", padx=18)
        ctk.CTkLabel(self, text="Учебный материал", font=FONT).pack(anchor="w", padx=18, pady=(10, 2))
        self.text = ctk.CTkTextbox(self, font=FONT, wrap="word")
        self.text.pack(fill="both", expand=True, padx=18)
        if module:
            set_entry(self.name, module["title"])
            self.text.insert("1.0", module["content"])
        ctk.CTkButton(self, text="Сохранить", command=self._save).pack(pady=12)
        self.transient(master.winfo_toplevel())
        self.after(50, self.grab_set)

    def _save(self):
        try:
            courses.save_module(self.course_id, self.name.get(),
                                self.text.get("1.0", "end"),
                                self.module["id"] if self.module else None,
                                self.app.user.id)
        except courses.ValidationError as exc:
            show_error(str(exc), self)
            return
        except Exception as exc:
            show_error(f"Ошибка базы данных: {exc}", self)
            return
        self.saved = True
        self.destroy()


class MaterialWindow(ctk.CTkToplevel):
    """Окно чтения учебного материала модуля."""

    def __init__(self, master, module_id: int):
        super().__init__(master)
        data = courses.module_content(module_id)
        self.title(f"Материал: {data['title']}")
        self.geometry("700x520")
        ctk.CTkLabel(self, text=data["course"], font=("Segoe UI", 12),
                     text_color="gray50").pack(anchor="w", padx=20, pady=(16, 0))
        ctk.CTkLabel(self, text=data["title"], font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=20)
        box = ctk.CTkTextbox(self, font=("Segoe UI", 14), wrap="word")
        box.pack(fill="both", expand=True, padx=20, pady=12)
        box.insert("1.0", data["content"] or "Материал пока не добавлен")
        box.configure(state="disabled")
        ctk.CTkButton(self, text="Закрыть", command=self.destroy).pack(pady=(0, 14))


class AssignDialog(ctk.CTkToplevel):
    """Назначение курса сотрудникам подразделения со сроком."""

    def __init__(self, master, app, course: dict):
        super().__init__(master)
        self.app, self.course = app, course
        self.title("Назначение курса")
        self.geometry("440x260")
        ctk.CTkLabel(self, text=f"Курс «{course['title']}»", font=FONT_BOLD,
                     wraplength=400).pack(padx=18, pady=(16, 8))
        ctk.CTkLabel(self, text="Подразделение (пусто - все сотрудники)", font=FONT).pack()
        self.dep = ctk.CTkComboBox(self, values=[""] + users.departments(), width=300)
        self.dep.set("")
        self.dep.pack(pady=4)
        ctk.CTkLabel(self, text="Срок, дней", font=FONT).pack()
        self.days = ctk.CTkEntry(self, width=80)
        self.days.insert(0, "14")
        self.days.pack(pady=4)
        ctk.CTkButton(self, text="Назначить", command=self._assign).pack(pady=10)
        self.transient(master.winfo_toplevel())
        self.after(50, self.grab_set)

    def _assign(self):
        try:
            days = int(self.days.get())
            if not 1 <= days <= 365:
                raise ValueError
        except ValueError:
            show_error("Срок указывается целым числом дней от 1 до 365", self)
            return
        due = datetime.now() + timedelta(days=days)
        count = courses.assign_course(self.course["id"], self.dep.get(), due,
                                      self.app.user.id)
        show_info(f"Курс назначен, новых назначений: {count}", self)
        self.destroy()


class CoursesView(ctk.CTkFrame):
    """Список курсов слева, карточка курса и его модули справа."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app, self.course = app, None
        PageHeader(self, "Курсы и модули", "Учебные курсы по информационной безопасности").pack(anchor="w")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, pady=10)
        left = ctk.CTkFrame(body, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)
        self.table = DataTable(left, [("title", "Курс", 360), ("modules", "Модулей", 80),
                                      ("questions", "Вопросов", 80)], height=12)
        self.table.pack(fill="both", expand=True)
        self.table.tree.bind("<<TreeviewSelect>>", lambda _e: self.select_course())
        lb = ctk.CTkFrame(left, fg_color="transparent")
        lb.pack(fill="x", pady=6)
        ctk.CTkButton(lb, text="Новый курс", width=120, command=self.new_course).pack(side="left")
        ctk.CTkButton(lb, text="Назначить", width=120, command=self.assign).pack(side="left", padx=6)
        ctk.CTkButton(lb, text="Удалить курс", width=120, fg_color="#c0392b",
                      command=self.delete_course).pack(side="left")

        right = ctk.CTkFrame(body)
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))
        ctk.CTkLabel(right, text="Название", font=FONT).pack(anchor="w", padx=14, pady=(12, 0))
        self.title_entry = ctk.CTkEntry(right, font=FONT)
        self.title_entry.pack(fill="x", padx=14)
        ctk.CTkLabel(right, text="Описание", font=FONT).pack(anchor="w", padx=14, pady=(8, 0))
        self.descr = ctk.CTkTextbox(right, height=70, font=FONT, wrap="word")
        self.descr.pack(fill="x", padx=14)
        self.active = ctk.CTkCheckBox(right, text="Активен (доступен сотрудникам)", font=FONT)
        self.active.pack(anchor="w", padx=14, pady=6)
        ctk.CTkButton(right, text="Сохранить курс", command=self.save_course).pack(anchor="w", padx=14)
        ctk.CTkLabel(right, text="Модули", font=FONT_BOLD).pack(anchor="w", padx=14, pady=(12, 2))
        self.modules = DataTable(right, [("position", "№", 40), ("title", "Модуль", 260),
                                         ("questions", "Вопросов", 80)], height=6)
        self.modules.pack(fill="both", expand=True, padx=14)
        self.modules.on_double_click(self.edit_module)
        mb = ctk.CTkFrame(right, fg_color="transparent")
        mb.pack(fill="x", padx=14, pady=8)
        for text, cmd in [("Добавить", self.add_module), ("Изменить", self.edit_module),
                          ("Материал", self.view_material), ("Удалить", self.delete_module)]:
            ctk.CTkButton(mb, text=text, width=100, command=cmd).pack(side="left", padx=(0, 6))
        self.reload()

    def reload(self):
        self.table.load(courses.list_courses())

    def select_course(self):
        self.course = self.table.selected()
        if not self.course:
            return
        set_entry(self.title_entry, self.course["title"])
        self.descr.delete("1.0", "end")
        self.descr.insert("1.0", self.course["description"])
        self.active.select() if self.course["active"] else self.active.deselect()
        self.modules.load(courses.list_modules(self.course["id"]))

    def new_course(self):
        self.course = None
        set_entry(self.title_entry, "")
        self.descr.delete("1.0", "end")
        self.active.select()
        self.modules.load([])
        self.title_entry.focus()

    def save_course(self):
        try:
            courses.save_course(self.title_entry.get(), self.descr.get("1.0", "end"),
                                bool(self.active.get()),
                                self.course["id"] if self.course else None,
                                self.app.user.id)
        except courses.ValidationError as exc:
            show_error(str(exc), self)
            return
        except Exception as exc:
            show_error(f"Ошибка базы данных: {exc}", self)
            return
        self.reload()
        show_info("Курс сохранён", self)

    def delete_course(self):
        if not self.course or not ConfirmDialog.ask(
                self, "Удаление курса", f"Удалить курс «{self.course['title']}» "
                                        "со всеми модулями и вопросами?"):
            return
        try:
            courses.delete_course(self.course["id"], self.app.user.id)
        except courses.ValidationError as exc:
            show_error(str(exc), self)
        self.new_course()
        self.reload()

    def assign(self):
        if not self.course:
            show_info("Выберите курс", self)
            return
        AssignDialog(self, self.app, self.course)

    def _module(self):
        row = self.modules.selected()
        if row is None:
            show_info("Выберите модуль", self)
        return row

    def add_module(self):
        if not self.course:
            show_info("Сначала сохраните или выберите курс", self)
            return
        dialog = ModuleDialog(self, self.app, self.course["id"])
        self.wait_window(dialog)
        if dialog.saved:
            self.modules.load(courses.list_modules(self.course["id"]))

    def edit_module(self):
        row = self._module()
        if row:
            dialog = ModuleDialog(self, self.app, self.course["id"], row)
            self.wait_window(dialog)
            if dialog.saved:
                self.modules.load(courses.list_modules(self.course["id"]))

    def view_material(self):
        row = self._module()
        if row:
            MaterialWindow(self, row["id"])

    def delete_module(self):
        row = self._module()
        if row and ConfirmDialog.ask(self, "Удаление модуля",
                                     f"Удалить модуль «{row['title']}» и его вопросы?"):
            courses.delete_module(row["id"], self.app.user.id)
            self.modules.load(courses.list_modules(self.course["id"]))
