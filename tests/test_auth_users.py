"""Вход в систему, права ролей и управление пользователями."""
import unittest

from ibtrain import config
from ibtrain.services import auth, users


class AuthTest(unittest.TestCase):

    def test_login_roles(self):
        for login, pwd, role in [("admin", "Admin#2026", config.ROLE_ADMIN),
                                 ("teacher", "Teach#2026", config.ROLE_TEACHER),
                                 ("employee", "Empl#2026", config.ROLE_EMPLOYEE)]:
            self.assertEqual(auth.login(login, pwd).role, role)

    def test_wrong_password(self):
        with self.assertRaises(auth.AuthError):
            auth.login("teacher", "wrong")

    def test_permissions(self):
        employee = auth.login("employee", "Empl#2026")
        self.assertFalse(auth.can(employee, "users"))
        self.assertFalse(auth.can(employee, "comment"))
        self.assertTrue(auth.can(employee, "tests"))

    def test_autoblock_after_fails(self):
        uid = users.save_user({"full_name": "Тестов Тест Тестович", "login": "blocktest",
                               "position": "", "email": "", "department": "",
                               "role_code": config.ROLE_EMPLOYEE, "password": "Block#2026"},
                              None, None)
        for _ in range(config.MAX_LOGIN_FAILS):
            with self.assertRaises(auth.AuthError):
                auth.login("blocktest", "bad")
        with self.assertRaisesRegex(auth.AuthError, "заблокирована"):
            auth.login("blocktest", "Block#2026")
        users.set_blocked(uid, False, None)
        self.assertEqual(auth.login("blocktest", "Block#2026").id, uid)


class UsersTest(unittest.TestCase):

    def test_validation(self):
        with self.assertRaises(users.ValidationError):
            users.save_user({"full_name": "", "login": "1bad", "position": "",
                             "email": "not-mail", "department": "",
                             "role_code": config.ROLE_EMPLOYEE, "password": "123"},
                            None, None)

    def test_duplicate_login(self):
        with self.assertRaises(users.ValidationError):
            users.save_user({"full_name": "Другой Админ", "login": "admin", "position": "",
                             "email": "", "department": "",
                             "role_code": config.ROLE_ADMIN, "password": "Admin#2027"},
                            None, None)


if __name__ == "__main__":
    unittest.main()
