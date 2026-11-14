"""
Headless DOCX Engine for DocuTools.
Bridges python-docx and Qt's rich text (QTextDocument / HTML).
Supports reading DOCX into structured HTML, saving HTML to DOCX, and exporting to PDF.
"""

from __future__ import annotations

import base64
import html
import io
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import docx
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor


class DocxEngine:
    """Core headless engine for DOCX parsing, authoring, and PDF conversion."""

    @staticmethod
    def docx_to_html(file_path: str | Path) -> str:
        """
        Convert a DOCX file into rich HTML for display and editing in QTextEdit.
        Preserves headings, paragraphs, bold, italic, underline, colors, lists, and tables.
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")

        doc = Document(str(p))
        html_parts: List[str] = [
            "<html><head><style>",
            "body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11pt; line-height: 1.4; color: #222; }",
            "h1 { font-size: 20pt; font-weight: bold; margin-top: 14px; margin-bottom: 6px; }",
            "h2 { font-size: 16pt; font-weight: bold; margin-top: 12px; margin-bottom: 4px; }",
            "h3 { font-size: 13pt; font-weight: bold; margin-top: 10px; margin-bottom: 3px; }",
            "p { margin-top: 4px; margin-bottom: 4px; }",
            "table { border-collapse: collapse; width: 100%; margin-top: 8px; margin-bottom: 8px; }",
            "th, td { border: 1px solid #aaa; padding: 6px 10px; text-align: left; }",
            "th { background-color: #f2f2f2; font-weight: bold; }",
            "ul, ol { margin-top: 4px; margin-bottom: 4px; padding-left: 24px; }",
            "</style></head><body>"
        ]

        # Extract paragraphs and tables in order
        for block in doc.element.body:
            if block.tag.endswith("p"):  # Paragraph
                para = docx.text.paragraph.Paragraph(block, doc)
                p_text = DocxEngine._paragraph_to_html(para)
                if p_text:
                    html_parts.append(p_text)
            elif block.tag.endswith("tbl"):  # Table
                table = docx.table.Table(block, doc)
                html_parts.append(DocxEngine._table_to_html(table))

        html_parts.append("</body></html>")
        return "".join(html_parts)

    @staticmethod
    def _paragraph_to_html(para: docx.text.paragraph.Paragraph) -> str:
        """Convert a single docx paragraph to HTML string with run styling."""
        style_name = (para.style.name if para.style else "").lower()
        tag = "p"
        if "heading 1" in style_name:
            tag = "h1"
        elif "heading 2" in style_name:
            tag = "h2"
        elif "heading 3" in style_name:
            tag = "h3"
        elif "list bullet" in style_name:
            tag = "li"
        elif "list number" in style_name:
            tag = "li"

        # Check alignment
        align_style = ""
        if para.alignment == WD_ALIGN_PARAGRAPH.CENTER:
            align_style = ' style="text-align: center;"'
        elif para.alignment == WD_ALIGN_PARAGRAPH.RIGHT:
            align_style = ' style="text-align: right;"'
        elif para.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY:
            align_style = ' style="text-align: justify;"'

        runs_html = []
        for run in para.runs:
            run_text = html.escape(run.text)
            if not run_text:
                continue

            open_tags = ""
            close_tags = ""
            styles = []

            if run.bold:
                open_tags += "<b>"
                close_tags = "</b>" + close_tags
            if run.italic:
                open_tags += "<i>"
                close_tags = "</i>" + close_tags
            if run.underline:
                open_tags += "<u>"
                close_tags = "</u>" + close_tags
            if run.font.strike:
                open_tags += "<s>"
                close_tags = "</s>" + close_tags
            if run.font.color and run.font.color.rgb:
                hex_col = f"#{run.font.color.rgb}"
                styles.append(f"color: {hex_col};")
            if run.font.size:
                styles.append(f"font-size: {run.font.size.pt:.1f}pt;")
            if run.font.name:
                styles.append(f"font-family: '{run.font.name}';")

            style_attr = f' style="{" ".join(styles)}"' if styles else ""
            if style_attr:
                runs_html.append(f"<span{style_attr}>{open_tags}{run_text}{close_tags}</span>")
            else:
                runs_html.append(f"{open_tags}{run_text}{close_tags}")

        inner_content = "".join(runs_html) or "<br/>"

        if tag == "li":
            return f"<ul><li>{inner_content}</li></ul>"
        return f"<{tag}{align_style}>{inner_content}</{tag}>"

    @staticmethod
    def _table_to_html(table: docx.table.Table) -> str:
        """Convert a docx table to clean HTML table."""
        parts = ["<table>"]
        for row_idx, row in enumerate(table.rows):
            parts.append("<tr>")
            for cell in row.cells:
                cell_tag = "th" if row_idx == 0 else "td"
                cell_text = html.escape(cell.text.strip())
                parts.append(f"<{cell_tag}>{cell_text or '&nbsp;'}</{cell_tag}>")
            parts.append("</tr>")
        parts.append("</table>")
        return "".join(parts)

    @staticmethod
    def html_to_docx(html_text: str, output_path: str | Path) -> str:
        """
        Convert HTML content (e.g. from QTextEdit.toHtml()) into a well-structured DOCX file.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        doc = Document()

        # Clean tags using regex for a clean pass
        # Extract body if present
        body_match = re.search(r"<body[^>]*>(.*?)</body>", html_text, re.DOTALL | re.IGNORECASE)
        content = body_match.group(1) if body_match else html_text

        # Split into blocks (p, h1, h2, h3, tr, li, div)
        block_pattern = re.compile(
            r"<(p|h1|h2|h3|li|tr|blockquote)[^>]*>(.*?)</\1>",
            re.DOTALL | re.IGNORECASE
        )

        blocks = block_pattern.findall(content)
        if not blocks:
            # Fallback: strip html tags and write as paragraphs
            raw_text = re.sub(r"<[^>]+>", "", content).strip()
            for line in raw_text.splitlines():
                if line.strip():
                    doc.add_paragraph(line.strip())
            doc.save(str(out_p))
            return str(out_p)

        in_table = False
        current_table = None

        for tag, inner_html in blocks:
            tag = tag.lower()
            if tag == "h1":
                clean_text = DocxEngine._clean_html_text(inner_html)
                doc.add_heading(clean_text, level=1)
            elif tag == "h2":
                clean_text = DocxEngine._clean_html_text(inner_html)
                doc.add_heading(clean_text, level=2)
            elif tag == "h3":
                clean_text = DocxEngine._clean_html_text(inner_html)
                doc.add_heading(clean_text, level=3)
            elif tag == "li":
                clean_text = DocxEngine._clean_html_text(inner_html)
                doc.add_paragraph(clean_text, style="List Bullet")
            elif tag == "tr":
                cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", inner_html, re.DOTALL | re.IGNORECASE)
                if cells:
                    if not current_table:
                        current_table = doc.add_table(rows=0, cols=len(cells))
                        current_table.style = "Table Grid"
                    row = current_table.add_row()
                    for c_idx, cell_content in enumerate(cells):
                        if c_idx < len(row.cells):
                            row.cells[c_idx].text = DocxEngine._clean_html_text(cell_content)
            else:
                current_table = None  # Reset table tracking
                p = doc.add_paragraph()
                DocxEngine._apply_html_runs_to_paragraph(p, inner_html)

        doc.save(str(out_p))
        return str(out_p)

    @staticmethod
    def _clean_html_text(raw_html: str) -> str:
        """Strip HTML tags and unescape entities."""
        text = re.sub(r"<[^>]+>", "", raw_html)
        return html.unescape(text).strip()

    @staticmethod
    def _apply_html_runs_to_paragraph(paragraph: docx.text.paragraph.Paragraph, inner_html: str) -> None:
        """Parse formatting tags (<b>, <i>, <u>, <s>, <span>) and append runs to paragraph."""
        # Simple inline token regex
        tokens = re.split(r"(<[^>]+>)", inner_html)
        is_bold = False
        is_italic = False
        is_underline = False

        for token in tokens:
            if not token:
                continue
            t_lower = token.lower()
            if t_lower in ("<b>", "<strong>"):
                is_bold = True
            elif t_lower in ("</b>", "</strong>"):
                is_bold = False
            elif t_lower in ("<i>", "<em>"):
                is_italic = True
            elif t_lower in ("</i>", "</em>"):
                is_italic = False
            elif t_lower == "<u>":
                is_underline = True
            elif t_lower == "</u>":
                is_underline = False
            elif token.startswith("<"):
                # Other tag, ignore
                continue
            else:
                txt = html.unescape(token)
                if txt:
                    run = paragraph.add_run(txt)
                    run.bold = is_bold
                    run.italic = is_italic
                    run.underline = is_underline
