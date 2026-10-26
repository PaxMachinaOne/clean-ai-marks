"""Tests for SVG/HTML/MD/DOCX/ODT container cleaners."""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "ai-watermark-scrambler" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from container_meta import (  # noqa: E402
    clean_container,
    clean_docx,
    clean_html,
    clean_markdown,
    clean_odt,
    clean_svg,
    inspect_container,
    inspect_html,
    inspect_markdown,
    inspect_svg,
)


def test_markdown_frontmatter():
    text = """---
title: Hello
generator: Claude
ai_generated: true
---
Body\u200b text.
"""
    _c2, has_ai, findings, _d = inspect_markdown(text)
    assert has_ai
    assert any("generator" in f or "ai" in f.lower() for f in findings)
    cleaned, actions = clean_markdown(text)
    assert "generator:" not in cleaned
    assert "ai_generated:" not in cleaned
    assert "title: Hello" in cleaned
    assert any("drop" in a for a in actions)


def test_markdown_frontmatter_survives_blank_lines():
    """A blank line between keys used to raise IndexError on line[0]."""
    text = "---\ntitle: Notes\n\ngenerator: Claude\n---\n\nBody.\n"

    cleaned, actions = clean_markdown(text)

    assert "title: Notes" in cleaned
    assert "generator:" not in cleaned
    assert "Body." in cleaned


def test_markdown_keeps_ordinary_keys_that_mention_a_vendor():
    text = (
        "---\n"
        "title: How I use Claude for code review\n"
        "description: Notes on the OpenAI API\n"
        "author: Alex\n"
        "generator: Claude\n"
        "---\n"
        "body\n"
    )

    _c2, has_ai, findings, _d = inspect_markdown(text)
    cleaned, actions = clean_markdown(text)

    assert has_ai
    assert any(f == "frontmatter key: generator" for f in findings)
    assert not any("value hit" in f for f in findings)
    assert "title: How I use Claude for code review" in cleaned
    assert "description: Notes on the OpenAI API" in cleaned
    assert "author: Alex" in cleaned
    assert "generator:" not in cleaned
    assert not any("value hit" in a for a in actions)


def test_markdown_frontmatter_drops_nested_lines_of_dropped_key():
    text = "---\ntitle: Notes\ngenerator:\n  name: Claude\n  version: 3\ntags:\n  - a\n---\nBody.\n"

    cleaned, _actions = clean_markdown(text)

    assert "name: Claude" not in cleaned, "nested lines must go with their parent"
    assert "version: 3" not in cleaned
    assert "title: Notes" in cleaned
    assert "- a" in cleaned, "nested lines of a kept key must survive"


def test_html_meta_strip():
    html = """<html><head>
<meta name="generator" content="ChatGPT">
<meta name="viewport" content="width=device-width">
<meta name="description" content="ok">
</head><body data-ai-model="gpt">Hi</body></html>"""
    _c2, has_ai, findings, _ = inspect_html(html)
    assert has_ai
    cleaned, actions = clean_html(html)
    assert "ChatGPT" not in cleaned
    assert "viewport" in cleaned
    assert "data-ai-model" not in cleaned
    assert "description" in cleaned
    assert any("drop" in a for a in actions)


def test_html_keeps_prose_meta_and_drops_provenance():
    html = (
        '<meta name="description" content="A review of Claude for writing">'
        '<meta property="og:title" content="Gemini vs Claude benchmark">'
        '<meta name="generator" content="Blogger">'
        '<meta name="generator" content="ChatGPT">'
        '<script type="application/ld+json">'
        '{"@type":"BlogPosting","headline":"Notes on the OpenAI API"}'
        "</script>"
        '<script type="application/ld+json">'
        '{"digitalSourceType":"trainedAlgorithmicMedia"}'
        "</script>"
        '<meta name="viewport" content="width=device-width">'
    )

    _c2, has_ai, findings, _ = inspect_html(html)
    cleaned, _actions = clean_html(html)

    assert has_ai
    assert "A review of Claude for writing" in cleaned
    assert "Gemini vs Claude benchmark" in cleaned
    assert 'content="Blogger"' in cleaned
    assert "ChatGPT" not in cleaned
    assert "Notes on the OpenAI API" in cleaned
    assert "trainedAlgorithmicMedia" not in cleaned
    assert "viewport" in cleaned
    assert not any("description" in f or "og:title" in f or "Blogger" in f for f in findings)


