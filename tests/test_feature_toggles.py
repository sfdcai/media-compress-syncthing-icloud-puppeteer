import pytest

from scripts import utils


@pytest.fixture(autouse=True)
def clear_toggle_env(monkeypatch):
    toggles = [
        "ENABLE_ICLOUD_DOWNLOAD",
        "ENABLE_FOLDER_DOWNLOAD",
        "ENABLE_ICLOUD_UPLOAD",
        "ENABLE_PIXEL_UPLOAD",
        "ENABLE_COMPRESSION",
        "ENABLE_IMAGE_COMPRESSION",
        "ENABLE_VIDEO_COMPRESSION",
        "ENABLE_DEDUPLICATION",
        "ENABLE_FILE_PREPARATION",
        "ENABLE_SORTING",
        "ENABLE_VERIFICATION",
        "ENABLE_GOOGLE_PHOTOS_SYNC_CHECK",
        "ENABLE_FILENAME_CONFLICT_RESOLUTION",
    ]
    for toggle in toggles:
        monkeypatch.delenv(toggle, raising=False)


def test_get_feature_toggle_respects_default(monkeypatch):
    monkeypatch.delenv("ENABLE_ICLOUD_UPLOAD", raising=False)
    assert utils.get_feature_toggle("ENABLE_ICLOUD_UPLOAD", default=False) is False

    monkeypatch.setenv("ENABLE_ICLOUD_UPLOAD", "true")
    assert utils.get_feature_toggle("ENABLE_ICLOUD_UPLOAD", default=False) is True

    monkeypatch.setenv("ENABLE_ICLOUD_UPLOAD", "false")
    assert utils.get_feature_toggle("ENABLE_ICLOUD_UPLOAD") is False


def test_validate_config_detects_invalid_toggle(monkeypatch):
    monkeypatch.setenv("ENABLE_ICLOUD_DOWNLOAD", "invalid")
    assert utils.validate_config() is False


def test_validate_config_accepts_valid_toggles(monkeypatch):
    monkeypatch.setenv("ENABLE_ICLOUD_DOWNLOAD", "true")
    monkeypatch.setenv("ENABLE_FOLDER_DOWNLOAD", "false")
    monkeypatch.setenv("ENABLE_ICLOUD_UPLOAD", "true")
    monkeypatch.setenv("ENABLE_PIXEL_UPLOAD", "true")
    monkeypatch.setenv("ENABLE_COMPRESSION", "true")
    monkeypatch.setenv("ENABLE_IMAGE_COMPRESSION", "true")
    monkeypatch.setenv("ENABLE_VIDEO_COMPRESSION", "true")
    monkeypatch.setenv("ENABLE_DEDUPLICATION", "true")
    monkeypatch.setenv("ENABLE_FILE_PREPARATION", "true")
    monkeypatch.setenv("ENABLE_SORTING", "true")
    monkeypatch.setenv("ENABLE_VERIFICATION", "true")
    monkeypatch.setenv("ENABLE_GOOGLE_PHOTOS_SYNC_CHECK", "false")
    monkeypatch.setenv("ENABLE_FILENAME_CONFLICT_RESOLUTION", "true")

    assert utils.validate_config() is True
