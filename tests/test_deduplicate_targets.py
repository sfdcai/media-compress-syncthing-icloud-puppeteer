import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import deduplicate


class DeduplicationTargetsTests(unittest.TestCase):
    def test_defaults_include_uploaded_directories(self):
        with mock.patch.dict(
            os.environ,
            {
                "ORIGINALS_DIR": "/data/originals",
                "UPLOADED_ICLOUD_DIR": "/data/uploaded/icloud",
                "UPLOADED_PIXEL_DIR": "/data/uploaded/pixel",
            },
            clear=True,
        ):
            targets = deduplicate.get_deduplication_targets()

        self.assertEqual(
            targets,
            [
                ("originals", "/data/originals"),
                ("uploaded_icloud", "/data/uploaded/icloud"),
                ("uploaded_pixel", "/data/uploaded/pixel"),
            ],
        )

    def test_custom_directories_appended(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            extra_a = Path(temp_dir) / "dropbox"
            extra_b = Path(temp_dir) / "camera_uploads"
            extra_a.mkdir()
            extra_b.mkdir()

            with mock.patch.dict(
                os.environ,
                {
                    "ORIGINALS_DIR": "/data/originals",
                    "DEDUPLICATION_DIRECTORIES": f"{extra_a}\n{extra_b}",
                },
                clear=True,
            ):
                targets = deduplicate.get_deduplication_targets()

        self.assertEqual(
            targets,
            [
                ("originals", "/data/originals"),
                (extra_a.name, str(extra_a)),
                (extra_b.name, str(extra_b)),
            ],
        )

    def test_missing_directory_is_skipped_gracefully(self):
        missing_dir = os.path.join(tempfile.gettempdir(), "dedupe_missing_test")
        if os.path.exists(missing_dir):
            shutil.rmtree(missing_dir)

        self.assertTrue(deduplicate.deduplicate_directory(missing_dir))


if __name__ == "__main__":
    unittest.main()
