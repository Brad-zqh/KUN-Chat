import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from worker import web_server


class AuthTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "usage.sqlite3"
        self.patch = patch.object(web_server, "USAGE_DB", self.db_path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp_dir.cleanup()

    def test_password_and_session_round_trip(self):
        username, password = web_server._validate_credentials(
            "test_user", "strong-pass-123"
        )
        salt = bytes.fromhex("00" * 16)
        conn = web_server._usage_connection()
        try:
            cursor = conn.execute(
                """INSERT INTO users(
                       username,password_hash,password_salt,created_at,updated_at
                   ) VALUES(?,?,?,?,?)""",
                (
                    username,
                    web_server._password_digest(password, salt),
                    salt.hex(),
                    1,
                    1,
                ),
            )
            token = web_server._create_session(conn, int(cursor.lastrowid))
        finally:
            conn.close()
        user = web_server._user_for_session(token)
        self.assertEqual(user["username"], username)
        self.assertEqual(user["is_admin"], 0)

    def test_simple_chinese_credentials_are_allowed(self):
        self.assertEqual(
            web_server._validate_credentials("小坤", "123456"),
            ("小坤", "123456"),
        )

    def test_credentials_still_have_minimum_safety_limits(self):
        with self.assertRaisesRegex(ValueError, "2-32"):
            web_server._validate_credentials("坤", "123456")
        with self.assertRaisesRegex(ValueError, "6-128"):
            web_server._validate_credentials("坤坤", "12345")

    def test_account_quota_is_stable_and_admin_is_unlimited(self):
        visitor = web_server._account_visitor_id(42)
        self.assertEqual(visitor, web_server._account_visitor_id(42))
        self.assertEqual(len(visitor), 48)
        quota = web_server._quota_status(visitor, is_admin=True)
        self.assertTrue(quota["unlimited"])
        self.assertEqual(
            web_server._reserve_chat_turn(
                visitor, "203.0.113.42", is_admin=True
            ),
            "unlimited",
        )
        web_server._reserve_tts_segment(visitor, is_admin=True)

    def test_manual_payment_requires_review_before_credits_are_added(self):
        conn = web_server._usage_connection()
        try:
            cursor = conn.execute(
                """INSERT INTO users(
                       username,password_hash,password_salt,created_at,updated_at
                   ) VALUES(?,?,?,?,?)""",
                ("payer", "hash", "salt", 1, 1),
            )
            user_id = int(cursor.lastrowid)
        finally:
            conn.close()

        with patch.object(web_server, "MANUAL_PAYMENT_ENABLED", True):
            order = web_server._create_manual_payment_order(
                user_id,
                "alipay",
                "starter",
                "12345678",
            )
            self.assertEqual(order["status"], "pending")
            before = web_server._quota_status(web_server._account_visitor_id(user_id))
            self.assertEqual(before["credits"], 0)

            approved = web_server._approve_manual_payment_order(
                order["order_id"], approve=True
            )
            self.assertEqual(approved["status"], "paid")
            after = web_server._quota_status(web_server._account_visitor_id(user_id))
            self.assertEqual(after["credits"], 20)

    def test_disabled_persona_is_not_published(self):
        self.assertNotIn("tulei", web_server.SUPPORTED_PERSONAS)
        self.assertNotIn("linqingxia", web_server.SUPPORTED_PERSONAS)


if __name__ == "__main__":
    unittest.main()
