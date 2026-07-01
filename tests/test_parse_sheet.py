import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ParseSheetCliTests(unittest.TestCase):
    def test_script_accepts_input_path_and_writes_output_file(self):
        repo_root = Path(__file__).resolve().parents[1]
        csv_path = repo_root / "source.csv"

        with tempfile.TemporaryDirectory(dir=repo_root) as tmp_dir:
            output_path = Path(tmp_dir) / "groups-test.txt"
            subprocess.run(
                [sys.executable, "parse-sheet.py", str(csv_path), "-o", str(output_path)],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertTrue(output_path.exists(), "parser should create the requested output file")
            content = output_path.read_text(encoding="utf-8")
            self.assertIn("GROUP", content)


if __name__ == "__main__":
    unittest.main()
