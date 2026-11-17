# ---------------------------------------------------------------
# objectives.py: links learning objectives to the slides that answer them
#   find_objectives  -> tries to auto-detect a "Learning objectives" slide
#   match_objectives -> for each objective: most relevant slides, their key
#                       points, and whether the cheatsheet covers it
# ---------------------------------------------------------------

from sentence_transformers import util
from covered import load_model, slide_points, split_cheatsheet

KEYWORDS = ("learning objective", "learning outcome", "by the end of",
            "you will be able to", "objectives", "outcomes")


def find_objectives(slides):
    """Look for a slide that lists learning objectives and return its bullet points."""
    for s in slides:
        if any(k in s["text"].lower() for k in KEYWORDS):
            lines = [l.strip(" •▪◦–-*\t") for l in s["text"].splitlines()]
            objs = [l for l in lines
                    if len(l.split()) >= 3                        # real sentences only
                    and not any(k in l.lower() for k in KEYWORDS)] 
            #The not any(k in l.lower() for k in KEYWORDS) check drops any line containing “learning objective”, “by the end of”, “you will be able to” and so on, leaving only the actual bullets # skip the heading
            if objs:
                return objs
    return []           # none found: the student types them in


def match_objectives(objectives, groups, cheatsheet="", top_k=3, threshold=0.45):
    """For each objective, rank slide sections by how well they match it."""
    model = load_model()

    # Only sections with text can be matched (image-only slides can't be compared)
    usable = [g for g in groups if g["has_text"]]
    if not usable or not objectives:
        return []

    # Turn objectives and slide sections into vectors
    obj_vecs = model.encode(objectives, convert_to_tensor=True)
    sec_vecs = model.encode([g["title"] + "\n" + g["text"] for g in usable],
                            convert_to_tensor=True)
    sims = util.cos_sim(obj_vecs, sec_vecs)        # rows = objectives, cols = sections

    # Cheatsheet lines, if the student gave a cheatsheet
    lines = split_cheatsheet(cheatsheet) if cheatsheet else []
    line_vecs = model.encode(lines, convert_to_tensor=True) if lines else None

    results = []
    for oi, obj in enumerate(objectives):
        # --- Most relevant slide sections for this objective ---
        top = sims[oi].topk(min(top_k, len(usable)))
        ranked = []
        for score, idx in zip(top.values, top.indices):
            g = usable[int(idx)]

            # Key points: the bullets on this slide closest to the objective
            pts = slide_points(g["text"], g["title"])
            key_points = []
            if pts:
                p_scores = util.cos_sim(obj_vecs[oi], model.encode(pts, convert_to_tensor=True))[0]
                best = p_scores.argsort(descending=True)[:3]
                key_points = [pts[int(j)] for j in best]

            ranked.append({"group": g, "score": float(score), "key_points": key_points})

        # --- Does the cheatsheet cover this objective? ---
        cheat = None
        if line_vecs is not None:
            c_scores = util.cos_sim(obj_vecs[oi], line_vecs)[0]
            j = int(c_scores.argmax())
            cheat = {"line": lines[j], "score": float(c_scores[j]),
                     "covered": float(c_scores[j]) >= threshold}

        results.append({"objective": obj, "slides": ranked, "cheatsheet": cheat})
    return results