"""Главная страница с виджетами статистики (форма 2)."""
import tkinter as tk

import customtkinter as ctk

from .. import config
from ..services import testing
from ..utils import fmt_pct
from .widgets import FONT, DataTable, PageHeader


class StatCard(ctk.CTkFrame):
    """Плитка с одним показателем."""

    def __init__(self, master, title: str, value, note: str = ""):
        super().__init__(master, corner_radius=10)
        ctk.CTkLabel(self, text=title, font=("Segoe UI", 12),
                     text_color=("gray35", "gray70")).pack(anchor="w", padx=14,
                                                          pady=(10, 0))
        ctk.CTkLabel(self, text=str(value),
                     font=("Segoe UI", 26, "bold")).pack(anchor="w", padx=14)
        ctk.CTkLabel(self, text=note, font=("Segoe UI", 11),
                     text_color=("gray40", "gray65")).pack(anchor="w", padx=14,
                                                          pady=(0, 10))


class BarChart(tk.Canvas):
    """Горизонтальная диаграмма среднего результата по курсам.

    Название курса пишется над своей полосой, поэтому длинные названия
    не обрезаются. Размеры пересчитываются под масштаб экрана."""

    def __init__(self, master, data: dict, threshold: int, dark: bool):
        bg = "#2b2b2b" if dark else "#ffffff"
        self.k = max(1.0, float(master.tk.call("tk", "scaling")) / 1.333)
        self.row = int(48 * self.k)
        super().__init__(master, height=int(30 * self.k) + self.row * max(len(data), 1),
                         bg=bg, highlightthickness=0)
        self.data, self.threshold, self.dark = data, threshold, dark
        self.bind("<Configure>", lambda _e: self.draw())

    def draw(self):
        self.delete("all")
        k, row = self.k, self.row
        fg = "#e8e8e8" if self.dark else "#1f1f1f"
        left, right = int(12 * k), self.winfo_width() - int(70 * k)
        if not self.data:
            self.create_text(left, int(20 * k), anchor="w", fill=fg,
                             font=("Segoe UI", 11), text="Пока нет завершённых попыток")
            return
        top, bar = int(24 * k), int(18 * k)
        for i, (title, value) in enumerate(self.data.items()):
            y = top + i * row
            self.create_text(left, y, anchor="nw", text=title, fill=fg,
                             font=("Segoe UI", 11))
            y_bar = y + int(22 * k)
            x = left + (right - left) * value / 100
            color = "#2e8b57" if value >= self.threshold else "#d35400"
            self.create_rectangle(left, y_bar, right, y_bar + bar,
                                  fill="#3a3a3a" if self.dark else "#eef0f3", width=0)
            self.create_rectangle(left, y_bar, x, y_bar + bar, fill=color, width=0)
            self.create_text(right + int(8 * k), y_bar + bar // 2, anchor="w",
                             text=fmt_pct(value), fill=fg, font=("Segoe UI", 11, "bold"))
        # линия проходного балла
        tx = left + (right - left) * self.threshold / 100
        self.create_line(tx, int(16 * k), tx, top + row * len(self.data),
                         dash=(4, 3), fill=fg)
        self.create_text(tx, int(4 * k), anchor="n", text=f"порог {self.threshold} %",
                         fill=fg, font=("Segoe UI", 9))


class DashboardView(ctk.CTkFrame):
    """Сводка для руководителя обучения или личная сводка сотрудника."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        employee = app.user.role == config.ROLE_EMPLOYEE
        stats = testing.dashboard_stats(app.user.id if employee else None)
        from ..services import settings
        threshold = settings.get_int("pass_threshold", 70)
        PageHeader(self, f"Здравствуйте, {app.user.full_name}",
                   "Ваши показатели обучения" if employee
                   else "Сводка по обучению сотрудников").pack(anchor="w")

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.pack(fill="x", pady=12)
        items = [("Пройдено тестов", stats["tests"], "завершённые попытки"),
                 ("Средний результат", fmt_pct(stats["avg"]), "по всем попыткам"),
                 ("Доля успешных", fmt_pct(stats["pass_rate"]), f"порог {threshold} %"),
                 ("Просрочено", stats["overdue"], "назначенных курсов")]
        if not employee:
            items.insert(0, ("Пользователей", stats["users"],
                             f"активных курсов: {stats['courses']}"))
        for i, (title, value, note) in enumerate(items):
            StatCard(cards, title, value, note).grid(row=0, column=i, padx=(0, 10),
                                                     sticky="nsew")
            cards.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(self, text="Средний результат по курсам",
                     font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(6, 4))
        BarChart(self, stats["by_course"], threshold,
                 ctk.get_appearance_mode() == "Dark").pack(fill="x")

        ctk.CTkLabel(self, text="Последние попытки",
                     font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(12, 4))
        table = DataTable(self, [("date", "Дата", 130), ("user", "Сотрудник", 230),
                                 ("course", "Курс", 300), ("percent", "%", 60),
                                 ("status", "Итог", 90)], height=6)
        table.pack(fill="both", expand=True)
        rows = testing.list_results(app.user.id if employee else None)
        table.load(rows[:8])
        if employee:
            ctk.CTkButton(self, text="Перейти к тестам", font=FONT,
                          command=lambda: app.open("tests")).pack(anchor="e", pady=8)
