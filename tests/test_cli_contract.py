"""Pins the CLI surface the README documents: exit codes and flags."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "ai-watermark-scrambler"
SCRIPTS = SKILL / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
README = SKILL / "README.md"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402

DOCUMENTED_FLAGS = {
    "inspect_text.py": ["--json", "--aggressive"],
    "clean_text.py": [
        "--output",
        "--nfkc",
        "--aggressive-homoglyphs",
        "--no-normalize-spaces",
        "--stats",
        "--in-place",
    ],
    "inspect_image.py": ["--json"],
    "clean_image.py": ["--output", "--in-place", "--keep-non-ai-metadata", "--json"],
    "inspect_file.py": ["--json", "--aggressive", "--as"],
    "clean_file.py": [
        "--output",
        "--in-place",
        "--json",
        "--nfkc",
        "--aggressive-homoglyphs",
        "--keep-non-ai-metadata",
        "--as",
    ],
    "rewrite_text.py": [
        "--output",
        "--backend",
        "--model",
        "--base-url",
        "--strength",
        "--no-layer-a-after",
    ],
    "ensure_tools.py": ["--install", "--json"],
}


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
    )


def test_exit_constants_match_the_documented_table():
    assert (common.EXIT_OK, common.EXIT_ERROR) == (0, 1)
    assert (common.EXIT_BAD_INPUT, common.EXIT_DEGRADED) == (2, 3)


@pytest.mark.parametrize("script", sorted(DOCUMENTED_FLAGS))
def test_documented_flags_exist(script: str):
    r = run(script, "--help")
    assert r.returncode == 0, r.stderr
    for flag in DOCUMENTED_FLAGS[script]:
        assert flag in r.stdout, f"{script} lost {flag}"


@pytest.mark.parametrize(
    "script",
    ["inspect_text.py", "inspect_file.py", "inspect_image.py", "clean_text.py", "clean_file.py", "clean_image.py"],
)
def test_missing_input_exits_bad_input(script: str):
    r = run(script, str(FIXTURES / "does_not_exist.txt"))
    assert r.returncode == common.EXIT_BAD_INPUT, r.stderr


@pytest.mark.parametrize(
    "script,fixture",
    [
        ("inspect_text.py", "sample_watermarked.txt"),
        ("inspect_file.py", "sample_watermarked.txt"),
        ("inspect_file.py", "sample_ai.md"),
        ("inspect_file.py", "sample_ai.html"),
        ("inspect_file.py", "sample_meta.svg"),
    ],
)
def test_inspect_exits_one_when_marks_found(script: str, fixture: str):
    r = run(script, str(FIXTURES / fixture))
    assert r.returncode == common.EXIT_ERROR, r.stdout


@pytest.mark.parametrize("script", ["inspect_text.py", "inspect_file.py"])
def test_inspect_exits_zero_on_clean_input(script: str, tmp_path: Path):
    src = tmp_path / "plain.txt"
    src.write_text("Nothing to see here.\n")

    r = run(script, str(src))

    assert r.returncode == common.EXIT_OK, r.stdout


def test_clean_file_nfkc_reaches_markdown(tmp_path: Path):
    src = tmp_path / "note.md"
    src.write_text("ﬁle\n", encoding="utf-8")
    dest = tmp_path / "note.cleaned.md"

    r = run("clean_file.py", str(src), "-o", str(dest), "--nfkc")

    assert r.returncode == common.EXIT_OK, r.stderr
    assert dest.read_text(encoding="utf-8") == "file\n"


def test_unreadable_or_unsupported_input_exits_bad_input(tmp_path: Path):
    broken = tmp_path / "broken.docx"
    broken.write_bytes(b"not a zip")
    text = tmp_path / "t.txt"
    text.write_text("hello\n", encoding="utf-8")
    weird = tmp_path / "a.weird"
    weird.write_bytes(b"xyz")
    bad_png = tmp_path / "bad.png"
    bad_png.write_bytes(b"not a png")

    cases = [
        ("clean_image.py", [str(text), "-o", str(tmp_path / "out.jpg")]),
        ("clean_file.py", [str(text), "--as", "image", "-o", str(tmp_path / "forced.jpg")]),
        ("inspect_file.py", [str(broken)]),
        ("inspect_file.py", [str(weird), "--as", "container"]),
        ("inspect_file.py", [str(bad_png)]),
        ("inspect_image.py", [str(text)]),
    ]
    for script, args in cases:
        result = run(script, *args)
        assert result.returncode == common.EXIT_BAD_INPUT, (script, result.returncode, result.stderr, result.stdout)


def test_clean_file_corrupt_inputs_exit_bad_input(tmp_path: Path):
    image = tmp_path / "bad.png"
    image.write_bytes(b"not a png")
    docx = tmp_path / "bad.docx"
    docx.write_bytes(b"PK\x03\x04not a zip")

    image_run = run("clean_file.py", str(image), "-o", str(tmp_path / "out.png"))
    docx_run = run("clean_file.py", str(docx), "-o", str(tmp_path / "out.docx"))

    assert image_run.returncode == common.EXIT_BAD_INPUT, image_run.stderr
    assert docx_run.returncode == common.EXIT_BAD_INPUT, docx_run.stderr


@pytest.mark.parametrize(
    "fixture", ["sample_watermarked.txt", "sample_ai.md", "sample_ai.html", "sample_meta.svg"]
)
def test_clean_then_inspect_round_trips_to_zero(fixture: str, tmp_path: Path):
    dest = tmp_path / f"clean{Path(fixture).suffix}"

    cleaned = run("clean_file.py", str(FIXTURES / fixture), "-o", str(dest))
    assert cleaned.returncode == common.EXIT_OK, cleaned.stderr

    assert run("inspect_file.py", str(dest)).returncode == common.EXIT_OK


def test_readme_documents_every_exit_code():
    body = README.read_text()
    table = body.split("## Exit codes", 1)[1].split("##", 1)[0]
    for code in (common.EXIT_OK, common.EXIT_ERROR, common.EXIT_BAD_INPUT, common.EXIT_DEGRADED):
        assert f"| {code} |" in table, f"exit {code} missing from the README table"


def test_readme_only_advertises_flags_that_exist():
    body = README.read_text()
    known = {flag for flags in DOCUMENTED_FLAGS.values() for flag in flags}
    advertised = {w.split("`")[0] for w in body.split("`--")[1:]}
    for flag in advertised:
        assert f"--{flag}" in known, f"README advertises unknown flag --{flag}"
