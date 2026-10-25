# Removal matrix

| Target | Method | Script / action | Side effects | Verifiable today? |
| --- | --- | --- | --- | --- |
| Invisible Unicode / exotic spaces / bidi / tags | Strip / normalize | `inspect_text.py`, `clean_text.py`, `clean_file.py` | Keeps emoji ZWJ, emoji VS16, flag tags, and script joiners | Yes (codepoint report) |
| Statistical text watermark (SynthID-class / Kirchenbauer) | Simpler synonyms, lexical paraphrase, back-translate, or outline plus order diversity | Agent Layer B + optional `rewrite_text.py` | Meaning/style drift | No without vendor key/detector |
| C2PA on PNG/JPEG | Drop APP11 / text chunks / exiftool | `clean_image.py` | Loses provenance metadata | Yes |
| SVG metadata / XMP | Drop `<metadata>`, xmpmeta | `clean_file.py` | Loses SVG metadata | Yes (re-inspect) |
| PDF XMP / info / C2PA associated file | pikepdf strip + rewrite (else exiftool + qpdf) | `clean_file.py` | Loses PDF metadata and C2PA embedded manifests; degraded (exit 3) without a rewriter | Partial |
| DOCX props / customXml / body Unicode | Rewrite OOXML zip, drop customXml relationships, Layer A on text nodes | `clean_file.py` | Loses doc properties and invisible characters in the text | Yes |
| ODT meta:generator / body Unicode | Scrub `meta.xml`, Layer A on `content.xml` text | `clean_file.py` | Loses generator tag and invisible characters in the text | Yes |
| HTML AI generator / provenance JSON-LD / `data-ai*` | Strip those tags | `clean_file.py` | Description, Open Graph, a CMS generator, and ordinary JSON-LD stay | Yes |
| Markdown AI frontmatter keys | Drop provenance key names | `clean_file.py` | Title and description stay, including when they mention a vendor | Yes |
| Pixel / audio / video watermarks (SynthID-media) | - | Out of scope. Regeneration needs a generative denoiser; a blur is not a substitute | - | - |
| Visible overlays (logos, stock stamps) | - | Out of scope. Single-image removal does not recover the pixels underneath | - | - |
| C2PA soft binding (in-content link to manifest) | - | Out of scope (survives our metadata strip) | - | Vendor detector only |
| Data-driven model backdoors | - | Out of scope | - | - |

## Default pipeline

1. **Inspect** (`inspect_file.py` or specific inspect_*).
2. **Deterministic clean**: Layer A text and/or container/image metadata.
3. **Always offer Layer B** rewrite for prose (paraphrase → optional strong pass).
4. Prefer a **non-origin** rewrite model when available (avoid re-stamping).
5. Layer A again after rewrite.
6. Report: Layer B is best-effort; residual risk remains.

## Code vs prose

- **Prose / Markdown / HTML body:** full A + B.
- **Code:** Layer A + formatter; statistical marks are weak; light rewrite only with user OK.

## Layer B strengths

| Strength | When |
| --- | --- |
| `paraphrase` | Default |
| `simplify` | Content words only, shorter common synonyms, same order |
| `backtranslate` | Stronger token reshuffle |
| `structural` | Strongest; most drift |