def test_svg_drops_generator_attrs_with_metadata():
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" inkscape:version="1.2" generator="Claude">'
        b"<metadata>c2pa</metadata><rect width=\"1\" height=\"1\"/></svg>"
    )

    cleaned, actions = clean_svg(svg)

    assert b"<metadata" not in cleaned.lower()
    assert b"inkscape:version" not in cleaned
    assert b"generator=" not in cleaned
    assert b"<rect" in cleaned
    assert any("generator-like" in a for a in actions)


def test_svg_metadata():
    svg = b"""<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg">
  <metadata>c2pa contentcredentials Anthropic</metadata>
  <circle cx="1" cy="1" r="1"/>
</svg>"""
    has_c2pa, has_ai, findings, _ = inspect_svg(svg)
    assert has_c2pa or has_ai
    cleaned, actions = clean_svg(svg)
    assert b"<metadata" not in cleaned.lower() or b"c2pa" not in cleaned.lower()
    assert b"<circle" in cleaned
    assert any("metadata" in a or "drop" in a for a in actions)


def _make_docx_with_app(app_name: str = "Claude AI Writer") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/customXml/item1.xml" ContentType="application/xml"/>
</Types>""",
        )
        zf.writestr(
            "word/document.xml",
            '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Hello</w:t></w:r></w:p></w:body></w:document>',
        )
        zf.writestr(
            "docProps/app.xml",
            f'<?xml version="1.0"?><Properties><Application>{app_name}</Application></Properties>',
        )
        zf.writestr(
            "customXml/item1.xml",
            '<?xml version="1.0"?><root>c2pa contentcredentials</root>',
        )
    return buf.getvalue()


def test_docx_strips_body_marks_and_customxml_relationships():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>A &amp; B\u200b</w:t></w:r></w:p></w:body></w:document>",
        )
        zf.writestr(
            "word/header1.xml",
            "<w:hdr><w:t>Head\u200b</w:t></w:hdr>",
        )
        zf.writestr(
            "word/_rels/document.xml.rels",
            '<Relationships>'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXml" Target="../customXml/item1.xml"/>'
            "</Relationships>",
        )
        zf.writestr("customXml/item1.xml", "<root>c2pa</root>")
    cleaned, actions = clean_docx(buf.getvalue())
    with zipfile.ZipFile(io.BytesIO(cleaned)) as zf:
        body = zf.read("word/document.xml").decode()
        header = zf.read("word/header1.xml").decode()
        rels = zf.read("word/_rels/document.xml.rels").decode()
        names = zf.namelist()
    assert "\u200b" not in body
    assert "A &amp; B" in body
    assert "\u200b" not in header
    assert "styles.xml" in rels
    assert "customXml" not in rels
    assert not any(n.startswith("customXml/") for n in names)
    assert any("relationship" in a for a in actions)
    assert any("layer A" in a for a in actions)


def test_docx_nfkc_reaches_text_nodes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", "<w:t>ﬁle</w:t>")

    cleaned, actions = clean_docx(buf.getvalue(), nfkc=True)

    with zipfile.ZipFile(io.BytesIO(cleaned)) as zf:
        assert zf.read("word/document.xml").decode() == "<w:t>file</w:t>"
    assert any("layer A" in a for a in actions)


def test_docx_strips_app_and_customxml(tmp_path: Path):
    data = _make_docx_with_app()
    cleaned, actions = clean_docx(data)
    assert any("customXml" in a or "Application" in a or "drop" in a for a in actions)
    with zipfile.ZipFile(io.BytesIO(cleaned)) as zf:
        names = zf.namelist()
        assert "word/document.xml" in names
        assert not any(n.startswith("customXml/") for n in names)
        app = zf.read("docProps/app.xml").decode()
        assert "Claude" not in app


def _make_odt(generator: str = "Anthropic Claude") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        zf.writestr(
            "meta.xml",
            f'<?xml version="1.0"?><office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0"><meta:generator>{generator}</meta:generator></office:document-meta>',
        )
        zf.writestr(
            "content.xml",
            '<?xml version="1.0"?><office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"/>',
        )
        zf.writestr(
            "META-INF/manifest.xml",
            '<?xml version="1.0"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"/>',
        )
    return buf.getvalue()


def test_odt_layer_a_runs_on_content():
    data = _make_odt()
    rebuilt = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as zin, zipfile.ZipFile(rebuilt, "w") as zout:
        for info in zin.infolist():
            payload = zin.read(info)
            if info.filename == "content.xml":
                payload = (
                    "<office:document-content><text:p>Hi\u200b</text:p>"
                    "</office:document-content>"
                ).encode()
            zout.writestr(info, payload)
    cleaned, actions = clean_odt(rebuilt.getvalue())
    with zipfile.ZipFile(io.BytesIO(cleaned)) as zf:
        content = zf.read("content.xml").decode()
    assert "\u200b" not in content
    assert "Hi" in content
    assert any("layer A" in a for a in actions)


def test_odt_drops_generator(tmp_path: Path):
    data = _make_odt()
    cleaned, actions = clean_odt(data)
    assert any("generator" in a for a in actions)
    with zipfile.ZipFile(io.BytesIO(cleaned)) as zf:
        meta = zf.read("meta.xml").decode()
        assert "Claude" not in meta
        assert "meta:generator" not in meta or "Anthropic" not in meta


def test_clean_container_markdown_honors_nfkc_and_homoglyphs(tmp_path: Path):
    src = tmp_path / "a.md"
    src.write_text("ﬁle \u0430\n", encoding="utf-8")
    dest = tmp_path / "a.cleaned.md"

    plain = tmp_path / "plain.md"
    clean_container(src, plain)
    assert plain.read_text(encoding="utf-8") == "ﬁle \u0430\n"

    clean_container(src, dest, nfkc=True, aggressive_homoglyphs=True)

    assert dest.read_text(encoding="utf-8") == "file a\n"


def test_clean_container_markdown_file(tmp_path: Path):
    src = tmp_path / "x.md"
    src.write_text("---\ngenerator: OpenAI\n---\nHi\u200b\n", encoding="utf-8")
    dest = tmp_path / "x.cleaned.md"
    result = clean_container(src, dest)
    assert dest.is_file()
    body = dest.read_text(encoding="utf-8")
    assert "generator" not in body
    assert "\u200b" not in body
    assert result["format"] == "markdown"


def test_inspect_container_svg(tmp_path: Path):
    src = tmp_path / "a.svg"
    src.write_bytes(
        b'<svg xmlns="http://www.w3.org/2000/svg"><metadata>c2pa</metadata></svg>'
    )
    report = inspect_container(src)
    assert report.format == "svg"
    assert report.has_c2pa or report.has_ai_metadata


def test_fixtures_md_html_svg_roundtrip(tmp_path: Path):
    root = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
    for name in ("sample_ai.md", "sample_ai.html", "sample_meta.svg"):
        src = root / name
        dest = tmp_path / f"{name}.cleaned{src.suffix}"
        result = clean_container(src, dest)
        assert dest.is_file()
        assert result["format"] in ("markdown", "html", "svg")
        # AI-ish keys/tags should be reduced
        body = dest.read_bytes().lower()
        assert b"chatgpt" not in body
        assert b"generator: claude" not in body


def test_pdf_degraded_clean_without_crash(tmp_path: Path):
    """Minimal PDF with an XMP packet; clean should not raise (may be degraded)."""
    from container_meta import clean_pdf, inspect_pdf

    xmp = (
        b"<?xpacket begin='' id='W5M0MpCehiHzreSzNTczkc9d'?>"
        b"<x:xmpmeta xmlns:x='adobe:ns:meta/'>"
        b"<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>"
        b"<rdf:Description>"
        b"<digitalSourceType>trainedAlgorithmicMedia</digitalSourceType>"
        b"</rdf:Description></rdf:RDF></x:xmpmeta>"
        b"<?xpacket end='w'?>"
    )
    # Minimal-ish PDF skeleton (not renderable; enough for byte-level tools)
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj<<>>endobj\n"
        b"trailer<<>>\n"
        + xmp
        + b"\n%%EOF\n"
    )
    src = tmp_path / "t.pdf"
    dest = tmp_path / "t.cleaned.pdf"
    src.write_bytes(pdf)
    has_c2pa, has_ai, findings, _ = inspect_pdf(src, pdf)
    assert has_ai or has_c2pa or findings
    actions, meta = clean_pdf(src, dest)
    assert dest.is_file()
    assert actions
    assert meta.get("mode") in ("exiftool", "stdlib-xmp", "copy")
