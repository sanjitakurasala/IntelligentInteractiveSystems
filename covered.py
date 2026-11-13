# covered.py: decides which slide sections the cheatsheet covers,
# both for the whole section and for each point on the slide.

import streamlit as st
from sentence_transformers import SentenceTransformer, util


@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")


def split_cheatsheet(text):
    """Cheatsheet -> list of lines/bullets (ignoring tiny fragments)."""
    lines = [line.strip(" -•*#\t") for line in text.splitlines()]
    return [line for line in lines if len(line.split()) >= 3]


def slide_points(text, title):
    """Slide text -> list of separate points (bullets/lines), without the
    title and without duplicates (animation builds repeat lines)."""
    seen, points = set(), []
    for line in text.splitlines():
        line = line.strip(" •▪◦–-*\t")
        if len(line.split()) < 3 or line == title or line in seen:
            continue
        seen.add(line)
        points.append(line)
    return points


def check_coverage(groups, cheatsheet, threshold):
    model = load_model()
    lines = split_cheatsheet(cheatsheet)
    line_vectors = model.encode(lines, convert_to_tensor=True)

    for g in groups:
        if not g["has_text"]:
            g.update(status="cant_check", score=None, match=None,
                     top_matches=[], points=[])
            continue

        # --- Whole section vs every cheatsheet line ---
        slide_vector = model.encode(g["title"] + "\n" + g["text"], convert_to_tensor=True)
        scores = util.cos_sim(slide_vector, line_vectors)[0]

        # The 3 closest cheatsheet lines, not just the best one
        top = scores.topk(min(3, len(lines)))
        g["top_matches"] = [(lines[int(i)], float(s))
                            for s, i in zip(top.values, top.indices)]
        g["score"], g["match"] = g["top_matches"][0][1], g["top_matches"][0][0]
        g["status"] = "covered" if g["score"] >= threshold else "skipped"

        # --- Each point on the slide vs every cheatsheet line ---
        points = slide_points(g["text"], g["title"])
        g["points"] = []
        if points:
            point_vectors = model.encode(points, convert_to_tensor=True)
            sims = util.cos_sim(point_vectors, line_vectors)  # one row per point
            best_scores, best_idx = sims.max(dim=1)           # best line for each point
            for p, s, i in zip(points, best_scores, best_idx):
                g["points"].append({
                    "text": p,
                    "score": float(s),
                    "match": lines[int(i)],
                    "covered": float(s) >= threshold,
                })
    return groups