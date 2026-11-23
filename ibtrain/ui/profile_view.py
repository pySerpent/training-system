"""Личный кабинет (форма 15): данные пользователя, назначения, смена пароля."""
import customtkinter as ctk

from ..services import auth, testing, users
from .widgets import FONT, FONT_BOLD, DataTable, PageHeader, labeled_entry, show_error, show_info


class ProfileView(ctk.CTkFrame):
    """Сведения об учётной записи и собственный прогресс обучения."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        data = users.get_user(app.user.id)
        PageHeader(self, "Личный кабинет", app.user.full_name).pack(anchor="w")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, pady=10)

        card = ctk.CTkFrame(body)
        card.pack(side="left", fill="y", padx=(0, 14))
        ctk.CTkLabel(card, text="Учётная запись", font=FONT_BOLD).pack(anchor="w", padx=16, pady=(14, 6))
        for label, value in [("Логин", data["login"]), ("Роль", app.user.role_title),
                             ("Подразделение", data["department"] or "-"),
                             ("Должность", data["position"] or "-"),
                             ("E-mail", data["email"] or "-"),
                             ("Последний вход", data.get("last_login") or "-")]:
            ctk.CTkLabel(card, text=f"{label}: {value}", font=FONT, wraplength=300,
                         justify="left").pack(anchor="w", padx=16, pady=2)

        ctk.CTkLabel(card, text="Смена пароля", font=FONT_BOLD).pack(anchor="w", padx=16, pady=(18, 4))
        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(padx=16, anchor="w")
        self.old = labeled_entry(form, "Текущий", 0, show="•", width=180)
        self.new = labeled_entry(form, "Новый", 1, show="•", width=180)
        self.repeat = labeled_entry(form, "Повтор", 2, show="•", width=180)
        ctk.CTkLabel(card, text="Не короче 8 символов: буквы, цифры\nи хотя бы один спецсимвол",
                     font=("Segoe UI", 11), text_color="gray50", justify="left").pack(anchor="w", padx=16)
        ctk.CTkButton(card, text="Изменить пароль", command=self.change_password).pack(
            anchor="w", padx=16, pady=12)

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(right, text="Мои курсы", font=FONT_BOLD).pack(anchor="w")
        courses_table = DataTable(right, [("title", "Курс", 340), ("due", "Срок", 100),
                                          ("tries", "Попыток", 80), ("best", "Лучший %", 90),
                                          ("state", "Состояние", 120)], height=7)
        courses_table.pack(fill="x", pady=(4, 12))
        rows = testing.available_courses(app.user.id)
        for row in rows:
            row["state"] = "Пройден" if row["best"] >= self._threshold() else \
                ("Не начат" if not row["tries"] else "В процессе")
        courses_table.load(rows)
        ctk.CTkLabel(right, text="Мои последние попытки", font=FONT_BOLD).pack(anchor="w")
        attempts = DataTable(right, [("date", "Дата", 130), ("course", "Курс", 300),
                                     ("percent", "%", 60), ("status", "Итог", 90)], height=7)
        attempts.pack(fill="both", expand=True, pady=4)
        attempts.load(testing.list_results(app.user.id)[:10])

    @staticmethod
    def _threshold() -> int:
        from ..services import settings
        return settings.get_int("pass_threshold", 70)

    def change_password(self):
        try:
            auth.change_password(self.app.user.id, self.old.get(), self.new.get(),
                                 self.repeat.get())
        except auth.AuthError as exc:
            show_error(str(exc), self)
            return
        for entry in (self.old, self.new, self.repeat):
            entry.delete(0, "end")
        show_info("Пароль изменён", self)
