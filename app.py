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
#   Header -> Sidebar settings -> Step 1 / Step 2 upload cards -> Two tabs:
#     Tab 1 "Coverage":            which slides the cheatsheet covered
#     Tab 2 "Learning objectives": every slide sorted under its LO
# =====================================================================

import io
import streamlit as st
from pypdf import PdfReader

from IntelligentInteractiveSystems import extract_slides, group_slides, render_pages
from covered import check_coverage
from objectives import find_objectives, assign_slides

# Must be the FIRST Streamlit command: browser tab title, icon, wide layout.
st.set_page_config(page_title="Slide Coverage", page_icon="📘",
                   layout="wide", initial_sidebar_state="expanded")

# Load our custom styling from style.css
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def html(markup):
    """Shortcut for drawing our own styled HTML."""
    st.markdown(markup, unsafe_allow_html=True)


def section_label(nums):
    """'Slide 5' for one slide, 'Slides 64–71' for a merged group."""
    return f"Slide {nums[0]}" if len(nums) == 1 else f"Slides {nums[0]}–{nums[-1]}"


def badge(text, kind):
    """A small coloured status pill. kind: cov | skip | na | edit"""
    return f'<span class="badge b-{kind}">{text}</span>'


@st.cache_data(show_spinner=False)
def load_deck(data):
    """Read the slides once per file and remember the result.
    Without caching, every click would re-read the whole PDF."""
    slides = extract_slides(io.BytesIO(data))
    groups = group_slides(slides)
    images = render_pages(data)
    return slides, groups, images


def read_cheatsheet(cheat_file, cheat_text):
    """Turn whichever cheatsheet input was used into ONE string."""
    if cheat_file:
        if cheat_file.name.endswith(".pdf"):
            return "\n".join((p.extract_text() or "") for p in PdfReader(cheat_file).pages)
        return cheat_file.read().decode("utf-8", errors="ignore")
    return cheat_text.strip()


def slide_grid(items, images, per_row=4):
    """Slide thumbnails in rows, each with its label and score."""
    for start in range(0, len(items), per_row):
        cols = st.columns(per_row)
        for col, it in zip(cols, items[start:start + per_row]):
            g = it["group"] if "group" in it else it
            nums = g["numbers"]
            cap = f"{section_label(nums)} · {g['title'][:38]}"
            if it.get("score") is not None:      # image-only slides have no score
                cap += f" · {it['score']:.2f}"
            if it.get("also"):
                cap += f" · also LO{it['also']}"
            with col:
                st.image(images[nums[-1] - 1], caption=cap)


# The student's own tick/untick decisions, kept across reruns.
# Key: (file, first slide number) -> True (covered) / False (skipped)
overrides = st.session_state.setdefault("overrides", {})


def remember_override(okey, widget_key):
    """Called when a tick box changes: store the student's decision."""
    overrides[okey] = st.session_state[widget_key]


# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------
html("""
<div class="hero">
  <div class="hero-left">
    <div class="mark">
      <svg viewBox="0 0 48 48" width="34" height="34" aria-hidden="true">
        <rect x="6" y="10" width="26" height="20" rx="3" fill="#BFDBFE"/>
        <rect x="14" y="16" width="26" height="20" rx="3" fill="#FFFFFF"/>
        <path d="M20 26l4 4 9-9" fill="none" stroke="#2563EB" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
    <div>
      <div class="eyebrow">Revision assistant</div>
      <div class="title">Slide <span>Coverage</span></div>
      <div class="tagline">Find what your AI cheatsheet left out of the lecture.</div>
      <div class="flow">
        <span class="flow-step"><b>1</b> Upload slides</span><span class="flow-arrow">→</span>
        <span class="flow-step"><b>2</b> Add your cheatsheet</span><span class="flow-arrow">→</span>
        <span class="flow-step"><b>3</b> See the gaps</span>
      </div>
    </div>
  </div>
  <div class="hero-right">
    <div class="peek">
      <div class="peek-row"><span>Signal detection</span><span class="badge b-cov">Covered</span></div>
      <div class="peek-row"><span>Cue integration</span><span class="badge b-skip">Skipped</span></div>
      <div class="peek-row"><span>Diagram slide</span><span class="badge b-na">Can't check</span></div>
    </div>
    <div class="chips"><span class="chip">Runs locally</span><span class="chip chip-blue">v1.0</span></div>
  </div>
</div>
""")


