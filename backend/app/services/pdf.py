from __future__ import annotations

import os
from typing import List, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from ..config import settings
from .utils import slugify

# Template folder
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")

class TemplateError(Exception): ...
class RenderError(Exception): ...
class FileIOError(Exception): ...

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"])
)

def render_deck_to_pdf(slides: List[Dict], deck_title: str, out_dir: str | None = None) -> str:
    """
    Renders the provided slides into a PDF and writes it to FILE_STORAGE_DIR (or out_dir).
    Returns a relative path suitable for building a URL, e.g. '/generated/acme_offdeal_abc123.pdf'.
    """
    try:
        tpl = _env.get_template("deck.html")
    except Exception as e:
        raise TemplateError(f"Template not found or invalid: {e!s}")

    html = tpl.render(deck_title=deck_title, slides=slides)

    # Output directory
    out_dir = (out_dir or settings.FILE_STORAGE_DIR).rstrip("/")
    os.makedirs(out_dir, exist_ok=True)

    # Filename
    base = slugify(deck_title) or "offdeal_pitch"
    filename = f"{base}.pdf"
    abs_path = os.path.join(out_dir, filename)

    try:
        HTML(string=html, base_url=out_dir).write_pdf(abs_path)
    except Exception as e:
        raise RenderError(f"Failed to render PDF: {e!s}")

    if not os.path.exists(abs_path):
        raise FileIOError("PDF file was not created.")

    # For static serving, we expose under /generated
    # settings.FILE_STORAGE_DIR should map to /generated in main.py
    rel_url_path = f"/generated/{filename}"
    return rel_url_path
