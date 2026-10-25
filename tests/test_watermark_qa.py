"""Pins the research harness: Layer A holds the z-score, a rewrite moves it."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "demo"))

from watermark_qa import run_pair  # noqa: E402

KEY = "research-key"
GAMMA = 0.25
N = 400
SEED = 2026
RATE = 0.3


def _row(mode: str, window: int) -> dict:
    return run_pair(n=N, key=KEY, gamma=GAMMA, rate=RATE, seed=SEED, mode=mode, window=window)


def test_layer_a_does_not_move_the_green_list_score():
    row = _row("context", 8)
    assert row["layer_a_removed"] == 0
    assert row["z_after_layer_a"] == row["z_marked"]
    assert row["z_marked"] > 30


def test_short_context_survives_a_light_rewrite_and_a_long_window_does_not():
    short = _row("context", 1)
    long = _row("context", 8)
    unigram = _row("unigram", 0)

    assert short["z_rewritten"] < short["z_marked"]
    assert short["z_rewritten"] > 10
    assert long["z_rewritten"] < 4
    assert unigram["z_rewritten"] > 20
    assert long["z_rewritten"] < unigram["z_rewritten"]


def test_cli_prints_the_three_default_rows():
    result = subprocess.run(
        [sys.executable, str(ROOT / "demo" / "watermark_qa.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "context/1" in result.stdout
    assert "context/8" in result.stdout
    assert "unigram" in result.stdout
    assert "ZeroGPT" not in result.stdout
