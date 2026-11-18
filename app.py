# =====================================================================
# app.py
# ---------------------------------------------------------------------
# The STREAMLIT INTERFACE (what the student sees in the browser).
#
# How Streamlit works: this whole file runs from top to bottom every time
# the student does anything (uploads a file, ticks a box, moves a slider).
# Each st.something(...) call draws one thing on the page.
#
# Page layout:
#   Header -> Sidebar settings -> Two upload areas -> Two tabs:
#     Tab 1 "Coverage":            which slides the cheatsheet covered
#     Tab 2 "Learning objectives": every slide sorted under its LO
# =====================================================================

import streamlit as st
from pypdf import PdfReader          # to read a cheatsheet uploaded as PDF

# Our own files (see their comments for details)
from IntelligentInteractiveSystems import extract_slides, group_slides, render_pages
from covered import check_coverage
from objectives import find_objectives, assign_slides

# Must be the FIRST Streamlit command: browser tab title, icon, wide layout.
st.set_page_config(page_title="Slide Coverage", page_icon="📘", layout="wide")

# Load our custom styling. st.markdown with unsafe_allow_html=True lets us
# put raw HTML (here, a <style> tag) into the page.
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------
# Helper functions used further down
# ---------------------------------------------------------------------
def section_label(nums):
    """'Slide 5' for a single slide, 'Slides 64–71' for a merged group."""
    return f"Slide {nums[0]}" if len(nums) == 1 else f"Slides {nums[0]}–{nums[-1]}"


def slide_grid(items, images, per_row=4):
    """Show slide thumbnails in rows of `per_row`.

    items can be either:
      - result items from assign_slides() ({"group": ..., "score": ...})
      - plain sections from group_slides() (image-only list)
    """
    # range(0, len, 4) -> 0, 4, 8, ... = the start of each row
    for start in range(0, len(items), per_row):
        cols = st.columns(per_row)                   # 4 equal columns
        for col, it in zip(cols, items[start:start + per_row]):
            g = it["group"] if "group" in it else it  # handle both item types
            nums = g["numbers"]

            # Caption: "Slides 34–36 · Batch Norm · 0.52 · also LO2"
            cap = f"{section_label(nums)} · {g['title'][:40]}"   # [:40] shortens long titles
            if "score" in it:
                cap += f" · {it['score']:.2f}"                    # :.2f = 2 decimal places
            if it.get("also"):
                cap += f" · also LO{it['also']}"

            with col:
                # nums[-1] = last slide in the group (the fully built animation).
                # -1 because images[0] is slide 1.
                st.image(images[nums[-1] - 1], caption=cap)


