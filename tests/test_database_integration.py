import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_manager import DataManager


class TestDatabaseIntegration(unittest.TestCase):
    """Test database storage and deduplication functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(__file__).resolve().parent.parent / "test_data"
        self.test_dir.mkdir(exist_ok=True)
        
        # Get the sample CSV from the repo if it exists
        self.sample_csv = Path(__file__).resolve().parent.parent / "source.csv"
        if not self.sample_csv.exists():
            self.skipTest("source.csv not found - skipping database integration test")
        
        # Get paths
        self.parse_script = Path(__file__).resolve().parent.parent / "parse-sheet.py"
        self.venv_python = Path(__file__).resolve().parent.parent / ".venv" / "bin" / "python"

    def run_parser(self, input_path, output_path, guild_id, db_path):
        """Helper to run the parser script via subprocess."""
        result = subprocess.run(
            [
                str(self.venv_python),
                str(self.parse_script),
                str(input_path),
                "-o", str(output_path),
                "-g", str(guild_id),
                "-db", str(db_path)
            ],
            cwd=self.parse_script.parent,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Parser failed: {result.stderr}")

    def test_datamanager_handles_signup_and_group_storage(self):
        """Test that DataManager can initialize schema and persist signups/groups."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "data-manager.db"
            manager = DataManager(db_path)
            manager.init_database()

            user = SimpleNamespace(
                name="TestUser",
                words_wr=3,
                words_r=2,
                genre_wr=["Epic Fantasy"],
                genre_r=["Science Fiction"],
                cw_wr=["Profanity"],
                cw_veto=["Sexual Content"],
                size_pref=["Small Group (3)"],
                match_pref="",
                match_veto="",
                prev_month="new_group",
                prev_group="",
            )
            group = SimpleNamespace(name="TestGroup", members=[user])

            manager.save_signups_to_db(1234567890, 42, [user], [])
            manager.save_groups_to_db(1234567890, 42, [group])

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM signups")
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute("SELECT COUNT(*) FROM groups")
            self.assertEqual(cursor.fetchone()[0], 1)
            conn.close()

    def test_database_creation_and_population(self):
        """Test that database is created and populated with signups and groups."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "test.db"
            output_path = tmp_path / "output.txt"
            guild_id = 123456789
            
            # Run parser with database parameters
            self.run_parser(
                input_path=str(self.sample_csv),
                output_path=str(output_path),
                guild_id=guild_id,
                db_path=str(db_path)
            )
            
            # Verify database was created
            self.assertTrue(db_path.exists(), "Database file was not created")
            
            # Verify tables were created and populated
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check signups table
            cursor.execute("SELECT COUNT(*) FROM signups")
            signup_count = cursor.fetchone()[0]
            self.assertGreater(signup_count, 0, "No signups were saved to database")
            
            # Check groups table
            cursor.execute("SELECT COUNT(*) FROM groups")
            group_count = cursor.fetchone()[0]
            self.assertGreater(group_count, 0, "No groups were saved to database")
            
            # Verify data structure
            cursor.execute("SELECT * FROM signups LIMIT 1")
            signup_row = cursor.fetchone()
            self.assertIsNotNone(signup_row, "Signup row is empty")
            
            # Verify key fields are populated
            cursor.execute("SELECT name, words_writing, genres_writing FROM signups LIMIT 1")
            name, words, genres = cursor.fetchone()
            self.assertIsNotNone(name, "Name field is empty")
            self.assertIsNotNone(words, "Words writing field is empty")
            self.assertIsNotNone(genres, "Genres writing field is empty")
            
            conn.close()

    def test_deduplication_on_rerun(self):
        """Test that running the parser multiple times doesn't create duplicate entries."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "test.db"
            output_path1 = tmp_path / "output1.txt"
            output_path2 = tmp_path / "output2.txt"
            guild_id = 123456789
            
            # First run
            self.run_parser(
                input_path=str(self.sample_csv),
                output_path=str(output_path1),
                guild_id=guild_id,
                db_path=str(db_path)
            )
            
            # Check first run signup count
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM signups")
            first_count = cursor.fetchone()[0]
            conn.close()
            
            # Second run (same CSV)
            self.run_parser(
                input_path=str(self.sample_csv),
                output_path=str(output_path2),
                guild_id=guild_id,
                db_path=str(db_path)
            )
            
            # Check second run signup count
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM signups")
            second_count = cursor.fetchone()[0]
            conn.close()
            
            # Should have same count due to deduplication
            self.assertEqual(
                first_count, second_count,
                f"Deduplication failed: first run had {first_count} signups, "
                f"second run had {second_count} signups"
            )


if __name__ == '__main__':
    unittest.main()
