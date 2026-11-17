"""Точка входа: подготовка базы данных, окно входа, главное окно.

Запуск:  python main.py
Восстановить демонстрационную базу:  python main.py --reset-demo
"""
import argparse
import sys
import traceback
from tkinter import messagebox

import customtkinter as ctk

from ibtrain import config
from ibtrain.database import init_db
from ibtrain.seed import reset_demo, seed_if_empty
from ibtrain.services import journal
from ibtrain.ui.login_window import LoginWindow
from ibtrain.ui.main_window import MainWindow


def report_crash(exc_type, exc, tb):
    """Необработанная ошибка попадает в журнал и показывается пользователю."""
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    journal.error(text[-900:])
    messagebox.showerror(config.APP_TITLE, f"Непредвиденная ошибка:\n{exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=config.APP_TITLE)
    parser.add_argument("--reset-demo", action="store_true",
                        help="сделать резервную копию базы и восстановить демонстрационные данные")
    args = parser.parse_args()
    config.ensure_dirs()
    try:
        init_db()
        if args.reset_demo:
            reset_demo()
            print("Демонстрационные данные восстановлены")
        seed_if_empty()
    except Exception as exc:
        messagebox.showerror(config.APP_TITLE, f"База данных недоступна:\n{exc}")
        return 1
    ctk.set_default_color_theme("blue")
    sys.excepthook = report_crash
    # после «Выхода» снова показывается окно входа
    while True:
        login = LoginWindow()
        login.report_callback_exception = report_crash
        login.mainloop()
        if login.current_user is None:
            return 0
        window = MainWindow(login.current_user)
        window.report_callback_exception = report_crash
        window.mainloop()
        if not window.logout_requested:
            return 0


if __name__ == "__main__":
    sys.exit(main())
