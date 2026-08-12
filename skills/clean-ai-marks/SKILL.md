---
name: clean-ai-marks
description: >
  Remove multi-vendor AI provenance marks: invisible Unicode (Layer A), statistical
  text watermarks via rewrite (Layer B, always offer), and C2PA/EXIF/XMP/container
  metadata on PNG/JPEG/SVG/PDF/DOCX/ODT/HTML/MD. Covers Claude, Gemini/SynthID-class,
  OpenAI provenance, and open-LLM sampling marks. Use when the user asks to strip
  watermarks, remove C2PA/Content Credentials, clean AI metadata, remove invisible
  Unicode, anti-detect clean AI output, or runs /clean-ai-marks (aliases:
  /remove-ai-marks, /remove-claude-marks).
---

# Clean AI marks

## Setup

- Set `SCRIPTS` to the absolute path of this skill's `scripts/` directory.
- Every command below assumes it.
- Relative paths fail from any other working directory.

```bash
SCRIPTS="<absolute path of this skill>/scripts"
```

## Rules

- Inspect before cleaning. Inspect again after, to verify.
- Exit 1 from an inspect means **marks found**, not command failure. Never report it as
  a tool error.
- Exit 3 means **degraded** — output not fully cleaned. Always tell the user.
- Write `*.cleaned.*` by default. Use `--in-place` only when asked.
- Always offer Layer B for prose. Never skip it silently.
- Never claim the result is undetectable or free of AI provenance.

## Sequence

### 1. Dispatch

| Input | Command |
| --- | --- |
| Any single file, type unknown | `inspect_file.py` → `clean_file.py` |
| `.txt`, code | `clean_text.py` (add a formatter for code) |
| `.md`, `.html` | `clean_file.py` — strips metadata *and* runs Layer A |
| `.png`, `.jpg`, `.jpeg` | `clean_file.py` or `clean_image.py` |
| `.svg`, `.pdf`, `.docx`, `.odt` | `clean_file.py` |
| Pasted text | write to a temp file, or pipe to `clean_text.py -` |
| Directory | loop `clean_file.py` over each matching file |

- Prefer `inspect_file.py` / `clean_file.py`.
- They dispatch by extension, then by byte signature.
- Override with `--as text|image|container` only when detection is wrong.

### 2. Inspect

```bash
python3 "$SCRIPTS/inspect_file.py" --json INPUT
```

- Report suspicious codepoints and C2PA/AI flags in two or three lines.
- Do not paste the whole JSON.

### 3. Clean (deterministic)

```bash
python3 "$SCRIPTS/clean_file.py" INPUT -o OUTPUT
python3 "$SCRIPTS/inspect_file.py" OUTPUT
```

- The second command is the verification. Exit 0 means clean.
- Text-only with Layer A statistics: `clean_text.py INPUT -o OUTPUT --stats`.
- `--nfkc` NFKC-normalizes; `--aggressive-homoglyphs` maps Cyrillic and fullwidth
  lookalikes to ASCII.
- Both alter characters the user may have intended. Mention them; do not apply silently.

### 4. Layer B — rewrite (prose only)

- Layer A cannot touch statistical token-sampling watermarks. Only a rewrite can.
- Offer it for every natural-language input.
- Order: Layer A → paraphrase → optional stronger pass → Layer A again → report.
- Use a rewrite model **different from the suspected origin** (Claude text → not Claude).
- Prefer a local Ollama model.

```bash
# get the exact prompt to run yourself
python3 "$SCRIPTS/rewrite_text.py" INPUT --backend print-prompt --strength paraphrase

# or drive a local model directly
python3 "$SCRIPTS/rewrite_text.py" INPUT -o OUTPUT \
  --backend ollama --model llama3.2 --base-url http://127.0.0.1:11434
```

- `--strength`: `paraphrase` (default), `backtranslate` (stronger), `structural`
  (strongest, most meaning drift).
- `print-prompt` calls no model — use it to obtain the prompt, then rewrite yourself.
- Layer A re-runs on model output automatically; `--no-layer-a-after` disables it.
- For code: formatter (`prettier`, `black`, `gofmt`) plus Layer A. Rewrite code only
  with explicit user approval.

### 5. Report

State all four, separately:

- **Removed, verified** — counts and actions from Layer A / metadata strip.
- **Best-effort** — what Layer B did. No undetectability claim.
- **Degraded** — any exit 3, and which tool would fix it.
- **Out of scope** — see below. These survive a clean and may still be detectable by
  vendor tools.

## Exit codes

| Code | Meaning | Action |
| --- | --- | --- |
| 0 | Clean | Proceed |
| 1 | Marks found, or residual signals after a clean | Report the findings |
| 2 | Bad path or unsupported type | Fix the argument |
| 3 | Degraded — output not fully cleaned | Install the missing tool, then say so |

## Optional tools

```bash
python3 "$SCRIPTS/ensure_tools.py"            # status table
python3 "$SCRIPTS/ensure_tools.py" --install  # skill venv + requirements.txt
```

- Installs `pikepdf` (PDF strip and rewrite) and `c2pa-python` (C2PA inspect).
- The scripts find them on their own.
- `exiftool` has no pip package — install it with the system package manager.
- `qpdf` and `c2patool` are needed only when the pip equivalents are absent.
- Without a PDF rewriter, PDF cleans exit 3.

## Out of scope

Do not claim to remove these:

- Pixel, audio, and video watermarks (SynthID-media class).
- C2PA **soft binding** — an in-content watermark that re-links to a remote manifest.
  Stripping the hard-bound manifest does not clear it.
- Detectors requiring a vendor secret key.
- Data-driven model backdoors (trigger phrases).

## References

- `references/mark-classes.md` — Unicode, sampling, C2PA, containers
- `references/vendor-notes.md` — Claude, Gemini/SynthID, OpenAI, open-LLM
- `references/removal-matrix.md` — which layer applies when
- `references/how-claude-marks.md` — Anthropic-specific detail
- `README.md` — full CLI reference and the residual-risk table
