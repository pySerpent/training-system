"""Окно авторизации (форма 1)."""
import customtkinter as ctk

from .. import config
from ..services import auth, settings
from .widgets import FONT, FONT_BOLD, show_error


class LoginWindow(ctk.CTk):
    """Стартовое окно: логин, пароль, кнопка входа."""

    def __init__(self):
        super().__init__()
        self.current_user = None
        values = settings.get_all()
        ctk.set_appearance_mode(values.get("theme", "light"))
        self.title(f"Вход - {config.APP_TITLE}")
        self.geometry("460x430")
        self.resizable(False, False)

        ctk.CTkLabel(self, text=values.get("company_name", ""),
                     font=("Segoe UI", 15)).pack(pady=(30, 2))
        ctk.CTkLabel(self, text="Обучение и контроль знаний\nпо информационной безопасности",
                     font=("Segoe UI", 19, "bold")).pack(pady=(0, 20))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack()
        ctk.CTkLabel(form, text="Логин", font=FONT).pack(anchor="w")
        self.login_entry = ctk.CTkEntry(form, width=300, font=FONT)
        self.login_entry.pack(pady=(0, 10))
        ctk.CTkLabel(form, text="Пароль", font=FONT).pack(anchor="w")
        self.password_entry = ctk.CTkEntry(form, width=300, show="•", font=FONT)
        self.password_entry.pack()
        self.show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(form, text="Показать пароль", variable=self.show_var,
                        command=self._toggle_password,
                        font=("Segoe UI", 12)).pack(anchor="w", pady=8)
        ctk.CTkButton(form, text="Войти", width=300, height=38, font=FONT_BOLD,
                      command=self._login).pack(pady=(6, 0))
        self.status = ctk.CTkLabel(self, text="", text_color="#c0392b", font=FONT)
        self.status.pack(pady=10)
        ctk.CTkLabel(self, text=f"Версия {config.APP_VERSION}",
                     font=("Segoe UI", 11), text_color="gray50").pack(side="bottom",
                                                                    pady=8)
        # Enter в любом поле запускает вход
        self.bind("<Return>", lambda _e: self._login())
        self.login_entry.focus()

    def _toggle_password(self):
        self.password_entry.configure(show="" if self.show_var.get() else "•")

    def _login(self):
        try:
            self.current_user = auth.login(self.login_entry.get(),
                                           self.password_entry.get())
        except auth.AuthError as exc:
            self.status.configure(text=str(exc))
            self.password_entry.delete(0, "end")
            return
        except Exception as exc:  # база недоступна или повреждена
            show_error(f"Не удалось выполнить вход: {exc}", self)
            return
        self.destroy()
