import logging
from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)


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
            "has_text": len(" ".join(useful)) > 20,
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