# clean-ai-marks

Removes machine-readable AI provenance marks from text and files:

- **Layer A**: invisible Unicode (zero-width, bidi, tag chars, variation selectors, exotic spaces). Deterministic and verifiable.
- **Layer B**: statistical token-sampling watermarks, reduced by rewrite. Best-effort.
- **Container metadata**: C2PA / EXIF / XMP / document properties on PNG, JPEG, SVG, PDF, DOCX, ODT, HTML, Markdown.

Covers Claude, Gemini / SynthID-class, OpenAI, and open-LLM marks. `SKILL.md` is the agent-facing workflow; this file is the human-facing one.

## Install

The scripts run on the standard library alone. Optional extras only remove degraded modes:

```bash
python3 scripts/ensure_tools.py            # status table
python3 scripts/ensure_tools.py --install  # create .venv, install requirements.txt
```

That installs `pikepdf` (PDF strip + rewrite) and `c2pa-python` (C2PA inspect) into the skill's own `.venv`, which the scripts discover on their own. `exiftool` has no pip package and must come from a system package manager; `qpdf` and `c2patool` are only needed when their pip equivalents are absent.

## Quickstart

```bash
python3 scripts/inspect_file.py notes.md              # look first
python3 scripts/clean_file.py notes.md -o notes.cleaned.md
python3 scripts/inspect_file.py notes.cleaned.md      # verify
```

`inspect_file` / `clean_file` dispatch on file type. The per-type scripts are also available directly:

| Script | Purpose |
| --- | --- |
| `inspect_text.py` / `clean_text.py` | Layer A on text or stdin (`-`) |
| `inspect_image.py` / `clean_image.py` | PNG / JPEG metadata |
| `inspect_file.py` / `clean_file.py` | Unified: text, image, container |
| `rewrite_text.py` | Layer B rewrite hook |
| `ensure_tools.py` | Optional-tool status and venv setup |

Useful flags: `--json` (machine-readable report), `--in-place` (writes a `.bak` first), `--stats`, `--nfkc`, `--aggressive-homoglyphs`, `--keep-non-ai-metadata` (images: drop only C2PA/AI-looking segments), `--as` (force the dispatch type).

## Layer B rewrite

Statistical marks live in word choice, not metadata, so only a rewrite touches them. Default backend prints the prompt and calls no model:

```bash
python3 scripts/rewrite_text.py draft.md --backend print-prompt

export WATERMARKS_REWRITE_BACKEND=ollama
export WATERMARKS_REWRITE_MODEL=llama3.2
export WATERMARKS_REWRITE_BASE_URL=http://127.0.0.1:11434
python3 scripts/rewrite_text.py draft.md -o draft.rewritten.md --strength paraphrase
```

Strengths: `paraphrase` (default), `backtranslate` (stronger token reshuffle), `structural` (strongest, most meaning drift). Backends: `print-prompt`, `ollama`, `openai-compatible`.

Prefer a rewrite model **different from the suspected origin**: rewriting Claude text with Claude can re-stamp it. Layer A runs again on the result unless `--no-layer-a-after`.

For code, prefer a formatter (`prettier`, `black`, `gofmt`) plus Layer A; statistical marks in code are weak and rewriting risks correctness.

## Format support

| Format | What is removed |
| --- | --- |
| Text / code | Invisible Unicode, bidi controls, exotic spaces |
| PNG / JPEG | C2PA (APP11/JUMBF), text chunks, EXIF/XMP AI tags |
| SVG | `<metadata>` blocks, XMP packets |
| PDF | XMP + document info (rewritten via `pikepdf`, else `qpdf`) |
| DOCX / ODT | Document properties, `customXml`, `meta:generator` |
| HTML | `meta` generator, JSON-LD provenance, `data-ai*` |
| Markdown | AI keys in YAML frontmatter |

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Clean: nothing found, or everything removed |
| 1 | Marks found (inspect), or residual C2PA/AI signals after a clean |
| 2 | Bad input (missing file, unsupported type) |
| 3 | Degraded: the cleaner ran without the tools it needed; output is not fully cleaned |

Inspect scripts exit 1 on a dirty file, so guard them in `make`-style pipelines (`-` prefix) or `if` blocks.

These codes are uniform across every script, so exit 1 always means *marks found* and never *the file was unreadable*; a missing or unopenable path is always 2. `tests/test_cli_contract.py` pins that, along with the flag lists above.

## Residual risk after a clean

A successful strip does not mean no provenance remains. What survives:

| Channel | Survives our clean? | How to check |
| --- | --- | --- |
| Invisible Unicode | No | re-run `inspect_text` / `inspect_file` |
| Hard-bound C2PA manifest | No | Content Credentials verify, `c2pa-python` |
| C2PA **soft binding** (in-content link to a remote manifest) | **Yes, by design** | vendor detector only |
| Pixel / audio / video watermarks (SynthID-media) | **Yes** | SynthID Detector |
| Statistical text watermark | Reduced, not provably gone | vendor detector / secret key |
| Data-driven model backdoors | **Yes** | out of reach |

Report the three buckets separately: what was verifiably removed (counts, actions), what was best-effort (Layer B), and what was never in scope. Layer B cannot be gold-verified without vendor detectors or keys, so no "undetectable" claim is supportable.

## Reference docs

- `references/mark-classes.md`: Unicode / sampling / C2PA / containers
- `references/vendor-notes.md`: Claude, Gemini/SynthID, OpenAI, open-LLM
- `references/removal-matrix.md`: which layer applies when
- `references/how-claude-marks.md`: Anthropic-specific detail

## Development

From the repository root:

```bash
make tools   # install optional extras
make test    # pytest (tests/)
make smoke   # end-to-end run over tests/fixtures
```
