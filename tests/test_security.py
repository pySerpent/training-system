"""Хеширование паролей и требования к сложности."""
import unittest

from ibtrain.security import hash_password, password_problems, verify_password


class SecurityTest(unittest.TestCase):

    def test_hash_and_verify(self):
        stored = hash_password("Secret#123")
        self.assertNotIn("Secret#123", stored)
        self.assertTrue(verify_password("Secret#123", stored))
        self.assertFalse(verify_password("secret#123", stored))

    def test_salt_differs(self):
        self.assertNotEqual(hash_password("Same#1234"), hash_password("Same#1234"))

    def test_broken_hash_is_rejected(self):
        self.assertFalse(verify_password("x", "не хеш"))

    def test_password_rules(self):
        self.assertEqual(password_problems("Good#Pass1"), [])
        self.assertTrue(password_problems("short1#"))
        self.assertTrue(password_problems("NoDigits#"))
        self.assertTrue(password_problems("NoSpecial1"))


if __name__ == "__main__":
    unittest.main()
