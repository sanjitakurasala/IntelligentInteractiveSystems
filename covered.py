# coverage.py: decides which slide sections the cheatsheet covers.
# Uses an embedding model (text -> numbers that capture meaning) to measure
# how similar each slide section is to each cheatsheet line.

import streamlit as st
from sentence_transformers import SentenceTransformer, util


@st.cache_resource          # load the model once, not on every refresh
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")   # small, free, runs locally


def split_cheatsheet(text):
    """Break the cheatsheet into lines/bullets, dropping tiny fragments."""
    lines = [line.strip(" -•*#\t") for line in text.splitlines()]
    return [line for line in lines if len(line.split()) >= 3]


def check_coverage(groups, cheatsheet, threshold):
    """Give every section a status: covered, skipped or cant_check."""
    model = load_model()
    lines = split_cheatsheet(cheatsheet)
    line_vectors = model.encode(lines, convert_to_tensor=True)   # one vector per line

    for g in groups:
        if not g["has_text"]:                    # image-only: can't judge it
            g.update(status="cant_check", score=None, match=None)
            continue
        slide_vector = model.encode(g["title"] + "\n" + g["text"], convert_to_tensor=True)
        scores = util.cos_sim(slide_vector, line_vectors)[0]     # similarity to every line
        best = int(scores.argmax())                              # closest line
        g["score"] = float(scores[best])
        g["match"] = lines[best]
        g["status"] = "covered" if g["score"] >= threshold else "skipped"
    return groups