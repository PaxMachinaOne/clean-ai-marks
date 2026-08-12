# clean-ai-marks

An agent skill that strips machine-readable AI provenance marks from text and files.

- **Layer A**: invisible Unicode (zero-width, bidi, tag chars, variation selectors, exotic spaces). Deterministic, verifiable.
- **Layer B**: statistical token-sampling watermarks, reduced by rewrite. Best-effort.
- **Metadata**: C2PA / EXIF / XMP / document properties on PNG, JPEG, SVG, PDF, DOCX, ODT, HTML, Markdown.

Covers Claude, Gemini / SynthID-class, OpenAI, and open-LLM marks.

Tool usage, flags, exit codes, and the residual-risk table live in
**[`skills/clean-ai-marks/README.md`](skills/clean-ai-marks/README.md)**. This file covers the repository.

## Quick start

```bash
make tools    # optional extras (pikepdf, c2pa-python) into the skill venv
make test     # pytest
make smoke    # end-to-end CLI run over tests/fixtures

python3 skills/clean-ai-marks/scripts/inspect_file.py notes.md
python3 skills/clean-ai-marks/scripts/clean_file.py notes.md -o notes.cleaned.md
```

## Layout

```
skills/clean-ai-marks/
  SKILL.md          agent-facing workflow
  README.md         human-facing tool documentation
  references/       mark classes, vendor notes, removal matrix, Claude specifics
  scripts/          CLI entry points and supporting modules
  requirements.txt  optional extras
tests/              pytest suite and fixtures
Makefile            tools / test / smoke / install-skill / clean
```

## Make targets

| Target | Does |
| --- | --- |
| `tools` | Creates `skills/clean-ai-marks/.venv` and installs the optional extras |
| `test` | Runs pytest |
| `smoke` | Drives the CLI end to end over `tests/fixtures` |
| `install-skill` | Symlinks the skill into `~/.grok/skills/` |
| `clean` | Drops `__pycache__`, `.pytest_cache`, and both venvs |

## Dependencies

Two separate install paths. Do not confuse them:

| Situation | Use | Gets |
| --- | --- | --- |
| Skill installed on a host, no repo | `ensure_tools.py --install` | Skill extras into `<skill>/.venv` |
| Working on this repo | `pip install -r requirements-dev.txt` | Skill extras **+ pytest** |

- The skill is self-contained: it ships its own `requirements.txt` and installs it into its own venv, so a fresh host needs nothing from this repo.
- `requirements-dev.txt` exists only to add the test runner. Nothing at runtime reads it.
- The scripts run on the Python standard library alone.
- Optional extras only remove degraded modes; they are never required.
- `pikepdf`: PDF strip and rewrite. Without it (or `qpdf`), PDF cleans exit 3 and the pre-strip revision stays readable.
- `c2pa-python`: C2PA manifest inspection.
- `exiftool`: no pip package; install with `brew install exiftool` or `apt install libimage-exiftool-perl`.
- Run `python3 skills/clean-ai-marks/scripts/ensure_tools.py` for a status table.

## Tests

- Suite covers the Unicode and container cleaners, image metadata paths, the Layer B rewrite hook, security properties (zip bombs, symlink writes, path handling), and a CLI contract pinning documented exit codes and flags against real `--help` output.
- Tests needing `pikepdf` or `c2pa` skip themselves when absent, so the suite passes with or without the extras.
- `make test` uses `.venv/bin/python` when a repo-level venv exists, `python3` otherwise.
- The skill venv at `skills/clean-ai-marks/.venv` is added to `sys.path` by the scripts, so no activation needed.

## CI

- Runs `make test` and `make smoke` on push, pull request, and manual dispatch.
- Matrix: Python 3.11, 3.12, 3.13.
- Installs `exiftool` so its branches are exercised; the pip extras install non-fatally, since a missing wheel must not fail a build the suite is designed to survive.

## Scope

| Channel | Removed? |
| --- | --- |
| Invisible Unicode | Yes (verify by re-inspecting) |
| Hard-bound C2PA manifest | Yes (verify by re-inspecting) |
| Container metadata (EXIF, XMP, doc props) | Yes |
| Statistical text watermark | Reduced, not provably gone |
| C2PA **soft binding** | No (survives by design) |
| Pixel / audio / video watermarks (SynthID-media) | No |
| Data-driven model backdoors | No |

A clean does not mean no AI provenance remains. Check the residual-risk table in the
skill README before relying on a result.

## Intended use

Provenance marks travel with a file whether or not you want them to. The marks this tool
removes routinely carry more than "an AI touched this": EXIF holds GPS coordinates and
device serials, XMP and document properties hold author names and editing history, and
invisible Unicode survives copy-paste into systems that never expected it. Stripping that
from your own documents before you publish them is ordinary hygiene.

Built for:

- Removing metadata from files you own or are authorized to process, before release.
- Sanitizing text where zero-width characters break downstream parsing, diffs, or search.
- Research on watermark robustness, and red-teaming provenance schemes to find where they
  fail.

Not built for defeating disclosure obligations. Where a person or institution is owed an
honest answer about how something was made (academic submissions, journalism, legal
attestations, contexts with an explicit AI-disclosure policy), removing the mark does not
change the answer you owe them, and this tool will not make an undisclosed submission
truthful.

Two limits worth stating plainly, because they cut both ways: the results are best-effort,
not guarantees, and a passing inspection is not proof of anything (see Scope above). Local
law on metadata removal, evidence handling, and document tampering is yours to check.

## License

Apache License 2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

Copyright 2026 Novatechflow
