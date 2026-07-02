import json
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_manager import TestDataManager


class TestTestDataManager(unittest.TestCase):
    def test_signup_dedupe_on_repeat_save(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_path = Path(tmp_dir) / "signups-test.txt"
            manager = TestDataManager(storage_path)
            manager.init_database()

            users = [
                {
                    "timestamp": 1700000000,
                    "name": "alice",
                    "words_wr": 2,
                    "words_r": 2,
                    "genre_wr": ["Epic Fantasy"],
                    "genre_r": ["Epic Fantasy"],
                    "cw_wr": [],
                    "cw_veto": [],
                    "size_pref": [3],
                    "match_pref": "",
                    "match_veto": "",
                    "prev_month": "no_group",
                    "prev_group": "",
                }
            ]

            manager.save_signups_to_db(None, 42, users, [])
            manager.save_signups_to_db(None, 42, users, [])

            with storage_path.open("r", encoding="utf-8") as handle:
                state = json.load(handle)

            self.assertEqual(len(state["signups"]), 1)


if __name__ == "__main__":
    unittest.main()
