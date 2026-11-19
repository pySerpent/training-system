"""Общие элементы интерфейса: таблица, заголовок раздела, диалоговые окна."""
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from ..utils import fmt_num

FONT = ("Segoe UI", 13)
FONT_BOLD = ("Segoe UI", 13, "bold")
FONT_TITLE = ("Segoe UI", 20, "bold")


def show_error(text: str, parent=None):
    """Сообщение об ошибке, понятное пользователю."""
    messagebox.showerror("Ошибка", text, parent=parent)


def show_info(text: str, parent=None):
    """Информационное сообщение."""
    messagebox.showinfo("Сообщение", text, parent=parent)


def style_treeview(dark: bool):
    """Настраивает вид таблиц ttk под светлую или тёмную тему."""
    style = ttk.Style()
    style.theme_use("default")
    bg, fg, head = ("#2b2b2b", "#e8e8e8", "#3a3a3a") if dark else \
        ("#ffffff", "#1f1f1f", "#e6e9ee")
    # высота строки в пикселях, поэтому пересчитывается под масштаб экрана
    try:
        px_per_pt = float(style.tk.call("tk", "scaling"))
    except tk.TclError:
        px_per_pt = 1.33
    style.configure("Treeview", background=bg, fieldbackground=bg, foreground=fg,
                    rowheight=max(26, int(12 * px_per_pt * 1.75)), font=("Segoe UI", 12))
    style.configure("Treeview.Heading", background=head, foreground=fg,
                    font=("Segoe UI", 12, "bold"))
    style.map("Treeview", background=[("selected", "#2f6fb5")],
              foreground=[("selected", "#ffffff")])


class PageHeader(ctk.CTkFrame):
    """Заголовок раздела с подзаголовком."""

    def __init__(self, master, title: str, subtitle: str = ""):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=title, font=FONT_TITLE).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(self, text=subtitle, font=FONT,
                         text_color=("gray35", "gray70")).pack(anchor="w")


class DataTable(ctk.CTkFrame):
    """Таблица на основе ttk.Treeview с прокруткой и сортировкой по столбцу."""

    def __init__(self, master, columns: list, height: int = 14):
        super().__init__(master)
        self.columns = columns  # [(ключ, заголовок, ширина)]
        self.rows = []
        self.tree = ttk.Treeview(self, columns=[c[0] for c in columns],
                                 show="headings", height=height,
                                 selectmode="browse")
        # ширины заданы для обычного экрана, на мониторе с масштабом 125-150 %
        # они увеличиваются вместе со шрифтом
        scale = max(1.0, float(self.tk.call("tk", "scaling")) / 1.333)
        for key, title, width in columns:
            self.tree.heading(key, text=title,
                              command=lambda k=key: self.sort_by(k))
            self.tree.column(key, width=int(width * scale), anchor="w")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._reverse = False

    def load(self, rows: list):
        """Заполняет таблицу списком словарей."""
        self.rows = rows
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(rows):
            values = [fmt_num(row.get(c[0], "")) for c in self.columns]
            self.tree.insert("", "end", iid=str(i), values=values)

    def selected(self) -> dict | None:
        """Выбранная строка или None."""
        sel = self.tree.selection()
        return self.rows[int(sel[0])] if sel else None

    def sort_by(self, key: str):
        """Сортирует строки по столбцу; повторный щелчок меняет порядок."""
        self._reverse = not self._reverse
        self.load(sorted(self.rows, key=lambda r: (str(r.get(key, "")).lower()
                                                    if not isinstance(r.get(key), (int, float))
                                                    else r.get(key)),
                         reverse=self._reverse))

    def on_double_click(self, callback):
        """Обработчик двойного щелчка по строке."""
        self.tree.bind("<Double-1>", lambda _e: callback())


class ConfirmDialog(ctk.CTkToplevel):
    """Модальное окно подтверждения действия (например, удаления)."""

    def __init__(self, master, title: str, text: str):
        super().__init__(master)
        self.title(title)
        self.result = False
        self.resizable(False, False)
        ctk.CTkLabel(self, text=text, font=FONT, wraplength=380,
                     justify="left").pack(padx=24, pady=(22, 14))
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=(0, 18))
        ctk.CTkButton(buttons, text="Да", width=110,
                      command=self._yes).pack(side="left", padx=6)
        ctk.CTkButton(buttons, text="Отмена", width=110, fg_color="gray50",
                      command=self.destroy).pack(side="left", padx=6)
        self._make_modal(master)

    def _make_modal(self, master):
        self.transient(master.winfo_toplevel())
        self.after(50, self.grab_set)
        self.focus_force()

    def _yes(self):
        self.result = True
        self.destroy()

    @classmethod
    def ask(cls, master, title: str, text: str) -> bool:
        """Показывает окно и ждёт ответа пользователя."""
        dialog = cls(master, title, text)
        master.wait_window(dialog)
        return dialog.result


class TextInputDialog(ctk.CTkToplevel):
    """Диалог ввода многострочного текста, например комментария к оценке."""

    def __init__(self, master, title: str, prompt: str, initial: str = ""):
        super().__init__(master)
        self.title(title)
        self.value = None
        self.geometry("460x300")
        ctk.CTkLabel(self, text=prompt, font=FONT, wraplength=420,
                     justify="left").pack(padx=18, pady=(16, 8), anchor="w")
        self.box = ctk.CTkTextbox(self, height=150, font=FONT)
        self.box.pack(fill="both", expand=True, padx=18)
        self.box.insert("1.0", initial)
        self.counter = ctk.CTkLabel(self, text="", font=("Segoe UI", 11))
        self.counter.pack(anchor="e", padx=18)
        self.box.bind("<KeyRelease>", lambda _e: self._count())
        self._count()
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=10)
        ctk.CTkButton(buttons, text="Сохранить", width=120,
                      command=self._save).pack(side="left", padx=6)
        ctk.CTkButton(buttons, text="Отмена", width=120, fg_color="gray50",
                      command=self.destroy).pack(side="left", padx=6)
        self.transient(master.winfo_toplevel())
        self.after(50, self.grab_set)

    def _count(self):
        length = len(self.box.get("1.0", "end").strip())
        self.counter.configure(text=f"{length} / 500")

    def _save(self):
        text = self.box.get("1.0", "end").strip()
        if len(text) > 500:
            show_error("Комментарий длиннее 500 символов", self)
            return
        self.value = text
        self.destroy()

    @classmethod
    def ask(cls, master, title: str, prompt: str, initial: str = ""):
        dialog = cls(master, title, prompt, initial)
        master.wait_window(dialog)
        return dialog.value


def labeled_entry(master, label: str, row: int, show: str = "", width: int = 300):
    """Подпись и поле ввода в сетке формы. Возвращает поле."""
    ctk.CTkLabel(master, text=label, font=FONT).grid(row=row, column=0, sticky="w",
                                                     padx=(0, 12), pady=6)
    entry = ctk.CTkEntry(master, width=width, show=show, font=FONT)
    entry.grid(row=row, column=1, sticky="w", pady=6)
    return entry


def set_entry(entry, value: str):
    """Заменяет текст в поле ввода."""
    entry.delete(0, tk.END)
    entry.insert(0, value or "")
