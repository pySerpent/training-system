"""Главное окно: боковое меню, шапка и область разделов."""
import os

import customtkinter as ctk
from PIL import Image

from .. import config
from ..services import auth, journal, settings
from .widgets import FONT, show_error, style_treeview

# Пункты меню: (ключ права, подпись). Видимость зависит от роли.
MENU = [
    ("dashboard", "Главная"),
    ("tests", "Обучение и тесты"),
    ("results", "Результаты"),
    ("courses", "Курсы и модули"),
    ("questions", "Вопросы тестов"),
    ("users", "Пользователи"),
    ("export", "Отчёты"),
    ("logs", "Журнал действий"),
    ("settings", "Настройки"),
    ("profile", "Личный кабинет"),
    ("help", "Справка"),
]


class MainWindow(ctk.CTk):
    """Окно приложения после входа."""

    def __init__(self, user: auth.CurrentUser):
        super().__init__()
        self.user = user
        self.logout_requested = False
        self.current_view = None
        self.apply_settings()
        self.geometry("1280x760")
        self.minsize(1100, 650)

        # боковая панель с пунктами меню
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.logo_label = ctk.CTkLabel(self.sidebar, text="")
        self.logo_label.pack(pady=(18, 4))
        self.company_label = ctk.CTkLabel(self.sidebar, text="", wraplength=190,
                                          font=("Segoe UI", 14, "bold"))
        self.company_label.pack(padx=10, pady=(0, 16))
        self.buttons = {}
        for key, title in MENU:
            if not auth.can(user, key):
                continue
            button = ctk.CTkButton(self.sidebar, text=title, anchor="w",
                                   height=34, font=FONT, corner_radius=6,
                                   fg_color="transparent",
                                   text_color=("gray10", "gray90"),
                                   hover_color=("gray80", "gray30"),
                                   command=lambda k=key: self.open(k))
            button.pack(fill="x", padx=10, pady=2)
            self.buttons[key] = button
        ctk.CTkButton(self.sidebar, text="Выход", fg_color="gray50", height=32,
                      command=self.logout).pack(side="bottom", fill="x",
                                                padx=10, pady=14)
        ctk.CTkLabel(self.sidebar, text=f"{user.full_name}\n{user.role_title}",
                     font=("Segoe UI", 12), wraplength=190,
                     justify="left").pack(side="bottom", padx=10, anchor="w")

        # область, в которую подставляются разделы
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True, padx=18, pady=14)
        self.refresh_branding()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.open("dashboard")

    def apply_settings(self):
        """Применяет тему оформления из настроек."""
        values = settings.get_all()
        ctk.set_appearance_mode(values.get("theme", "light"))
        style_treeview(values.get("theme") == "dark")
        self.title(f"{config.APP_TITLE} - {values.get('company_name', '')}")

    def refresh_branding(self):
        """Обновляет название компании и логотип в боковой панели."""
        values = settings.get_all()
        self.company_label.configure(text=values.get("company_name", ""))
        path = values.get("logo_path", "")
        if path and os.path.isfile(path):
            try:
                image = Image.open(path)
                image.thumbnail((160, 80))
                self._logo = ctk.CTkImage(image, size=image.size)
                self.logo_label.configure(image=self._logo, text="")
                return
            except OSError as exc:
                journal.error(f"логотип не загружен: {exc}", self.user.id)
        self.logo_label.configure(image=None, text="ИБ", font=("Segoe UI", 28, "bold"))

    def open(self, key: str, **kwargs):
        """Показывает раздел по ключу меню."""
        from . import views  # импорт здесь, чтобы избежать циклической ссылки
        if not auth.can(self.user, key):
            show_error("Недостаточно прав для этого раздела", self)
            return
        if self.current_view is not None:
            self.current_view.destroy()
        for k, button in self.buttons.items():
            button.configure(fg_color=("gray75", "gray25") if k == key
                             else "transparent")
        try:
            self.current_view = views.VIEWS[key](self.content, self, **kwargs)
            self.current_view.pack(fill="both", expand=True)
        except Exception as exc:
            journal.error(f"раздел {key}: {exc}", self.user.id)
            show_error(f"Не удалось открыть раздел: {exc}", self)

    def logout(self):
        """Выход к окну авторизации."""
        journal.write("logout", "", self.user.id)
        self.logout_requested = True
        self.destroy()

    def on_close(self):
        journal.write("logout", "закрытие окна", self.user.id)
        self.destroy()