# ---------------------------------------------------------------------
# Sidebar: settings
# ---------------------------------------------------------------------
with st.sidebar:
    html('<div class="side-title">Detection settings</div>')
    threshold = st.slider("Match threshold", 0.2, 0.8, 0.45, 0.05,
                          help="How similar a slide must be to a cheatsheet line to count as covered. "
                               "Higher = stricter, flags more slides.")
    html('<div class="side-title">Learning objectives</div>')
    first_n = st.number_input("Objectives are on the first … slides", 1, 3, 1)
    min_sim = st.slider("Minimum relevance", 0.1, 0.6, 0.25, 0.05,
                        help="Slides below this go under 'Not linked'.")
    st.divider()
    if st.button("Reset my overrides",
                 help="Undo every tick or untick you made."):
        overrides.clear()
        st.rerun()


# ---------------------------------------------------------------------
# Step 1 and Step 2: upload cards
# ---------------------------------------------------------------------
col_slides, col_cheat = st.columns(2, gap="medium")

with col_slides:
    with st.container(border=True):
        html('<div class="step">Step 1</div><div class="step-title">Lecture slides</div>'
             '<div class="step-help">The PDF your lecturer shared. This is the reference.</div>')
        uploaded = st.file_uploader("Lecture slides (PDF)", type="pdf",
                                    label_visibility="collapsed")

with col_cheat:
    with st.container(border=True):
        html('<div class="step">Step 2</div><div class="step-title">Your cheatsheet</div>'
             '<div class="step-help">Upload or paste the cheatsheet you revise from.</div>')
        cheat_file = st.file_uploader("Cheatsheet", type=["pdf", "txt", "md"],
                                      label_visibility="collapsed")
        cheat_text = st.text_area("Paste cheatsheet", height=96,
                                  label_visibility="collapsed",
                                  placeholder="…or paste your cheatsheet here")

cheatsheet = read_cheatsheet(cheat_file, cheat_text)


# ---------------------------------------------------------------------
# Empty state: nothing uploaded yet
# ---------------------------------------------------------------------
if not uploaded:
    html("""
    <div class="empty">
      <div class="empty-title">Upload a lecture to get started</div>
      <div class="empty-text">You'll see which slides your cheatsheet covers, which it skips,
      and how the lecture splits by learning objective.</div>
      <div class="features">
        <div><b>Coverage check</b><span>Every slide marked covered, skipped or can't check</span></div>
        <div><b>Evidence</b><span>The slide beside the cheatsheet lines that matched it</span></div>
        <div><b>Objectives</b><span>Slides grouped under the lecture's learning objectives</span></div>
      </div>
    </div>
    """)
    st.stop()


# ---------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------
data = uploaded.getvalue()
slides, groups, images = load_deck(data)
file_key = f"{uploaded.name}:{len(data)}"

# ---- File card: what was loaded ----
ready = badge("Ready", "cov") if cheatsheet else badge("Add your cheatsheet", "na")
words = f" · cheatsheet {len(cheatsheet.split())} words" if cheatsheet else ""
html(f'''<div class="filecard"><div class="ficon">PDF</div>
<div class="fbody"><div class="fname">{uploaded.name}</div>
<div class="fmeta">{len(slides)} slides → {len(groups)} sections{words}</div></div>{ready}</div>''')

tab_cov, tab_obj = st.tabs(["Coverage", "Learning objectives"])

