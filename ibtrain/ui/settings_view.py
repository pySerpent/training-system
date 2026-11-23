"""Панель настроек системы (форма 13): компания, логотип, тема, тестирование, БД."""
import os
from tkinter import filedialog

import customtkinter as ctk

from .. import config
from ..services import journal, settings
from .widgets import FONT, FONT_BOLD, PageHeader, set_entry, show_error, show_info

THEMES = {"light": "Светлая", "dark": "Тёмная", "system": "Как в Windows"}
NUMBERS = [("pass_threshold", "Проходной балл, %"),
           ("test_time_min", "Время на тест, мин"),
           ("questions_per_test", "Вопросов в тесте"),
           ("max_attempts", "Попыток на курс")]


class SettingsView(ctk.CTkFrame):
    """Вкладки панели управления; доступна только администратору."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.values = settings.get_all()
        PageHeader(self, "Настройки", "Параметры организации и тестирования").pack(anchor="w")
        tabs = ctk.CTkTabview(self, height=420)
        tabs.pack(fill="both", expand=True, pady=8)
        self._company_tab(tabs.add("Организация"))
        self._look_tab(tabs.add("Оформление"))
        self._test_tab(tabs.add("Тестирование"))
        self._db_tab(tabs.add("База данных"))
        ctk.CTkButton(self, text="Сохранить настройки", font=FONT_BOLD,
                      command=self.save).pack(anchor="e", pady=6)

    def _row(self, tab, row: int, label: str, width: int = 360):
        ctk.CTkLabel(tab, text=label, font=FONT).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        entry = ctk.CTkEntry(tab, width=width, font=FONT)
        entry.grid(row=row, column=1, sticky="w")
        return entry

    def _company_tab(self, tab):
        self.company = self._row(tab, 0, "Название организации")
        set_entry(self.company, self.values["company_name"])
        self.logo = self._row(tab, 1, "Файл логотипа (PNG, JPG)")
        set_entry(self.logo, self.values["logo_path"])
        ctk.CTkButton(tab, text="Выбрать...", width=100,
                      command=self.choose_logo).grid(row=1, column=2, padx=8)
        ctk.CTkButton(tab, text="Убрать", width=80, fg_color="gray50",
                      command=lambda: set_entry(self.logo, "")).grid(row=1, column=3)

    def _look_tab(self, tab):
        ctk.CTkLabel(tab, text="Тема интерфейса", font=FONT).grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.theme = ctk.CTkSegmentedButton(tab, values=list(THEMES.values()))
        self.theme.set(THEMES.get(self.values["theme"], THEMES["light"]))
        self.theme.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(tab, text="Тема применяется сразу после сохранения",
                     font=("Segoe UI", 11), text_color="gray50").grid(row=1, column=1, sticky="w")

    def _test_tab(self, tab):
        self.numbers = {}
        for i, (key, label) in enumerate(NUMBERS):
            entry = self._row(tab, i, label, 90)
            set_entry(entry, self.values[key])
            self.numbers[key] = entry
        ctk.CTkLabel(tab, text="Изменения действуют для новых попыток",
                     font=("Segoe UI", 11), text_color="gray50").grid(
            row=len(NUMBERS), column=1, sticky="w")

    def _db_tab(self, tab):
        ctk.CTkLabel(tab, text=f"Файл базы данных: {config.DB_PATH}", font=FONT,
                     wraplength=760, justify="left").pack(anchor="w", padx=10, pady=8)
        size = os.path.getsize(config.DB_PATH) / 1024 if os.path.exists(config.DB_PATH) else 0
        ctk.CTkLabel(tab, text=f"Размер: {size:.0f} КБ", font=FONT).pack(anchor="w", padx=10)
        ctk.CTkButton(tab, text="Создать резервную копию", command=self.backup).pack(anchor="w", padx=10, pady=8)
        ctk.CTkButton(tab, text="Копия в выбранную папку", fg_color="gray50",
                      command=lambda: self.backup(ask=True)).pack(anchor="w", padx=10)

    def choose_logo(self):
        path = filedialog.askopenfilename(parent=self, title="Логотип организации",
                                          filetypes=[("Изображения", "*.png *.jpg *.jpeg *.gif")])
        if path:
            set_entry(self.logo, path)

    def collect(self) -> dict:
        values = {"company_name": self.company.get().strip(),
                  "logo_path": self.logo.get().strip(),
                  "theme": next(k for k, v in THEMES.items() if v == self.theme.get())}
        values.update({key: entry.get().strip() for key, entry in self.numbers.items()})
        return values

    def save(self):
        values = self.collect()
        errors = settings.validate(values)
        if errors:
            show_error("\n".join(errors), self)
            return
        try:
            settings.save(values)
        except Exception as exc:
            journal.error(f"настройки: {exc}", self.app.user.id)
            show_error(f"Настройки не сохранены: {exc}", self)
            return
        changed = [k for k, v in values.items() if str(self.values.get(k)) != v]
        journal.write("settings", ", ".join(changed) or "без изменений", self.app.user.id)
        self.values.update(values)
        self.app.apply_settings()
        self.app.refresh_branding()
        show_info("Настройки сохранены", self)

    def backup(self, ask: bool = False):
        target = None
        if ask:
            target = filedialog.askdirectory(parent=self, title="Папка для резервной копии")
            if not target:
                return
        try:
            path = settings.backup_database(target)
        except OSError as exc:
            journal.error(f"резервная копия: {exc}", self.app.user.id)
            show_error(f"Копия не создана: {exc}", self)
            return
        journal.write("backup", os.path.basename(path), self.app.user.id)
        show_info(f"Резервная копия создана:\n{path}", self)
