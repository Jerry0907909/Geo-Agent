import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.api.chat_routes import compact_chat_history


class TestChatHistoryCompaction(unittest.TestCase):
    def test_keeps_latest_messages_with_total_budget(self):
        history = [
            {"role": "user", "content": "u1 " + "a" * 2000},
            {"role": "assistant", "content": "a1 " + "b" * 2000},
            {"role": "user", "content": "u2 short"},
            {"role": "assistant", "content": "a2 short"},
        ]

        compacted = compact_chat_history(
            history,
            max_messages=3,
            max_total_chars=60,
            max_item_chars=40,
        )

        self.assertEqual(len(compacted), 2)
        self.assertEqual(compacted[0]["content"], "u2 short")
        self.assertEqual(compacted[1]["content"], "a2 short")

    def test_truncates_single_large_message(self):
        history = [
            {"role": "assistant", "content": "x" * 300},
        ]

        compacted = compact_chat_history(
            history,
            max_messages=6,
            max_total_chars=80,
            max_item_chars=120,
        )

        self.assertEqual(len(compacted), 1)
        self.assertLessEqual(len(compacted[0]["content"]), 78)
        self.assertTrue(compacted[0]["content"].endswith("..."))


if __name__ == "__main__":
    unittest.main()
