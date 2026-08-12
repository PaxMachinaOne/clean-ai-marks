#!/usr/bin/env python3
"""Unified inspect: text, images (PNG/JPEG), and containers (SVG/PDF/DOCX/ODT/HTML/MD)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    EXIT_BAD_INPUT,
    EXIT_ERROR,
    EXIT_OK,
    detect_kind,
    emit_json,
    eprint,
    read_text_input,
)
from container_meta import inspect_container  # noqa: E402
from image_meta import inspect_image  # noqa: E402
from text_unicode import human_report, inspect_text  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="File to inspect")
    p.add_argument("--json", action="store_true")
    p.add_argument("--aggressive", action="store_true", help="Text: flag confusables")
    p.add_argument(
        "--as",
        dest="force_type",
        choices=("text", "image", "container", "auto"),
        default="auto",
    )
    args = p.parse_args()

    if not args.path.is_file():
        eprint(f"not a file: {args.path}")
        return EXIT_BAD_INPUT

    kind = args.force_type if args.force_type != "auto" else detect_kind(args.path)

    if kind == "text":
        report = inspect_text(read_text_input(str(args.path)), aggressive=args.aggressive)
        if args.json:
            emit_json({"kind": "text", **report.to_dict()})
        else:
            print("Kind: text")
            print(human_report(report))
        return EXIT_OK if report.suspicious_total == 0 else EXIT_ERROR

    report = inspect_image(args.path) if kind == "image" else inspect_container(args.path)
    if args.json:
        emit_json({"kind": kind, **report.to_dict()})
    else:
        print(f"Kind: {kind}")
        print(f"Path: {report.path}")
        print(f"Format: {report.format}")
        print(f"C2PA: {report.has_c2pa}")
        print(f"AI metadata: {report.has_ai_metadata}")
        for f in report.findings:
            print(f"  - {f}")
    return EXIT_ERROR if (report.has_c2pa or report.has_ai_metadata) else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
