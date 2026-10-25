"""Tests for Layer A text Unicode scrub."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "clean-ai-marks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from text_unicode import clean_text, inspect_text  # noqa: E402


def test_strips_zero_width_and_soft_hyphen():
    raw = "Hello\u200bWorld\u00ad!"
    cleaned, stats = clean_text(raw)
    assert cleaned == "HelloWorld!"
    assert stats["removed_count"] >= 2


def test_normalizes_exotic_spaces():
    raw = "a\u2003b\u3000c"  # em space, ideographic space
    cleaned, stats = clean_text(raw)
    assert cleaned == "a b c"
    assert stats["replaced_count"] >= 2


def test_inspect_finds_zwsp():
    report = inspect_text("x\u200by")
    assert report.suspicious_total >= 1
    kinds = {h.kind for h in report.hits}
    assert "zwj_family" in kinds or "strip" in kinds


def test_inspect_tag_chars():
    # Language tag character U+E0041 (TAG LATIN CAPITAL LETTER A)
    raw = "hi" + chr(0xE0041) + "there"
    report = inspect_text(raw)
    assert report.suspicious_total >= 1
    assert any(h.kind == "tag_chars" for h in report.hits)
    cleaned, stats = clean_text(raw)
    assert chr(0xE0041) not in cleaned
    assert stats["removed_count"] >= 1


def test_inspect_bidi():
    raw = "ab\u202eef"  # RLO
    report = inspect_text(raw)
    assert any(h.kind == "bidi" for h in report.hits)
    cleaned, _ = clean_text(raw)
    assert "\u202e" not in cleaned


def test_keeps_emoji_sequences_flag_tags_and_script_joiners():
    samples = [
        "\U0001f468\u200d\U0001f469\u200d\U0001f467",
        "\u2764\ufe0f",
        "\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f",
        "\u0645\u06cc\u200c\u062e\u0648\u0627\u0647\u0645",
        "\u0915\u200d\u0915",
    ]
    for raw in samples:
        cleaned, stats = clean_text(raw)
        assert cleaned == raw
        assert stats["removed_count"] == 0
        assert inspect_text(raw).suspicious_total == 0


def test_strips_stray_joiners_selectors_and_tag_chars():
    stray_zwj = "a\u200db"
    stray_zwnj = "a\u200cb"
    text_style_heart = "\u2764\ufe0e"
    lone_tag = "hi" + chr(0xE0041) + "there"
    for raw, gone in (
        (stray_zwj, "\u200d"),
        (stray_zwnj, "\u200c"),
        (text_style_heart, "\ufe0e"),
        (lone_tag, chr(0xE0041)),
    ):
        cleaned, _stats = clean_text(raw)
        assert gone not in cleaned
        assert inspect_text(raw).suspicious_total >= 1


def test_clean_preserves_normal_text():
    raw = "Normal ASCII and café — fine."
    cleaned, stats = clean_text(raw)
    assert cleaned == raw
    assert stats["removed_count"] == 0


def test_aggressive_confusable():
    # Cyrillic 'а' (U+0430) looks like Latin 'a'
    raw = "p\u0430y"  # p + cyrillic a + y
    cleaned, _ = clean_text(raw, aggressive_homoglyphs=True)
    assert cleaned == "pay"
