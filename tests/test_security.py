"""Regression tests for the security fixes: argv injection, zip bombs, encode-truncation."""

from __future__ import annotations

import io
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "clean-ai-marks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import container_meta  # noqa: E402
import image_meta  # noqa: E402
from common import exit_code, tool_arg, write_text_file  # noqa: E402
from container_meta import ZipTooLarge, clean_docx, clean_odt, inspect_docx, inspect_odt  # noqa: E402


def test_tool_arg_never_looks_like_an_option(tmp_path: Path):
    src = tmp_path / "-overwrite_original"
    src.write_bytes(b"x")
    assert not tool_arg(src).startswith("-")


def test_optional_tools_get_absolute_paths(tmp_path: Path, monkeypatch):
    """A file named like a flag must reach exiftool/c2patool as a path, not an option."""
    src = tmp_path / "-ver.png"
    src.write_bytes(b"x")
    seen: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(image_meta, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(image_meta.subprocess, "run", fake_run)
    image_meta.run_optional_tools(src)

    assert seen
    for cmd in seen:
        assert cmd[-1] == str(src.resolve())
        assert not cmd[-1].startswith("-")


def test_clean_image_exiftool_pass_gets_absolute_path(tmp_path: Path, monkeypatch):
    from test_clean_image import _minimal_png_with_text

    src = tmp_path / "in.png"
    src.write_bytes(_minimal_png_with_text())
    dest = tmp_path / "-out.png"
    seen: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(image_meta, "which", lambda name: "/usr/bin/exiftool")
    monkeypatch.setattr(image_meta.subprocess, "run", fake_run)
    image_meta.clean_image(src, dest)

    assert any(cmd[0] == "/usr/bin/exiftool" and cmd[-1] == str(dest.resolve()) for cmd in seen)


def _zip_bomb(names_with_body: dict[str, bytes], filler: int) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, body in names_with_body.items():
            zf.writestr(name, body)
        zf.writestr("big.bin", b"\0" * filler)
    return buf.getvalue()


@pytest.fixture
def small_budget(monkeypatch):
    monkeypatch.setattr(container_meta, "MAX_ZIP_MEMBER_BYTES", 4096)
    monkeypatch.setattr(container_meta, "MAX_ZIP_TOTAL_BYTES", 8192)


def test_docx_zip_bomb_is_refused(small_budget):
    data = _zip_bomb({"word/document.xml": b"<w:document/>"}, filler=1024 * 1024)
    _c2, has_ai, findings, details = inspect_docx(data)
    assert has_ai
    assert details.get("oversized")
    assert any("oversized" in f for f in findings)
    with pytest.raises(ZipTooLarge):
        clean_docx(data)


def test_odt_zip_bomb_is_refused(small_budget):
    data = _zip_bomb(
        {"mimetype": b"application/vnd.oasis.opendocument.text", "content.xml": b"<x/>"},
        filler=1024 * 1024,
    )
    _c2, has_ai, findings, details = inspect_odt(data)
    assert has_ai
    assert details.get("oversized")
    with pytest.raises(ZipTooLarge):
        clean_odt(data)


def test_zip_budget_caps_total_across_members(small_budget):
    """Members each under the per-member cap still cannot blow the total budget."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(5):
            zf.writestr(f"part{i}.bin", b"\0" * 3000)
    budget = container_meta._ZipBudget()
    with pytest.raises(ZipTooLarge):
        with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as zf:
            for info in zf.infolist():
                budget.read(zf, info)


def test_docx_under_budget_still_cleans():
    from test_container_meta import _make_docx_with_app

    cleaned, actions = clean_docx(_make_docx_with_app())
    assert any("drop" in a for a in actions)


LATIN1_TEXT = b"caf\xe9 na\xefve\n"


def test_write_text_file_preserves_undecodable_bytes(tmp_path: Path):
    dest = tmp_path / "out.txt"
    write_text_file(dest, LATIN1_TEXT.decode("utf-8", errors="surrogateescape"))
    assert dest.read_bytes() == LATIN1_TEXT


def _run_clean_file(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "clean_file.py"), *args],
        capture_output=True,
        text=True,
    )


def test_clean_file_non_utf8_input_does_not_truncate(tmp_path: Path):
    src = tmp_path / "latin1.txt"
    src.write_bytes(LATIN1_TEXT)
    dest = tmp_path / "out.txt"
    r = _run_clean_file(str(src), "-o", str(dest))
    assert r.returncode == 0, r.stderr
    assert dest.read_bytes() == LATIN1_TEXT


def test_clean_file_in_place_non_utf8_keeps_content(tmp_path: Path):
    src = tmp_path / "latin1.txt"
    src.write_bytes(LATIN1_TEXT)
    r = _run_clean_file(str(src), "--in-place")
    assert r.returncode == 0, r.stderr
    assert src.read_bytes() == LATIN1_TEXT


def test_clean_container_html_non_utf8_does_not_truncate(tmp_path: Path):
    src = tmp_path / "page.html"
    src.write_bytes(b'<html><meta name="generator" content="ChatGPT"><p>caf\xe9</p></html>')
    dest = tmp_path / "page.cleaned.html"
    container_meta.clean_container(src, dest)
    body = dest.read_bytes()
    assert b"ChatGPT" not in body
    assert b"caf\xe9" in body


def test_pdf_clean_without_qpdf_is_degraded(tmp_path: Path, monkeypatch):
    """exiftool alone leaves the old PDF revision, so the result must not read as clean."""
    src = tmp_path / "t.pdf"
    src.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
    dest = tmp_path / "t.cleaned.pdf"

    def fake_which(name):
        return "/usr/bin/exiftool" if name == "exiftool" else None

    monkeypatch.setattr(container_meta, "which", fake_which)
    monkeypatch.setattr(
        container_meta.subprocess,
        "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),
    )
    actions, meta = container_meta.clean_pdf(src, dest)
    assert meta["degraded"] is True
    assert any("qpdf" in a for a in actions)


def test_pdf_clean_with_qpdf_is_not_degraded(tmp_path: Path, monkeypatch):
    src = tmp_path / "t.pdf"
    src.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
    dest = tmp_path / "t.cleaned.pdf"
    seen: list[list[str]] = []

    def fake_run(cmd, **kw):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(container_meta, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(container_meta.subprocess, "run", fake_run)
    actions, meta = container_meta.clean_pdf(src, dest)
    assert meta["degraded"] is False
    assert any(cmd[0].endswith("qpdf") and cmd[-1] == str(dest.resolve()) for cmd in seen)
    assert any("linearize" in a for a in actions)


def test_degraded_result_gets_its_own_exit_code():
    from common import EXIT_DEGRADED, EXIT_ERROR, EXIT_OK

    assert exit_code({"meta": {"degraded": True}}) == EXIT_DEGRADED
    assert exit_code({"meta": {"degraded": True}, "still_has_ai_metadata": True}) == EXIT_DEGRADED
    assert exit_code({"still_has_ai_metadata": True}) == EXIT_ERROR
    assert exit_code({"still_has_c2pa": True}) == EXIT_ERROR
    assert exit_code({"meta": {}}) == EXIT_OK


def test_residual_signals_fail_with_json_output(tmp_path: Path):
    """--json must not mask a residual-signal failure."""
    src = tmp_path / "x.svg"
    src.write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"><title>c2pa</title></svg>')
    r = _run_clean_file(str(src), "-o", str(tmp_path / "out.svg"), "--json")
    assert r.returncode == 1, r.stdout


def test_in_place_refuses_symlink(tmp_path: Path):
    real = tmp_path / "real.txt"
    real.write_text("hello​\n", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(real)

    r = _run_clean_file(str(link), "--in-place")
    assert r.returncode == 2
    assert "symlink" in r.stderr
    assert real.read_text(encoding="utf-8") == "hello​\n"
    assert not (tmp_path / "link.txt.bak").exists()


def test_rewrite_rejects_non_http_base_url():
    import rewrite_text

    with pytest.raises(SystemExit):
        rewrite_text.rewrite(
            "hi",
            backend="ollama",
            model="m",
            base_url="file:///etc/passwd",
            api_key=None,
            strength="paraphrase",
            lang="French",
            original_lang="English",
            timeout=1.0,
            layer_a_after=False,
        )
