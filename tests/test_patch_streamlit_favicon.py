"""The build-time Streamlit favicon patch: patches, is idempotent, and fails loudly."""

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "patch_streamlit_favicon.py"
_spec = importlib.util.spec_from_file_location("patch_streamlit_favicon", _SCRIPT)
patcher = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(patcher)


@pytest.fixture
def streamlit_static(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text(
        f"<head>{patcher.ORIGINAL_LINK}<title>Streamlit</title></head>", encoding="utf-8"
    )
    (static / "favicon.png").write_bytes(b"crown")
    return static


@pytest.fixture
def icon(tmp_path):
    path = tmp_path / "icon.png"
    path.write_bytes(b"icon")
    return path


def test_patch_rewrites_link_and_replaces_bundled_favicon(streamlit_static, icon):
    assert patcher.patch(streamlit_static, icon) == "patched"
    html = (streamlit_static / "index.html").read_text(encoding="utf-8")
    assert patcher.PATCHED_LINK in html
    assert patcher.ORIGINAL_LINK not in html
    assert (streamlit_static / "favicon.png").read_bytes() == b"icon"


def test_patch_is_idempotent(streamlit_static, icon):
    patcher.patch(streamlit_static, icon)
    assert patcher.patch(streamlit_static, icon) == "already patched"
    html = (streamlit_static / "index.html").read_text(encoding="utf-8")
    assert html.count(patcher.PATCHED_LINK) == 1


def test_patch_fails_when_link_is_unrecognised(streamlit_static, icon):
    (streamlit_static / "index.html").write_text("<head></head>", encoding="utf-8")
    with pytest.raises(ValueError):
        patcher.patch(streamlit_static, icon)
    assert (streamlit_static / "favicon.png").read_bytes() == b"crown"


def test_bundled_icon_is_a_png():
    assert patcher.ICON.read_bytes().startswith(b"\x89PNG")
