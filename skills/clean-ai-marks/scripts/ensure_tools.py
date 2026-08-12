#!/usr/bin/env python3
"""Report which optional cleaning tools are present; --install sets up the skill venv."""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shutil import which  # noqa: E402

from common import (  # noqa: E402
    EXIT_ERROR,
    EXIT_OK,
    SKILL_ROOT,
    SKILL_VENV,
    activate_skill_venv,
    emit_json,
    eprint,
    skill_venv_site_packages,
)

REQUIREMENTS = SKILL_ROOT / "requirements.txt"

# import name -> what it gives us
PIP_MODULES = {
    "pikepdf": "PDF metadata strip + full rewrite (bundles libqpdf)",
    "c2pa": "C2PA manifest inspection",
}

# system tool -> (what it gives us, how to get it)
SYSTEM_TOOLS = {
    "exiftool": (
        "residual metadata strip on images; no pip package exists",
        "brew install exiftool | apt install libimage-exiftool-perl",
    ),
    "qpdf": (
        "PDF rewrite; not needed when pikepdf is installed",
        "brew install qpdf | apt install qpdf",
    ),
    "c2patool": (
        "C2PA inspect; not needed when c2pa-python is installed",
        "cargo install c2patool",
    ),
}


def _module_available(name: str) -> bool:
    activate_skill_venv()
    return importlib.util.find_spec(name) is not None


def survey() -> dict:
    return {
        "venv": str(SKILL_VENV),
        "venv_exists": SKILL_VENV.is_dir(),
        "pip_modules": {
            name: {"available": _module_available(name), "role": role}
            for name, role in PIP_MODULES.items()
        },
        "system_tools": {
            name: {"available": which(name) is not None, "role": role, "install": hint}
            for name, (role, hint) in SYSTEM_TOOLS.items()
        },
    }


def install() -> int:
    if not REQUIREMENTS.is_file():
        eprint(f"missing {REQUIREMENTS}")
        return EXIT_ERROR
    if not SKILL_VENV.is_dir():
        eprint(f"creating venv at {SKILL_VENV}")
        r = subprocess.run([sys.executable, "-m", "venv", str(SKILL_VENV)], check=False)
        if r.returncode != 0:
            eprint("venv creation failed")
            return EXIT_ERROR
    python = SKILL_VENV / "bin" / "python"
    if not python.exists():  # Windows layout
        python = SKILL_VENV / "Scripts" / "python.exe"
    r = subprocess.run(
        [str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
        check=False,
    )
    if r.returncode != 0:
        eprint("pip install failed")
        return EXIT_ERROR
    return EXIT_OK


def report(data: dict) -> None:
    print(f"Skill venv: {data['venv']} ({'present' if data['venv_exists'] else 'absent'})")
    print("\nPip extras (install with --install):")
    for name, info in data["pip_modules"].items():
        print(f"  [{'x' if info['available'] else ' '}] {name}: {info['role']}")
    print("\nSystem tools (install yourself):")
    for name, info in data["system_tools"].items():
        print(f"  [{'x' if info['available'] else ' '}] {name}: {info['role']}")
        if not info["available"]:
            print(f"      {info['install']}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--install",
        action="store_true",
        help=f"Create {SKILL_VENV} and install requirements.txt into it",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.install:
        rc = install()
        if rc != EXIT_OK:
            return rc
        # Drop the stale sys.path entry so the fresh install is picked up.
        site = str(skill_venv_site_packages())
        if site in sys.path:
            sys.path.remove(site)
        importlib.invalidate_caches()

    data = survey()
    if args.json:
        emit_json(data)
    else:
        report(data)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
