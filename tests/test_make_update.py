import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
BUILDER = REPO / "make_update.py"
UPDATER = "PDF Splitter Updater.exe"


class UpdatePackageTests(unittest.TestCase):
    def test_running_updater_is_only_in_full_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = root / "current"
            previous = root / "previous"
            output = root / "output"
            current.mkdir()
            previous.mkdir()

            (current / "PDF Splitter.exe").write_bytes(b"new-app")
            (previous / "PDF Splitter.exe").write_bytes(b"old-app")
            (current / UPDATER).write_bytes(b"new-updater")
            (previous / UPDATER).write_bytes(b"old-updater")
            (current / "library.dat").write_bytes(b"new-library")
            (previous / "library.dat").write_bytes(b"old-library")

            subprocess.run(
                [sys.executable, str(BUILDER), str(current), str(previous), str(output)],
                check=True,
                capture_output=True,
                text=True,
            )

            with zipfile.ZipFile(output / "PDF-Splitter-Full.zip") as full:
                self.assertIn(UPDATER, full.namelist())

            with zipfile.ZipFile(output / "PDF-Splitter-Update.zip") as patch:
                names = patch.namelist()
                manifest = json.loads(patch.read("update_manifest.json"))
                self.assertNotIn(UPDATER, names)
                self.assertNotIn(UPDATER, manifest["files"])
                self.assertNotIn(UPDATER, manifest["deleted"])
                self.assertIn("PDF Splitter.exe", manifest["files"])
                self.assertIn("library.dat", manifest["files"])


if __name__ == "__main__":
    unittest.main()
