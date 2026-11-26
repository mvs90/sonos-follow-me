"""Verify the exact archive layout consumed by HACS and Marketplace."""

import json
from zipfile import ZipFile

import pytest

from dev.build_release import INTEGRATION, ROOT, build_release


def test_installable_release_contains_complete_integration(tmp_path):
    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert hacs["zip_release"] is True
    version = json.loads((INTEGRATION / "manifest.json").read_text())["version"]
    archive_path = build_release(tmp_path / hacs["filename"], f"v{version}")
    with ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        assert {"manifest.json", "__init__.py", "frontend/sonos-follow-me-card.js"} <= names
        assert {"brand/icon.png", "brand/logo.png", "frontend/follow-me-logo.png"} <= names
        for language in (INTEGRATION / "translations").glob("*.json"):
            assert f"translations/{language.name}" in names
            assert f"frontend/translations/{language.name}" in names
        assert all(not name.startswith(("custom_components/", "dev/", ".")) for name in names)
        assert all("__pycache__" not in name and not name.endswith(".pyc") for name in names)
        expected = {
            p.relative_to(INTEGRATION).as_posix()
            for p in INTEGRATION.rglob("*")
            if p.is_file() and p.suffix in {".py", ".js", ".json", ".png"}
        }
        assert names == expected
        for name in names:
            assert archive.read(name) == (INTEGRATION / name).read_bytes()
        assert archive.testzip() is None
    assert build_release(tmp_path / "second.zip").read_bytes() == archive_path.read_bytes()


def test_release_rejects_wrong_version(tmp_path):
    with pytest.raises(ValueError, match="tag must match"):
        build_release(tmp_path / "wrong.zip", "v0.0.0")
