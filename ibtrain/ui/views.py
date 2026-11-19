"""Соответствие пунктов меню классам разделов."""
from .courses_view import CoursesView
from .dashboard_view import DashboardView
from .export_view import ExportView
from .help_view import HelpView
from .logs_view import LogsView
from .profile_view import ProfileView
from .questions_view import QuestionsView
from .results_view import ResultsView
from .settings_view import SettingsView
from .tests_view import TestsView
from .users_view import UsersView

VIEWS = {
    "dashboard": DashboardView,
    "tests": TestsView,
    "results": ResultsView,
    "courses": CoursesView,
    "questions": QuestionsView,
    "users": UsersView,
    "export": ExportView,
    "logs": LogsView,
    "settings": SettingsView,
    "profile": ProfileView,
    "help": HelpView,
}
