"""Tests for the optional-extras venv and the code paths it unlocks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "clean-ai-marks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import container_meta  # noqa: E402
import image_meta  # noqa: E402

REQUIREMENTS = ROOT / "skills" / "clean-ai-marks" / "requirements.txt"


def test_requirements_file_ships_with_the_skill():
    """It must live inside the skill dir, which is what gets symlinked on install."""
    assert REQUIREMENTS.is_file()
    body = REQUIREMENTS.read_text()
    assert "pikepdf" in body
    assert "c2pa-python" in body


def test_activate_skill_venv_appends_site_packages(tmp_path: Path, monkeypatch):
    v = sys.version_info
    site = tmp_path / "lib" / f"python{v.major}.{v.minor}" / "site-packages"
    site.mkdir(parents=True)
    monkeypatch.setattr(common, "SKILL_VENV", tmp_path)
    monkeypatch.setattr(sys, "path", list(sys.path))

    common.activate_skill_venv()

    assert str(site) in sys.path
    assert sys.path[-1] == str(site), "ambient environment must keep priority"


def test_activate_skill_venv_is_a_noop_without_venv(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(common, "SKILL_VENV", tmp_path / "absent")
    before = list(sys.path)
    monkeypatch.setattr(sys, "path", list(sys.path))

    common.activate_skill_venv()

    assert sys.path == before


def test_ensure_tools_reports_without_installing():
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "ensure_tools.py"), "--json"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert set(data["pip_modules"]) == {"pikepdf", "c2pa"}
    assert "exiftool" in data["system_tools"]
    for info in data["system_tools"].values():
        assert info["install"]


def test_pdf_falls_back_when_pikepdf_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setitem(sys.modules, "pikepdf", None)
    monkeypatch.setattr(container_meta, "which", lambda name: None)
    src = tmp_path / "t.pdf"
    src.write_bytes(b"%PDF-1.4\ntrailer<<>>\n%%EOF\n")
    dest = tmp_path / "out.pdf"

    actions, meta = container_meta.clean_pdf(src, dest)

    assert meta["mode"] == "copy"
    assert meta["degraded"] is True


def test_c2pa_probe_absent_without_the_binding(tmp_path: Path, monkeypatch):
    monkeypatch.setitem(sys.modules, "c2pa", None)
    src = tmp_path / "x.png"
    src.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert image_meta._c2pa_python_probe(src) is None


def test_pdf_clean_with_pikepdf_leaves_no_residue(tmp_path: Path):
    pikepdf = pytest.importorskip("pikepdf")
    src = tmp_path / "dirty.pdf"
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page()
    with pdf.open_metadata() as m:
        m["dc:creator"] = ["Claude"]
    pdf.docinfo["/Producer"] = "Anthropic Claude"
    pdf.save(src)
    assert b"Anthropic" in src.read_bytes()

    dest = tmp_path / "clean.pdf"
    actions, meta = container_meta.clean_pdf(src, dest)

    assert meta["mode"] == "pikepdf"
    assert meta["degraded"] is False
    assert any("rewrote PDF" in a for a in actions)
    raw = dest.read_bytes()
    assert b"Anthropic" not in raw
    assert b"Claude" not in raw


def test_pdf_clean_drops_c2pa_associated_file_and_keeps_others(tmp_path: Path):
    pikepdf = pytest.importorskip("pikepdf")
    src = tmp_path / "marked.pdf"
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page()
    c2pa = pikepdf.AttachedFileSpec(
        pdf,
        b"c2pa-secret-manifest",
        filename="c2pa.dat",
        mime_type="application/c2pa",
        relationship=pikepdf.Name.C2PA_Manifest,
    )
    other = pikepdf.AttachedFileSpec(
        pdf,
        b"ordinary-attachment",
        filename="notes.txt",
        mime_type="text/plain",
        relationship=pikepdf.Name.Data,
    )
    pdf.Root.AF = pikepdf.Array([c2pa.obj, other.obj])
    pdf.Root.Names = pikepdf.Dictionary()
    tree = pikepdf.NameTree.new(pdf)
    tree["c2pa.dat"] = c2pa.obj
    tree["notes.txt"] = other.obj
    pdf.Root.Names.EmbeddedFiles = tree.obj
    pdf.pages[0].obj.AF = pikepdf.Array([c2pa.obj])
    pdf.save(src)

    dest = tmp_path / "clean.pdf"
    actions, meta = container_meta.clean_pdf(src, dest)

    assert meta["degraded"] is False
    assert any("C2PA" in a for a in actions)
    out = pikepdf.open(dest)
    rels = [str(item.get("/AFRelationship")) for item in out.Root.AF]
    assert rels == ["/Data"]
    assert "/AF" not in out.pages[0].obj
    names = list(pikepdf.NameTree(out.Root.Names.EmbeddedFiles))
    assert names == ["notes.txt"]
    kept = pikepdf.NameTree(out.Root.Names.EmbeddedFiles)["notes.txt"]
    assert kept["/EF"]["/F"].read_bytes() == b"ordinary-attachment"
    for obj in out.objects:
        if isinstance(obj, pikepdf.Stream):
            assert b"c2pa-secret-manifest" not in obj.read_bytes()


def test_c2pa_probe_reports_no_manifest_for_plain_image(tmp_path: Path):
    pytest.importorskip("c2pa")
    from test_clean_image import _minimal_png_with_text

    src = tmp_path / "x.png"
    src.write_bytes(_minimal_png_with_text())

    probe = image_meta._c2pa_python_probe(src)

    assert probe is not None
    assert probe["available"] is True
    assert probe.get("has_manifest") is False
