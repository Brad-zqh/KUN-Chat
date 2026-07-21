import hashlib
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from worker import web_server


class PublicQuotaTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "usage.sqlite3"
        self.patches = [
            patch.object(web_server, "USAGE_DB", self.db_path),
            patch.object(web_server, "FREE_CHAT_LIMIT", 5),
            patch.object(web_server, "IP_HOURLY_CHAT_LIMIT", 20),
            patch.object(web_server, "INITIAL_TTS_ALLOWANCE", 8),
            patch.object(web_server, "OWNER_TTS_ALLOWANCE", 64),
            patch.object(web_server, "UNLIMITED_TEST_MODE", False),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_sixth_chat_requires_payment(self):
        visitor = "a" * 48
        for expected_remaining in range(4, -1, -1):
            self.assertEqual(web_server._reserve_chat_turn(visitor, "203.0.113.8"), "free")
            self.assertEqual(
                web_server._quota_status(visitor)["free_remaining"], expected_remaining
            )

        with self.assertRaises(web_server.PaymentRequiredError):
            web_server._reserve_chat_turn(visitor, "203.0.113.8")
        self.assertFalse(web_server._quota_status(visitor)["can_chat"])

    def test_failed_chat_refunds_reserved_turn(self):
        visitor = "b" * 48
        reservation = web_server._reserve_chat_turn(visitor, "203.0.113.9")
        web_server._refund_chat_turn(visitor, reservation)
        quota = web_server._quota_status(visitor)
        self.assertEqual(quota["free_used"], 0)
        self.assertEqual(quota["free_remaining"], 5)

    def test_successful_chat_grants_limited_tts_allowance(self):
        visitor = "c" * 48
        web_server._reserve_chat_turn(visitor, "203.0.113.10")
        web_server._finish_chat_turn(visitor, "这是一条成功生成的回复。")
        web_server._reserve_tts_segment(visitor)

        conn = sqlite3.connect(self.db_path)
        try:
            remaining = conn.execute(
                "SELECT tts_allowance FROM visitors WHERE visitor_id = ?", (visitor,)
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertGreaterEqual(remaining, 2)

    def test_first_visitor_can_play_initial_reply_but_not_unlimited_tts(self):
        visitor = "d" * 48
        for _ in range(8):
            web_server._reserve_tts_segment(visitor)
        with self.assertRaises(web_server.PaymentRequiredError):
            web_server._reserve_tts_segment(visitor)

    def test_owner_invite_grants_50_credits_once(self):
        token = "phone-owner-token-1234567890abcdef"
        conn = web_server._usage_connection()
        try:
            conn.execute(
                "INSERT INTO owner_invites(token_hash, credits, created_at) VALUES (?, ?, ?)",
                (hashlib.sha256(token.encode()).hexdigest(), 50, int(time.time())),
            )
        finally:
            conn.close()

        quota = web_server._claim_owner_invite("e" * 48, token)
        self.assertEqual(quota["available_total"], 50)
        self.assertEqual(quota["credits"], 45)
        conn = sqlite3.connect(self.db_path)
        try:
            allowance = conn.execute(
                "SELECT tts_allowance FROM visitors WHERE visitor_id = ?", ("e" * 48,)
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(allowance, 64)
        with self.assertRaises(ValueError):
            web_server._claim_owner_invite("f" * 48, token)

    def test_unlimited_mode_bypasses_chat_and_tts_limits(self):
        visitor = "1" * 48
        with patch.object(web_server, "UNLIMITED_TEST_MODE", True):
            for _ in range(30):
                self.assertEqual(
                    web_server._reserve_chat_turn(visitor, "203.0.113.20"), "unlimited"
                )
                web_server._reserve_tts_segment(visitor)
            quota = web_server._quota_status(visitor)
        self.assertTrue(quota["unlimited"])
        self.assertTrue(quota["can_chat"])


if __name__ == "__main__":
    unittest.main()
