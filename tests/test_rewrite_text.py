"""Tests for Layer B rewrite_text hook (offline / print-prompt)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "clean-ai-marks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pytest  # noqa: E402

from rewrite_text import PROMPTS, build_prompt, rewrite  # noqa: E402


def test_build_prompt_paraphrase_contains_text():
    p = build_prompt("paraphrase", "Hello world facts 42.", lang="French", original_lang="English")
    assert "Hello world facts 42." in p
    assert "Rewrite" in p or "rewrite" in p.lower()


def test_print_prompt_backend():
    out, info = rewrite(
        "Sample prose about water marks.",
        backend="print-prompt",
        model=None,
        base_url=None,
        api_key=None,
        strength="paraphrase",
        lang="French",
        original_lang="English",
        timeout=5.0,
        layer_a_after=True,
    )
    assert info["mode"] == "print-prompt"
    assert "Sample prose" in out
    assert info["backend"] == "print-prompt"


def test_every_strength_scrambles_the_statistical_signal():
    for strength in PROMPTS:
        prompt = build_prompt(strength, "Hello.", lang="French", original_lang="English")
        assert "statistical sampling watermark" in prompt
        assert "Scramble and blur that statistical signal." in prompt


def test_prompts_match_the_published_paraphrase_attacks():
    lexical = build_prompt("paraphrase", "Hello.", lang="French", original_lang="English")
    structural = build_prompt("structural", "Hello.", lang="French", original_lang="English")
    assert "lexical diversity" in lexical
    assert "keep the sentence order" in lexical
    assert "outline" in structural
    assert "sentence order" in structural


def test_structural_and_backtranslate_prompts():
    for strength in ("structural", "backtranslate"):
        p = build_prompt(strength, "ABC 123", lang="German", original_lang="English")
        assert "ABC 123" in p


def test_backtranslate_prompt_names_both_languages():
    p = build_prompt("backtranslate", "ABC", lang="German", original_lang="English")
    assert "German" in p
    assert "English" in p


@pytest.mark.parametrize("strength", sorted(PROMPTS))
def test_braces_in_input_are_not_reinterpreted(strength: str):
    """The templates are .format()ed, so user braces must survive as literals."""
    text = "keep {TEXT} and {unknown_key} and {} intact"

    p = build_prompt(strength, text, lang="French", original_lang="English")

    assert text in p


def test_unknown_strength_is_rejected():
    with pytest.raises(ValueError, match="unknown strength"):
        build_prompt("nope", "x", lang="French", original_lang="English")
