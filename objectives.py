# =====================================================================
# objectives.py
# ---------------------------------------------------------------------
# Splits the lecture's slides by LEARNING OBJECTIVE (LO).
#
#   find_objectives(slides) -> reads the LOs from the first 1-2 slides
#   assign_slides(...)      -> puts EVERY slide section under the LO it
#                              matches best, and checks whether the
#                              cheatsheet covers each LO
#
# Why: covered/skipped treats every slide as equally important.
# Learning objectives are the lecturer's own statement of what matters,
# so organising the slides by LO shows the student what to focus on.
# =====================================================================

from sentence_transformers import util
from covered import load_model, split_cheatsheet   # reuse the same model

# Characters PDFs commonly use as bullet points.
#  and  are PowerPoint "Symbol"/"Wingdings" bullets.
BULLETS = "•▪◦–-*"

# Words found on title slides that are NOT objectives
# (e.g. "Intelligent Interactive Systems · Week 2 · Lecture 04").
META = ("week", "lecture", "university", "intelligent interactive systems",
        "course-own", "diagram")


def _join_wrapped(text):
    """Join lines that the PDF split in half.

    A long bullet like "We will examine how perception and attention shape
    what people notice..." comes out of the PDF as two lines. The second
    starts with a lowercase letter ("people notice..."), so we know it
    continues the line before and join them back together.
    """
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue                         # ignore blank lines
        if lines and line[0].islower():
            lines[-1] += " " + line          # continuation -> join onto previous
        else:
            lines.append(line)               # a new line
    return lines


# How learning objectives usually start. A line starting with one of these
# is very likely an objective, even if the PDF lost its bullet symbol.
LO_STARTS = ("we will", "you will", "students will", "by the end", "you should",
             "learn", "understand", "explain", "describe", "compare", "apply",
             "analyse", "analyze", "evaluate", "identify", "use ", "design",
             "recognise", "recognize", "discuss", "examine")


def _objective_lines(slide):
    """Look at one slide and return two lists:
      worded  - lines worded like objectives ("We will examine...")
      bullets - other bullet points (used only if no worded lines are found)
    """
    worded, bullets = [], []
    for line in _join_wrapped(slide["text"]):       # rejoin lines the PDF split
        is_bullet = line[0] in BULLETS
        clean = line.lstrip(BULLETS).strip()         # remove any bullet symbol
        words = clean.split()

        # Skip the title, short fragments and course details ("Week 2 · Lecture 04")
        if len(words) < 5 or clean == slide["title"]:
            continue
        if len(words) < 10 and any(m in clean.lower() for m in META):
            continue

        if clean.lower().startswith(LO_STARTS):      # worded like an objective
            worded.append(clean)
        elif is_bullet:                              # just a bullet point
            bullets.append(clean)
    return worded, bullets


def find_objectives(slides, first_n=1):
    """Read the learning objectives from the first `first_n` slides.

    1. Go slide by slide. On the FIRST slide that has lines worded like
       objectives ("We will...", "Explain..."), return those and stop.
       This stops content from slide 2 being mixed in.
    2. If no slide has worded lines, use the first slide's bullet points.
    3. If neither is found, return nothing; the student types them in.
       (Better an empty box than the wrong text.)
    """
    for s in slides[:first_n]:
        worded, _ = _objective_lines(s)
        if worded:
            return worded

    for s in slides[:first_n]:
        _, bullets = _objective_lines(s)
        if bullets:
            return bullets

    return []


def assign_slides(objectives, groups, skip_numbers, min_sim=0.25,
                  cheatsheet="", threshold=0.45):
    """Put every slide section under its best-matching objective.

    objectives:   list of LO strings
    groups:       slide sections from group_slides()
    skip_numbers: slide numbers to leave out (the objectives slides themselves)
    min_sim:      below this, a slide isn't clearly about ANY objective
    cheatsheet:   optional, to check whether each LO is covered
    threshold:    similarity needed for the cheatsheet to "cover" an LO

    Returns three things:
      results  - one entry per LO: its text, its slides, cheatsheet status
      unlinked - slides that didn't clearly match any LO
      no_text  - image-only slides that can't be sorted
    """
    model = load_model()
    obj_vecs = model.encode(objectives, convert_to_tensor=True)  # one vector per LO

    # Leave out the objectives slides, then split by whether there's text.
    candidates = [g for g in groups if g["numbers"][0] not in skip_numbers]
    usable = [g for g in candidates if g["has_text"]]
    no_text = [g for g in candidates if not g["has_text"]]

    # One empty list per LO: {0: [], 1: [], ...}. Slides get added to these.
    buckets = {i: [] for i in range(len(objectives))}
    unlinked = []

    if usable:
        # One vector per slide section (title + all its text).
        sec_vecs = model.encode([g["title"] + "\n" + g["text"] for g in usable],
                                convert_to_tensor=True)

        # Table of scores: one ROW per section, one COLUMN per LO.
        # e.g. row for slide 7 might be [0.41, 0.22] -> closer to LO1.
        sims = util.cos_sim(sec_vecs, obj_vecs)

        for g, row in zip(usable, sims):
            # LO positions sorted from best match to worst, e.g. [0, 1]
            order = row.argsort(descending=True)
            best = int(order[0])
            score = float(row[best])
            item = {"group": g, "score": score, "also": None}

            # If the slide is almost as relevant to a second LO (within 0.05),
            # note it so the app can show "also LO2".
            # +1 because LOs are shown to the user as LO1, LO2 (not 0, 1).
            if len(objectives) > 1:
                second = int(order[1])
                if float(row[second]) >= min_sim and score - float(row[second]) < 0.05:
                    item["also"] = second + 1

            # Strong enough match -> goes under its best LO.
            # Too weak -> "Not linked" (e.g. references, Q&A slides).
            if score >= min_sim:
                buckets[best].append(item)
            else:
                unlinked.append(item)

    # ---- Does the cheatsheet cover each LO? ----
    lines = split_cheatsheet(cheatsheet) if cheatsheet else []
    line_vecs = model.encode(lines, convert_to_tensor=True) if lines else None

    results = []
    for i, obj in enumerate(objectives):
        cheat = None                                  # stays None if no cheatsheet
        if line_vecs is not None:
            c = util.cos_sim(obj_vecs[i], line_vecs)[0]   # LO vs every cheatsheet line
            j = int(c.argmax())                           # closest line
            cheat = {"line": lines[j], "score": float(c[j]),
                     "covered": float(c[j]) >= threshold}

        # Show each LO's slides in lecture order (by first slide number).
        slides_in_order = sorted(buckets[i], key=lambda it: it["group"]["numbers"][0])

        results.append({"objective": obj, "slides": slides_in_order, "cheatsheet": cheat})

    return results, unlinked, no_text