# =====================================================================
# TAB 1: COVERAGE
# =====================================================================
with tab_cov:
    if not cheatsheet:
        st.info("Add your cheatsheet in Step 2 to check coverage.")
    else:
        with st.spinner("Comparing your cheatsheet with the slides…"):
            groups = check_coverage(groups, cheatsheet, threshold)

        # Work out each section's final status: the AI's, unless the student overrode it
        for g in groups:
            okey = (file_key, g["numbers"][0])
            if g["status"] == "cant_check":
                g["final"] = "cant_check"
            else:
                ai_covered = g["status"] == "covered"
                g["final"] = "covered" if overrides.get(okey, ai_covered) else "skipped"
                g["edited"] = okey in overrides and overrides[okey] != ai_covered

        n_cov = sum(g["final"] == "covered" for g in groups)
        n_skip = sum(g["final"] == "skipped" for g in groups)
        n_na = sum(g["final"] == "cant_check" for g in groups)
        checked = n_cov + n_skip
        pct = round(100 * n_cov / checked) if checked else 0

        # ---- Summary cards (colour-coded) ----
        total = n_cov + n_skip + n_na
        html(f'''<div class="stats">
<div class="stat s-blue"><div class="stat-label">Coverage</div><div class="stat-value">{pct}%</div><div class="stat-sub">of sections that could be checked</div></div>
<div class="stat s-green"><div class="stat-label">Covered</div><div class="stat-value">{n_cov}</div><div class="stat-sub">in your cheatsheet</div></div>
<div class="stat s-red"><div class="stat-label">Skipped</div><div class="stat-value">{n_skip}</div><div class="stat-sub">to revise from the slides</div></div>
<div class="stat s-amber"><div class="stat-label">Can't check</div><div class="stat-value">{n_na}</div><div class="stat-sub">image-only slides</div></div>
</div>''')

        # ---- One bar split into covered / skipped / can't check ----
        def share(n):
            return f"{100 * n / total:.1f}%" if total else "0%"
        html(f'''<div class="stackbar"><span class="sb-g" style="width:{share(n_cov)}"></span><span class="sb-r" style="width:{share(n_skip)}"></span><span class="sb-a" style="width:{share(n_na)}"></span></div>
<div class="legend"><span><i class="dot g"></i>Covered</span><span><i class="dot r"></i>Skipped</span><span><i class="dot a"></i>Can't check</span></div>''')

        # ---- Filter (with counts) ----
        names = {"all": f"All ({total})", "skipped": f"Skipped ({n_skip})",
                 "covered": f"Covered ({n_cov})", "cant_check": f"Can't check ({n_na})"}
        choice = st.radio("Show", list(names), format_func=names.get,
                          horizontal=True, label_visibility="collapsed")
        wanted = None if choice == "all" else choice

        shown = [g for g in groups if wanted is None or g["final"] == wanted]
        if not shown:
            st.caption("Nothing to show for this filter.")

        # ---- One card per section ----
        for g in shown:
            nums = g["numbers"]
            label = section_label(nums)
            slide_img = images[nums[-1] - 1]
            okey = (file_key, nums[0])

            with st.container(border=True):
                c_tick, c_title, c_status = st.columns([0.06, 0.70, 0.24],
                                                       vertical_alignment="center")

                if g["final"] == "cant_check":
                    with c_tick:
                        html('<div class="na-dot">–</div>')
                    with c_title:
                        st.markdown(f"**{label}** · {g['title']}")
                    with c_status:
                        html(badge("Can't check", "na"))
                    with st.expander("View slide (image only, no text to compare)"):
                        st.image(slide_img)
                    continue

                # Tick = covered. The student can change it; the change is remembered.
                is_cov = g["final"] == "covered"
                wkey = f"cb_{file_key}_{nums[0]}_{int(is_cov)}"
                with c_tick:
                    st.checkbox(f"Covered: {label}", value=is_cov, key=wkey,
                                label_visibility="collapsed",
                                on_change=remember_override, args=(okey, wkey))
                with c_title:
                    st.markdown(f"**{label}** · {g['title']}")
                with c_status:
                    tags = badge("Covered", "cov") if is_cov else badge("Skipped", "skip")
                    if g.get("edited"):
                        tags += " " + badge("Edited by you", "edit")
                    html(f'<div class="right">{tags}<span class="score">{g["score"]:.2f}</span></div>')

                # ---- Compare panel ----
                with st.expander("Compare with cheatsheet"):
                    left, right = st.columns([3, 2], gap="medium")
                    with left:
                        st.image(slide_img, caption=f"Slide {nums[-1]}")
                    with right:
                        html('<div class="panel-title">Closest cheatsheet lines</div>')
                        for line, s in g["top_matches"]:
                            html(f'<div class="match"><span>{line}</span><span class="score">{s:.2f}</span></div>')
                    if g["points"]:
                        n_ok = sum(p["covered"] for p in g["points"])
                        html(f'<div class="panel-title">Points on this slide · {n_ok}/{len(g["points"])} covered</div>')
                        for p in g["points"]:
                            mark = '<span class="tick">✓</span>' if p["covered"] else '<span class="cross">✗</span>'
                            sub = f'<div class="sub">↳ {p["match"]} · {p["score"]:.2f}</div>' if p["covered"] else ""
                            html(f'<div class="point">{mark}<div>{p["text"]}{sub}</div></div>')
                    else:
                        st.caption("Mostly a diagram, so there are no text points to compare.")

