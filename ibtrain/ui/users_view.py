"""Управление пользователями (форма 3) и карточка пользователя (форма 4)."""
import customtkinter as ctk

from .. import config
from ..services import users
from .widgets import (FONT, ConfirmDialog, DataTable, PageHeader,
                      labeled_entry, set_entry, show_error, show_info)


class UserDialog(ctk.CTkToplevel):
    """Окно добавления и редактирования учётной записи."""

    def __init__(self, master, app, user_id: int | None = None):
        super().__init__(master)
        self.app, self.user_id, self.saved = app, user_id, False
        self.title("Новый пользователь" if user_id is None else "Карточка пользователя")
        self.geometry("540x470")
        self.resizable(False, False)
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(padx=22, pady=18, fill="both")
        # отступ между подписью и полем, иначе «Подразделение» упирается в поле
        form.grid_columnconfigure(0, pad=24)
        self.full_name = labeled_entry(form, "ФИО", 0)
        self.login = labeled_entry(form, "Логин", 1)
        self.position = labeled_entry(form, "Должность", 2)
        self.email = labeled_entry(form, "E-mail", 3)
        ctk.CTkLabel(form, text="Подразделение", font=FONT).grid(row=4, column=0,
                                                              sticky="w", pady=6)
        self.department = ctk.CTkComboBox(form, width=300, font=FONT,
                                          values=users.departments())
        self.department.grid(row=4, column=1, sticky="w")
        ctk.CTkLabel(form, text="Роль", font=FONT).grid(row=5, column=0,
                                                     sticky="w", pady=6)
        self.roles = users.roles()
        self.role = ctk.CTkOptionMenu(form, width=300, font=FONT,
                                      values=[t for _c, t in self.roles])
        self.role.grid(row=5, column=1, sticky="w")
        self.password = labeled_entry(form, "Пароль", 6, show="•")
        hint = "Пароль обязателен" if user_id is None else \
            "Оставьте пустым, чтобы не менять пароль"
        ctk.CTkLabel(form, text=hint, font=("Segoe UI", 11),
                     text_color="gray50").grid(row=7, column=1, sticky="w")
        if user_id is not None:
            self._fill(users.get_user(user_id))
        else:
            self.department.set("")
            self.role.set(config.ROLE_TITLES[config.ROLE_EMPLOYEE])
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=10)
        ctk.CTkButton(buttons, text="Сохранить", command=self._save).pack(side="left", padx=6)
        ctk.CTkButton(buttons, text="Отмена", fg_color="gray50",
                      command=self.destroy).pack(side="left", padx=6)
        self.transient(master.winfo_toplevel())
        self.after(50, self.grab_set)

    def _fill(self, data: dict):
        set_entry(self.full_name, data["full_name"])
        set_entry(self.login, data["login"])
        set_entry(self.position, data["position"])
        set_entry(self.email, data["email"])
        self.department.set(data["department"])
        self.role.set(config.ROLE_TITLES[data["role_code"]])

    def _save(self):
        role_code = next(c for c, t in self.roles if t == self.role.get())
        data = {"full_name": self.full_name.get(), "login": self.login.get().strip(),
                "position": self.position.get(), "email": self.email.get(),
                "department": self.department.get(), "role_code": role_code,
                "password": self.password.get()}
        try:
            users.save_user(data, self.user_id, self.app.user.id)
        except users.ValidationError as exc:
            show_error(str(exc), self)
            return
        except Exception as exc:
            show_error(f"Ошибка базы данных: {exc}", self)
            return
        self.saved = True
        self.destroy()


class UsersView(ctk.CTkFrame):
    """Таблица пользователей с поиском и кнопками действий."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        PageHeader(self, "Пользователи", "Учётные записи сотрудников и их роли").pack(anchor="w")
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=10)
        self.search = ctk.CTkEntry(bar, placeholder_text="Поиск по ФИО или логину",
                                   width=280, font=FONT)
        self.search.pack(side="left")
        self.search.bind("<KeyRelease>", lambda _e: self.reload())
        self.role_filter = ctk.CTkOptionMenu(
            bar, values=["Все роли"] + list(config.ROLE_TITLES.values()),
            command=lambda _v: self.reload(), width=160)
        self.role_filter.pack(side="left", padx=8)
        for text, cmd, color in [("Добавить", self.add, None),
                                 ("Изменить", self.edit, None),
                                 ("Блок / разблок", self.toggle_block, "#7f8c8d"),
                                 ("Удалить", self.delete, "#c0392b")]:
            ctk.CTkButton(bar, text=text, width=120, command=cmd,
                          **({"fg_color": color} if color else {})).pack(side="right", padx=4)
        self.table = DataTable(self, [("full_name", "ФИО", 240), ("login", "Логин", 110),
                                      ("role", "Роль", 120), ("department", "Подразделение", 200),
                                      ("position", "Должность", 180), ("status", "Статус", 110),
                                      ("last_login", "Последний вход", 130)], height=18)
        self.table.pack(fill="both", expand=True)
        self.table.on_double_click(self.edit)
        self.reload()

    def reload(self):
        role = self.role_filter.get()
        code = next((c for c, t in config.ROLE_TITLES.items() if t == role), "")
        try:
            self.table.load(users.list_users(self.search.get(), code))
        except Exception as exc:
            show_error(f"Не удалось загрузить список: {exc}", self)

    def _selected(self):
        row = self.table.selected()
        if row is None:
            show_info("Выберите пользователя в таблице", self)
        return row

    def add(self):
        dialog = UserDialog(self, self.app)
        self.wait_window(dialog)
        if dialog.saved:
            self.reload()

    def edit(self):
        row = self._selected()
        if row:
            dialog = UserDialog(self, self.app, row["id"])
            self.wait_window(dialog)
            if dialog.saved:
                self.reload()

    def toggle_block(self):
        row = self._selected()
        if not row:
            return
        block = row["status"] == "Активен"
        try:
            users.set_blocked(row["id"], block, self.app.user.id)
        except users.ValidationError as exc:
            show_error(str(exc), self)
        self.reload()

    def delete(self):
        row = self._selected()
        if not row or not ConfirmDialog.ask(
                self, "Удаление", f"Удалить пользователя {row['full_name']}?"):
            return
        try:
            users.delete_user(row["id"], self.app.user.id)
        except users.ValidationError as exc:
            show_error(str(exc), self)
        self.reload()
