"""Журнал действий пользователей (форма 14)."""
import csv
from tkinter import filedialog

import customtkinter as ctk

from ..services import journal
from .widgets import FONT, DataTable, PageHeader, show_error, show_info

PERIODS = {"1 день": 1, "7 дней": 7, "30 дней": 30, "365 дней": 365}


class LogsView(ctk.CTkFrame):
    """Просмотр журнала с отбором по периоду, типу события и тексту."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app, self.rows = app, []
        PageHeader(self, "Журнал действий", "Входы, изменения данных, тесты и ошибки").pack(anchor="w")
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=10)
        self.period = ctk.CTkOptionMenu(bar, values=list(PERIODS), width=120,
                                        command=lambda _v: self.reload())
        self.period.set("30 дней")
        self.period.pack(side="left")
        self.action = ctk.CTkOptionMenu(bar, width=240, command=lambda _v: self.reload(),
                                        values=["Все события"] + list(journal.ACTIONS.values()))
        self.action.pack(side="left", padx=8)
        self.search = ctk.CTkEntry(bar, placeholder_text="Логин или текст", width=220)
        self.search.pack(side="left")
        self.search.bind("<KeyRelease>", lambda _e: self.reload())
        ctk.CTkButton(bar, text="Сохранить в CSV", width=150,
                      command=self.save_csv).pack(side="right")
        self.table = DataTable(self, [("time", "Время", 150), ("login", "Пользователь", 120),
                                      ("action", "Событие", 210), ("level", "Уровень", 80),
                                      ("details", "Подробности", 440)], height=20)
        self.table.pack(fill="both", expand=True)
        self.count = ctk.CTkLabel(self, text="", font=FONT)
        self.count.pack(anchor="w", pady=6)
        self.reload()

    def reload(self):
        title = self.action.get()
        code = next((k for k, v in journal.ACTIONS.items() if v == title), None)
        self.rows = journal.fetch(PERIODS[self.period.get()], code, self.search.get().strip())
        self.table.load(self.rows)
        errors = sum(1 for r in self.rows if r["level"] == "ERROR")
        self.count.configure(text=f"Записей: {len(self.rows)}, из них ошибок: {errors}")

    def save_csv(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv",
                                            initialfile="journal.csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            # utf-8-sig, чтобы Excel правильно показал кириллицу
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["time", "login", "action", "level", "details"],
                                        delimiter=";")
                writer.writeheader()
                writer.writerows(self.rows)
        except OSError as exc:
            show_error(f"Файл не сохранён: {exc}", self)
            return
        journal.write("export", f"журнал в CSV, {len(self.rows)} записей", self.app.user.id)
        show_info("Журнал сохранён", self)