# =====================================================================
# TAB 2: LEARNING OBJECTIVES
# =====================================================================
with tab_obj:
    detected = find_objectives(slides, first_n)

    with st.container(border=True):
        html('<div class="panel-title">Learning objectives</div>')
        st.caption(("Read from slide 1. " if first_n == 1 else f"Read from slides 1–{first_n}. ")
                   + "One per line; edit them if they're wrong." if detected else
                   "No objectives found on the first slides. Type them in, one per line.")
        obj_text = st.text_area("Learning objectives", value="\n".join(detected),
                                height=110, label_visibility="collapsed",
                                key=f"objs_{file_key}_{first_n}")
    objectives = [o.strip(" •-*\t") for o in obj_text.splitlines() if o.strip()]

    if objectives:
        with st.spinner("Sorting slides by learning objective…"):
            results, unlinked, no_text = assign_slides(
                objectives, groups, set(range(1, first_n + 1)),
                min_sim, cheatsheet, threshold)

        # ---- Overview cards ----
        cols = st.columns(len(results) + 1)
        for i, (col, r) in enumerate(zip(cols, results), start=1):
            n = len(r["slides"])
            col.metric(f"Objective {i}", f"{n} section{'' if n == 1 else 's'}")
        cols[-1].metric("Not linked", len(unlinked))

        # ---- One card per objective ----
        for i, r in enumerate(results, start=1):
            with st.container(border=True):
                c = r["cheatsheet"]
                status = ""
                if c:
                    status = (badge("Covered by cheatsheet", "cov") if c["covered"]
                              else badge("Not covered by cheatsheet", "skip"))
                html(f'<div class="lo-head"><span class="lo-num">LO{i}</span>'
                     f'<span class="lo-text">{r["objective"]}</span>{status}</div>')
                if c and c["covered"]:
                    st.caption(f"Closest cheatsheet line: {c['line']} ({c['score']:.2f})")
                elif c:
                    st.caption("Your cheatsheet doesn't cover this objective, so revise these slides directly.")
                if r["slides"]:
                    n = len(r["slides"])
                    st.caption(f"{n} section{'' if n == 1 else 's'}, in lecture order")
                    slide_grid(r["slides"], images)
                else:
                    st.caption("No slides matched this objective.")

        if unlinked:
            with st.expander(f"Not linked to any objective ({len(unlinked)})"):
                slide_grid(sorted(unlinked, key=lambda it: it["group"]["numbers"][0]), images)
        if no_text:
            with st.expander(f"Image only, couldn't sort ({len(no_text)})"):
                slide_grid(no_text, images)

html('<div class="footer">Runs entirely on your computer · no API key · your files are not uploaded anywhere</div>')