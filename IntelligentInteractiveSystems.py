# =====================================================================
# IntelligentInteractiveSystems.py
# ---------------------------------------------------------------------
# Everything to do with READING THE LECTURE SLIDES.
#
#   extract_slides(pdf_file) -> one dictionary per slide: number, title, text
#   group_slides(slides)     -> merges animation builds into "sections"
#   render_pages(pdf_bytes)  -> one PNG picture per slide
#   clean_text(text)         -> tidies extracted text so it's readable
#
# app.py, covered.py and objectives.py all build on what this file returns.
# =====================================================================

import logging                  # Python's built-in system for warning messages
import fitz                     # PyMuPDF: draws PDF pages as images
from pypdf import PdfReader     # pypdf: pulls the text out of a PDF

# pypdf prints harmless warnings like "Ignoring wrong pointing object"
# for PDFs exported from PowerPoint. Only show real errors.
logging.getLogger("pypdf").setLevel(logging.ERROR)


def _is_noise(line):
    """Return True if a line is NOT a real title.

    The underscore at the start of the name is a Python convention for
    "helper used only inside this file".
    """
    return (
        line.isdigit()              # a page number, e.g. "4"
        or line.startswith("http")  # an image credit URL
        or len(line) < 3            # tiny fragments, e.g. "J" or "•"
    )


def extract_slides(pdf_file):
    """Read every slide and return a list of dictionaries like:

        {"number": 19, "title": "Initialisation",
         "text": "...all the slide's text...", "has_text": True}
    """
    reader = PdfReader(pdf_file)        # open the PDF
    slides = []                         # results go in here

    # enumerate(..., start=1) gives (1, page1), (2, page2), ...
    # so slide numbers start at 1 like in the lecture, not 0.
    for i, page in enumerate(reader.pages, start=1):

        # extract_text() can return None for image-only pages, so
        # "or ''" swaps None for an empty string. strip() trims spaces.
        text = (page.extract_text() or "").strip()

        # Split into lines, trim each one, and drop empty lines.
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # Keep only lines that could be a title (not page numbers / URLs).
        useful = [line for line in lines if not _is_noise(line)]

        slides.append({
            "number": i,
            # First useful line is usually the title; otherwise a placeholder.
            "title": useful[0] if useful else f"Slide {i} (no title)",
            "text": text,
            # Over 20 characters of real text = enough for the checker to judge.
            # Under that, the slide is treated as image-only ("can't check").
            "has_text": len(" ".join(useful)) > 20,
        })

    return slides


def group_slides(slides):
    """Merge NEIGHBOURING slides that share a title into one "section".

    Lecturers often reveal bullets one at a time, which makes several
    near-identical slides (e.g. slides 64-71 "Linear Upsampling - Line by
    Line"). They're really one slide, so we treat them as one section.

    Only slides next to each other are merged; a title that comes back
    later in the deck stays separate, because it's usually new content.
    """
    groups = []

    for s in slides:
        # groups[-1] is the section we're currently building.
        # "groups and ..." first checks the list isn't empty.
        if groups and s["title"] == groups[-1]["title"]:
            # Same title as the previous slide -> add it to that section
            g = groups[-1]
            g["numbers"].append(s["number"])        # e.g. [64, 65] -> [64, 65, 66]
            g["text"] += "\n" + s["text"]           # combine their text
            g["has_text"] = g["has_text"] or s["has_text"]  # any text in the group counts
        else:
            # Different title -> start a new section
            groups.append({
                "title": s["title"],
                "numbers": [s["number"]],           # list, so more can be added
                "text": s["text"],
                "has_text": s["has_text"],
            })

    return groups


def render_pages(pdf_bytes, zoom=1.5):
    """Turn every PDF page into a PNG image (as raw bytes).

    pdf_bytes: the uploaded file's contents (uploaded.getvalue() in app.py)
    zoom:      1.5 = 150% size, so the images are sharp on screen

    Returns a list where index 0 is slide 1, index 1 is slide 2, etc.
    That's why app.py uses images[slide_number - 1].
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")   # open PDF from memory
    return [
        # get_pixmap draws the page as pixels; tobytes("png") saves it as a PNG
        page.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).tobytes("png")
        for page in doc
    ]


def clean_text(text):
    """Make extracted slide text easier to read (not used by app.py at the
    moment, kept for possible later use).

    - turns bullet symbols into markdown bullets ("- ")
    - removes page numbers
    - joins lines that the PDF broke in half
    """
    out = []
    for raw in text.splitlines():
        line = raw.strip()

        if not line or line.isdigit():          # blank line or page number
            continue

        if line[0] in "•▪◦–-*":                 # starts with a bullet symbol
            out.append("- " + line[1:].strip())
        elif out and line[0].islower():         # starts lowercase = the end of the
            out[-1] += " " + line               # previous sentence, so join it on
        else:
            out.append(line + "  ")             # two trailing spaces = line break in markdown

    return "\n".join(out)
