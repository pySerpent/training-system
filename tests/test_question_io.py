"""Импорт вопросов из Excel."""
import os
import tempfile
import unittest

from openpyxl import load_workbook

from ibtrain.services import courses, question_io


class QuestionImportTest(unittest.TestCase):

    def test_template_imports_one_question(self):
        module_id = courses.list_modules(courses.list_courses()[0]["id"])[0]["id"]
        before = len(courses.list_questions(module_id))
        path = question_io.save_template(os.path.join(tempfile.mkdtemp(), "t.xlsx"))
        wb = load_workbook(path)
        wb.active.append(["Плохая строка", "иногда", 1, "a", "b"])
        wb.save(path)
        added, problems = question_io.import_questions(module_id, path, None)
        self.assertEqual(added, 1)
        self.assertEqual(len(problems), 1)
        self.assertIn("строка 3", problems[0])
        self.assertEqual(len(courses.list_questions(module_id)), before + 1)

    def test_parse_marks_correct(self):
        _t, _q, weight, answers = question_io.parse_row(
            ("Вопрос?", "несколько", "1,5", "*да", "нет", "*тоже да", None, None, None))
        self.assertEqual(weight, 1.5)
        self.assertEqual(answers, [("да", True), ("нет", False), ("тоже да", True)])


if __name__ == "__main__":
    unittest.main()