# ---------------------------------------------------------------------
# Header banner (HTML so we can style it with style.css)
# ---------------------------------------------------------------------
st.markdown("""
<div class="hero">
  <h1>Slide Coverage Cheatsheet</h1>
  <p>See what your AI cheatsheet covered, what it skipped, and how the lecture splits by learning objective.</p>
  <code>embeddings: all-MiniLM-L6-v2</code><code>runs locally</code><code>v0.5</code>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------
# Sidebar: settings
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="label">Settings</div>', unsafe_allow_html=True)

    # slider(label, min, max, default, step)
    threshold = st.slider("Match threshold", 0.2, 0.8, 0.45, 0.05,
                          help="How similar text must be to count as covered.")

    # number_input(label, min, max, default)
    first_n = st.number_input("Objectives are on the first … slides", 1, 3, 1)

    min_sim = st.slider("Minimum relevance to an objective", 0.1, 0.6, 0.25, 0.05,
                        help="Slides below this go under 'Not linked'.")

    st.markdown('<div class="label">How it works</div>', unsafe_allow_html=True)
    st.markdown('<p class="mono">1. slides → text + images<br>'
                '2. cheatsheet / objectives → lines<br>'
                '3. embed all → similarity<br>'
                '4. compare and sort</p>', unsafe_allow_html=True)


# ---------------------------------------------------------------------
# Inputs: slides on the left, cheatsheet on the right
# ---------------------------------------------------------------------
col_slides, col_cheat = st.columns(2, gap="large")

with col_slides:
    st.markdown('<div class="label">01 · Lecture slides</div>', unsafe_allow_html=True)
    # 'uploaded' is None until a file is chosen.
    # label_visibility="collapsed" hides the label (we show our own above).
    uploaded = st.file_uploader("Upload lecture slides (PDF)", type="pdf",
                                label_visibility="collapsed")

with col_cheat:
    st.markdown('<div class="label">02 · Your cheatsheet (optional for objectives)</div>',
                unsafe_allow_html=True)
    cheat_file = st.file_uploader("Upload cheatsheet", type=["pdf", "txt", "md"],
                                  label_visibility="collapsed")
    cheat_text = st.text_area("…or paste it here", height=140,
                              placeholder="…or paste your cheatsheet here")

# Turn whichever cheatsheet input was used into ONE string.
cheatsheet = ""
if cheat_file:                                         # a file was uploaded
    if cheat_file.name.endswith(".pdf"):
        # PDF: join the text of every page
        cheatsheet = "\n".join((p.extract_text() or "")
                               for p in PdfReader(cheat_file).pages)
    else:
        # TXT/MD: the file is bytes, decode them into text
        cheatsheet = cheat_file.read().decode("utf-8", errors="ignore")
elif cheat_text.strip():                               # nothing uploaded, text pasted
    cheatsheet = cheat_text


# ---------------------------------------------------------------------
# Results (only once a slides PDF has been uploaded)
# ---------------------------------------------------------------------
if uploaded:
    slides = extract_slides(uploaded)              # individual slides
    groups = group_slides(slides)                  # animation builds merged
    images = render_pages(uploaded.getvalue())     # one PNG per slide

    st.caption(f"{len(slides)} slides → {len(groups)} sections"
               + (f" · cheatsheet {len(cheatsheet.split())} words" if cheatsheet else ""))

    # Two tabs; everything inside "with tab_x:" appears in that tab.
    tab_cov, tab_obj = st.tabs(["Coverage", "Learning objectives"])

    # =================================================================
    # TAB 1: COVERAGE
    # =================================================================
    with tab_cov:
        if not cheatsheet:
            st.info("Add your cheatsheet to check coverage.")
        else:
            # Spinner shows "Checking coverage…" while this runs.
            with st.spinner("Checking coverage…"):
                groups = check_coverage(groups, cheatsheet, threshold)

            # st.empty() reserves a spot at the top. We fill it with the
            # summary cards AFTER the loop, once we've counted everything
            # (including the student's tick overrides).
            summary = st.empty()
            covered = skipped = cant = 0

            for g in groups:
                nums = g["numbers"]
                label = section_label(nums)
                slide_img = images[nums[-1] - 1]

                # ---- Image-only: can't check, but still show the slide ----
                if g["status"] == "cant_check":
                    cant += 1
                    with st.expander(f"{label} · {g['title']}  :orange-background[can't check]"):
                        st.image(slide_img, caption=f"Slide {nums[-1]}")
                    continue                       # go to the next section

                # ---- Tick box: ticked = covered ----
                # :green-background[...] is Streamlit's coloured-label syntax.
                tag = (":green-background[covered]" if g["status"] == "covered"
                       else ":red-background[skipped]")

                # The key must be unique per box. Including the status means
                # that if the threshold changes the status, the box resets to
                # the new default. Otherwise the student's own tick is kept.
                ticked = st.checkbox(f"**{label}** · {g['title']}  {tag}",
                                     value=(g["status"] == "covered"),
                                     key=f"cov_{nums[0]}_{g['status']}")

                # True counts as 1 and False as 0, so these add up correctly.
                covered += ticked
                skipped += not ticked

                # ---- Compare panel: slide vs cheatsheet ----
                with st.expander(f"Compare · similarity {g['score']:.2f}"):
                    # [3, 2] = left column 3/5 wide, right column 2/5 wide
                    left, right = st.columns([3, 2], gap="medium")

                    with left:                     # the real slide
                        st.image(slide_img, caption=f"Slide {nums[-1]}")

                    with right:                    # 3 closest cheatsheet lines
                        st.markdown('<div class="label">Closest cheatsheet lines</div>',
                                    unsafe_allow_html=True)
                        for line, s in g["top_matches"]:
                            st.markdown(f"- {line}  \n  `{s:.2f}`")

                    # Each point on the slide: ✅ covered or ❌ missed
                    if g["points"]:
                        n_cov = sum(p["covered"] for p in g["points"])
                        st.markdown(f'<div class="label">Points on this slide · '
                                    f'{n_cov}/{len(g["points"])} covered</div>',
                                    unsafe_allow_html=True)
                        for p in g["points"]:
                            st.markdown(f"{'✅' if p['covered'] else '❌'} {p['text']}")
                            if p["covered"]:
                                st.caption(f"↳ {p['match']} · {p['score']:.2f}")
                    else:
                        st.caption("Mostly a diagram, so there are no text points to compare.")

            # ---- Fill in the summary cards reserved at the top ----
            checked = covered + skipped
            with summary.container():
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Covered", covered)
                c2.metric("Skipped", skipped)
                c3.metric("Can't check", cant)
                # "if checked else 0" avoids dividing by zero
                c4.metric("Coverage", f"{round(100 * covered / checked) if checked else 0}%")

    # =================================================================
    # TAB 2: LEARNING OBJECTIVES
    # =================================================================
    with tab_obj:
        # Read the LOs from the first 1-2 slides.
        detected = find_objectives(slides, first_n)

        st.markdown('<div class="label">Learning objectives (one per line)</div>',
                    unsafe_allow_html=True)
        st.caption(f"Read from slide{'s 1–' + str(first_n) if first_n > 1 else ' 1'}. "
                   "Edit them if they're wrong."
                   if detected else
                   "No objectives found on the first slides. Type them in.")

        # Editable box, pre-filled with the detected LOs.
        # The key includes the file name and first_n, so the box refills
        # when a different PDF is uploaded or the setting changes.
        obj_text = st.text_area("Learning objectives", value="\n".join(detected),
                                height=120, label_visibility="collapsed",
                                key=f"objs_{uploaded.name}_{first_n}")

        # One objective per non-empty line, without bullet symbols.
        objectives = [o.strip(" •-*\t") for o in obj_text.splitlines() if o.strip()]

        if objectives:
            with st.spinner("Sorting slides by learning objective…"):
                results, unlinked, no_text = assign_slides(
                    objectives, groups,
                    set(range(1, first_n + 1)),   # skip the LO slides, e.g. {1, 2}
                    min_sim, cheatsheet, threshold)

            # ---- Overview: number of sections per LO ----
            cols = st.columns(len(results) + 1)       # one per LO + "Not linked"
            for i, (col, r) in enumerate(zip(cols, results), start=1):
                col.metric(f"LO{i}", f"{len(r['slides'])} sections")
            cols[-1].metric("Not linked", len(unlinked))

            # ---- One block per LO ----
            for i, r in enumerate(results, start=1):
                st.markdown(f"### 🎯 LO{i}: {r['objective']}")

                # Cheatsheet status (only if a cheatsheet was given)
                c = r["cheatsheet"]
                if c:
                    if c["covered"]:
                        st.markdown(f":green-background[covered by cheatsheet] "
                                    f"↳ {c['line']} `{c['score']:.2f}`")
                    else:
                        st.markdown(":red-background[not covered by cheatsheet]: "
                                    "revise these slides directly")

                # All slides for this LO, in lecture order
                if r["slides"]:
                    st.caption(f"{len(r['slides'])} sections, in lecture order")
                    slide_grid(r["slides"], images)
                else:
                    st.caption("No slides matched this objective.")
                st.divider()                           # horizontal line

            # ---- Slides that didn't clearly match any LO ----
            if unlinked:
                with st.expander(f"Not linked to any objective ({len(unlinked)})"):
                    slide_grid(sorted(unlinked, key=lambda it: it["group"]["numbers"][0]),
                               images)

            # ---- Image-only slides (can't be sorted without text) ----
            if no_text:
                with st.expander(f"Image only, couldn't sort ({len(no_text)})"):
                    slide_grid(no_text, images)
