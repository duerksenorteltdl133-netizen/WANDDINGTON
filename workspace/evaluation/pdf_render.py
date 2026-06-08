#!/usr/bin/env python3
"""Render PDF pages to base64 PNG using pymupdf. Called as subprocess by vision.ts."""
import sys
import json
import base64

try:
    import fitz  # pymupdf
except ImportError:
    print(json.dumps({"error": "pymupdf not installed: pip install pymupdf"}))
    sys.exit(1)


def render_pages(pdf_path: str, dpi: int = 150, max_pages: int = 30) -> list:
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(min(len(doc), max_pages)):
        page = doc[i]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
        pages.append({
            "page_num": i + 1,
            "width": pix.width,
            "height": pix.height,
            "b64_png": b64,
        })
    return pages


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: pdf_render.py <pdf_path> [dpi] [max_pages]"}))
        sys.exit(1)

    pdf_path = sys.argv[1]
    dpi = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    try:
        result = render_pages(pdf_path, dpi, max_pages)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
