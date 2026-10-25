# clean-ai-marks

Scrambles and blurs **statistical text watermarks**. That is the job: the token-sampling signal (green-list, SynthID-Text, Claude's embedded text watermark, and the same class) lives in word choice, and a rewrite changes that choice. It does not certify that a detector with the vendor key will miss it.

The same scripts also strip marks that ride along with the file:

- **Layer A**: invisible Unicode (zero-width, bidi, tag chars, variation selectors, exotic spaces). Deterministic and verifiable. This is not the statistical watermark.
- **Container metadata**: C2PA / EXIF / XMP / document properties on PNG, JPEG, SVG, PDF, DOCX, ODT, HTML, Markdown.

Pixel, audio, video, and visible watermarks are a different thing and are not this tool.

Covers Claude, Gemini / SynthID-class, OpenAI, and open-LLM marks. `SKILL.md` is the agent-facing workflow; this file is the human-facing one. An agent only loads `SKILL.md` from a skill directory (`~/.grok/skills`, `~/.claude/skills`, `~/.cursor/skills`, or the matching project directory). The repo README has the symlink commands, how a statistical text watermark is embedded, why a rewrite blurs it, and the paper list. `make install-skill` covers Grok.

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

## Layer B: scramble and blur the statistical watermark

This is the point of the tool. A statistical watermark is a bias on the next token. Scrambling changes which tokens appear and in what order. Blurring is that same change seen from the detector: the green-list score falls because the tokens moved. Default backend prints the prompt and calls no model:

```bash
python3 scripts/rewrite_text.py draft.md --backend print-prompt

export WATERMARKS_REWRITE_BACKEND=ollama
export WATERMARKS_REWRITE_MODEL=llama3.2
export WATERMARKS_REWRITE_BASE_URL=http://127.0.0.1:11434
python3 scripts/rewrite_text.py draft.md -o draft.rewritten.md --strength paraphrase
```

Strengths, all of them aimed at the statistical signal: `paraphrase` (default: high lexical diversity, stable sentence order), `simplify` (shorter common words for content words only, same order), `backtranslate` (pivot language and back), `structural` (outline, then new wording and sentence order; most drift). Backends: `print-prompt`, `ollama`, `openai-compatible`. See `references/watermark-attacks.md`.

Prefer a rewrite model **different from the suspected origin**: rewriting Claude text with Claude can re-stamp it. Layer A runs again on the result unless `--no-layer-a-after`.

For code, prefer a formatter (`prettier`, `black`, `gofmt`) plus Layer A; statistical marks in code are weak and rewriting risks correctness.

## Format support

| Format | What is removed |
| --- | --- |
| Text / code | Invisible Unicode, bidi controls, exotic spaces |
| PNG / JPEG | C2PA (APP11/JUMBF), text chunks, EXIF/XMP AI tags |
| SVG | `<metadata>` blocks, XMP packets |
| PDF | XMP, document info, and C2PA associated-file manifests (`pikepdf`, else `qpdf`) |
| DOCX / ODT | Document properties, `customXml` (parts and relationships), `meta:generator`, invisible Unicode in the text |
| HTML | AI `generator` meta, provenance meta names, provenance JSON-LD, `data-ai*`. Description, Open Graph, a CMS generator, and ordinary JSON-LD stay |
| Markdown | Provenance key names in YAML frontmatter. A title or description that mentions a vendor stays |

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Clean: nothing found, or everything removed |
| 1 | Marks found (inspect), or residual C2PA/AI signals after a clean |
| 2 | Bad input (missing file, unsupported type, or a file the cleaner cannot read) |
| 3 | Degraded: the cleaner ran without the tools it needed; output is not fully cleaned |

Inspect scripts exit 1 on a dirty file, so guard them in `make`-style pipelines (`-` prefix) or `if` blocks.

These codes are uniform across every script, so exit 1 always means *marks found* and never *the file was unreadable*. A missing path, an unsupported type, or a file the cleaner cannot read is exit 2. `tests/test_cli_contract.py` pins that, along with the flag lists above.

## Residual risk after a clean

A successful strip does not mean no provenance remains. What survives:

| Channel | Survives our clean? | How to check |
| --- | --- | --- |
| Invisible Unicode | No | re-run `inspect_text` / `inspect_file` |
| Hard-bound C2PA manifest | No | Content Credentials verify, `c2pa-python` |
| C2PA **soft binding** (in-content link to a remote manifest) | **Yes, by design** | vendor detector only |
| Pixel / audio / video watermarks (SynthID-media) | **Yes** | SynthID Detector |
| Visible overlays (logos, stock stamps) | **Yes** | Look at the image |
| Statistical text watermark | Scrambled and blurred by Layer B, not provably gone | vendor detector / secret key |
| Data-driven model backdoors | **Yes** | out of reach |

Report the three buckets separately: what was verifiably removed (counts, actions), what was best-effort (Layer B), and what was never in scope. Layer B cannot be gold-verified without vendor detectors or keys, so no "undetectable" claim is supportable.

## Reference docs

- `references/mark-classes.md`: Unicode / sampling / C2PA / containers
- `references/vendor-notes.md`: Claude, Gemini/SynthID, OpenAI, open-LLM
- `references/removal-matrix.md`: which layer applies when
- `references/how-claude-marks.md`: Anthropic-specific detail
- `references/watermark-attacks.md`: sampling, pixel, and visible watermarks

## Development

From the repository root:

```bash
make tools   # install optional extras
make test    # pytest (tests/)
make smoke   # end-to-end run over tests/fixtures
```
