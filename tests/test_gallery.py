"""Gallery rebuilds must preserve verification records in a public checkout."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GalleryChecks(unittest.TestCase):
    def test_two_rebuilds_without_private_benchmark_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'scripts').mkdir()
            shutil.copy2(ROOT/'scripts/build_gallery.py', root/'scripts/build_gallery.py')
            shutil.copytree(ROOT/'examples', root/'examples')
            expected = (root/'examples/preview-manifest.json').read_bytes()
            for _ in range(2):
                result = subprocess.run([sys.executable, str(root/'scripts/build_gallery.py')],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((root/'examples/preview-manifest.json').read_bytes(), expected)


if __name__ == '__main__':
    unittest.main()
