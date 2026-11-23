"""Выбор вопросов, подсчёт баллов и выгрузка протоколов."""
import os
import tempfile
import unittest

from docx import Document
from openpyxl import load_workbook
from sqlalchemy import select

from ibtrain.database import session_scope
from ibtrain.models import Answer
from ibtrain.services import auth, reports, settings, testing


class TestingTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        settings.save({"max_attempts": 50})
        cls.user = auth.login("employee", "Empl#2026")
        cls.course_id = testing.available_courses(cls.user.id)[0]["id"]

    def _start(self):
        return testing.start_test(self.user.id, self.course_id)

    def test_questions_are_unique(self):
        session = self._start()
        ids = [q.id for q in session.questions]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertLessEqual(len(ids), settings.get_int("questions_per_test", 10))
        testing.finish_test(session, self.user.id)

    def test_all_correct_gives_100(self):
        session = self._start()
        with session_scope() as s:
            for q in session.questions:
                session.answers[q.id] = set(s.scalars(select(Answer.id).where(
                    Answer.question_id == q.id, Answer.is_correct.is_(True))))
        summary = testing.finish_test(session, self.user.id)
        self.assertEqual(summary["percent"], 100)
        self.assertTrue(summary["passed"])

    def test_empty_answers_give_zero(self):
        summary = testing.finish_test(self._start(), self.user.id, timeout=True)
        self.assertEqual(summary["score"], 0)
        self.assertFalse(summary["passed"])

    def test_reports(self):
        rows = testing.list_results()
        self.assertTrue(rows)
        folder = tempfile.mkdtemp()
        docx_path = reports.export_docx(rows, os.path.join(folder, "r.docx"), None, True)
        self.assertIn("Протокол", "\n".join(p.text for p in Document(docx_path).paragraphs))
        xlsx_path = reports.export_xlsx(rows, os.path.join(folder, "r.xlsx"), None)
        sheet = load_workbook(xlsx_path).active
        self.assertEqual(sheet.cell(3, 1).value, "Сотрудник")
        self.assertTrue(str(sheet.cell(sheet.max_row, 6).value).startswith("=ROUND"))


if __name__ == "__main__":
    unittest.main()
