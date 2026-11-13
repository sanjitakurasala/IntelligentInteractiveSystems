# ---------------------------------------------------------------
# IntelligentInteractiveSystems.py: reading the lecture slides
#   extract_slides -> number, title and text for each slide
#   group_slides   -> merges animation builds into one section
#   render_pages   -> turns each PDF page into an image
#   clean_text     -> tidies extracted text so it's readable
# ---------------------------------------------------------------

import logging
import fitz                      # PyMuPDF: renders PDF pages as images
from pypdf import PdfReader      # reads the text out of the PDF

logging.getLogger("pypdf").setLevel(logging.ERROR)   # hide harmless PDF warnings


def _is_noise(line):
    """Page numbers, URLs and tiny fragments aren't real titles."""
    return line.isdigit() or line.startswith("http") or len(line) < 3


def extract_slides(pdf_file):
    """Return a list of slides, each with its number, title and text."""
    reader = PdfReader(pdf_file)
    slides = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        useful = [line for line in lines if not _is_noise(line)]
        slides.append({
            "number": i,
            "title": useful[0] if useful else f"Slide {i} (no title)",
            "text": text,
            "has_text": len(" ".join(useful)) > 20,   # enough text to check?
        })
    return slides


def group_slides(slides):
    """Merge consecutive slides with the same title (animation builds)."""
    groups = []
    for s in slides:
        if groups and s["title"] == groups[-1]["title"]:
            g = groups[-1]
            g["numbers"].append(s["number"])
            g["text"] += "\n" + s["text"]
            g["has_text"] = g["has_text"] or s["has_text"]
        else:
            groups.append({
                "title": s["title"],
                "numbers": [s["number"]],
                "text": s["text"],
                "has_text": s["has_text"],
            })
    return groups


def render_pages(pdf_bytes, zoom=1.5):
    """Return a PNG image (as bytes) for every page of the PDF.
    zoom 1.5 makes the images sharper than the default."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return [page.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).tobytes("png")
            for page in doc]


def clean_text(text):
    """Make extracted slide text readable: real bullets, no page numbers,
    and lines that PDF extraction broke in half joined back together."""
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.isdigit():           # skip blanks and page numbers
            continue
        if line[0] in "•▪◦–-*":                  # a bullet point
            out.append("- " + line[1:].strip())
        elif out and line[0].islower():          # continuation of previous line
            out[-1] += " " + line
        else:
            out.append(line + "  ")              # two spaces = line break in markdown
    return "\n".join(out)