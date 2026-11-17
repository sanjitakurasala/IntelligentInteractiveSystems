# ---------------------------------------------------------------
# app.py: the Streamlit interface
# Tab 1: which slides the cheatsheet covered, skipped or couldn't check
# Tab 2: which slides answer each learning objective, and whether the
#        cheatsheet covers that objective
# ---------------------------------------------------------------

import streamlit as st
from pypdf import PdfReader
from IntelligentInteractiveSystems import extract_slides, group_slides, render_pages
from covered import check_coverage
from objectives import find_objectives, match_objectives

st.set_page_config(page_title="Slide Coverage", page_icon="📘", layout="wide")
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def section_label(nums):
    """'Slide 5' for one slide, 'Slides 64–71' for a group."""
    return f"Slide {nums[0]}" if len(nums) == 1 else f"Slides {nums[0]}–{nums[-1]}"


# ---------------- Header ----------------
st.markdown("""
<div class="hero">
  <h1>Slide Coverage Cheatsheet</h1>
  <p>See what your AI cheatsheet covered, what it skipped, and which slides matter most for each learning objective.</p>
  <code>embeddings: all-MiniLM-L6-v2</code><code>runs locally</code><code>v0.4</code>
</div>
""", unsafe_allow_html=True)

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown('<div class="label">Settings</div>', unsafe_allow_html=True)
    threshold = st.slider("Match threshold", 0.2, 0.8, 0.45, 0.05,
                          help="How similar text must be to count as covered.")
    top_k = st.slider("Slides per objective", 1, 5, 3)
    st.markdown('<div class="label">How it works</div>', unsafe_allow_html=True)
    st.markdown('<p class="mono">1. slides → text + images<br>'
                '2. cheatsheet / objectives → lines<br>'
                '3. embed all → similarity<br>'
                '4. rank and compare</p>', unsafe_allow_html=True)

# ---------------- Inputs ----------------
col_slides, col_cheat = st.columns(2, gap="large")
with col_slides:
    st.markdown('<div class="label">01 · Lecture slides</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload lecture slides (PDF)", type="pdf",
                                label_visibility="collapsed")
with col_cheat:
    st.markdown('<div class="label">02 · Your cheatsheet (optional for objectives)</div>',
                unsafe_allow_html=True)
    cheat_file = st.file_uploader("Upload cheatsheet", type=["pdf", "txt", "md"],
                                  label_visibility="collapsed")
    cheat_text = st.text_area("…or paste it here", height=140,
                              placeholder="…or paste your cheatsheet here")

cheatsheet = ""
if cheat_file:
    if cheat_file.name.endswith(".pdf"):
        cheatsheet = "\n".join((p.extract_text() or "") for p in PdfReader(cheat_file).pages)
    else:
        cheatsheet = cheat_file.read().decode("utf-8", errors="ignore")
elif cheat_text.strip():
    cheatsheet = cheat_text

# ---------------- Results ----------------
if uploaded:
    slides = extract_slides(uploaded)
    groups = group_slides(slides)
    images = render_pages(uploaded.getvalue())
    st.caption(f"{len(slides)} slides → {len(groups)} sections"
               + (f" · cheatsheet {len(cheatsheet.split())} words" if cheatsheet else ""))

    tab_cov, tab_obj = st.tabs(["Coverage", "Learning objectives"])

    # ======================= TAB 1: COVERAGE =======================
    with tab_cov:
        if not cheatsheet:
            st.info("Add your cheatsheet to check coverage.")
        else:
            with st.spinner("Checking coverage…"):
                groups = check_coverage(groups, cheatsheet, threshold)

            summary = st.empty()
            covered = skipped = cant = 0

            for g in groups:
                nums = g["numbers"]
                label = section_label(nums)
                slide_img = images[nums[-1] - 1]

                if g["status"] == "cant_check":
                    cant += 1
                    with st.expander(f"{label} · {g['title']}  :orange-background[can't check]"):
                        st.image(slide_img, caption=f"Slide {nums[-1]}")
                    continue

                tag = (":green-background[covered]" if g["status"] == "covered"
                       else ":red-background[skipped]")
                ticked = st.checkbox(f"**{label}** · {g['title']}  {tag}",
                                     value=(g["status"] == "covered"),
                                     key=f"cov_{nums[0]}_{g['status']}")
                covered += ticked
                skipped += not ticked

                with st.expander(f"Compare · similarity {g['score']:.2f}"):
                    left, right = st.columns([3, 2], gap="medium")
                    with left:
                        st.image(slide_img, caption=f"Slide {nums[-1]}")
                    with right:
                        st.markdown('<div class="label">Closest cheatsheet lines</div>',
                                    unsafe_allow_html=True)
                        for line, s in g["top_matches"]:
                            st.markdown(f"- {line}  \n  `{s:.2f}`")
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

            checked = covered + skipped
            with summary.container():
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Covered", covered)
                c2.metric("Skipped", skipped)
                c3.metric("Can't check", cant)
                c4.metric("Coverage", f"{round(100 * covered / checked) if checked else 0}%")

    # =================== TAB 2: LEARNING OBJECTIVES ===================
    with tab_obj:
        detected = find_objectives(slides)
        st.markdown('<div class="label">Learning objectives (one per line)</div>',
                    unsafe_allow_html=True)
        if detected:
            st.caption("Detected from your slides. Edit them if they're wrong.")
        else:
            st.caption("No objectives slide found. Type or paste them from the module page.")

        obj_text = st.text_area("Learning objectives", value="\n".join(detected),
                                height=140, label_visibility="collapsed",
                                key=f"objs_{uploaded.name}",
                                placeholder="Explain how batch normalisation works\n"
                                            "Compare upsampling methods")
        objectives = [o.strip(" •-*\t") for o in obj_text.splitlines() if o.strip()]

        if objectives:
            with st.spinner("Finding the most relevant slides…"):
                results = match_objectives(objectives, groups, cheatsheet, top_k, threshold)

            for r in results:
                st.markdown(f"### 🎯 {r['objective']}")

                # Does the cheatsheet cover this objective?
                c = r["cheatsheet"]
                if c:
                    if c["covered"]:
                        st.markdown(f":green-background[covered by cheatsheet] "
                                    f"↳ {c['line']} `{c['score']:.2f}`")
                    else:
                        st.markdown(":red-background[not covered by cheatsheet]: "
                                    "revise these slides directly")

                # Most relevant slides, ranked left to right
                cols = st.columns(len(r["slides"]))
                for rank, (col, s) in enumerate(zip(cols, r["slides"]), start=1):
                    nums = s["group"]["numbers"]
                    with col:
                        st.image(images[nums[-1] - 1],
                                 caption=f"#{rank} · {section_label(nums)} · relevance {s['score']:.2f}")

                # Answer built from the slides' own words
                st.markdown('<div class="label">What the slides say</div>',
                            unsafe_allow_html=True)
                for s in r["slides"]:
                    nums = s["group"]["numbers"]
                    for p in s["key_points"][:2]:
                        st.markdown(f"- {p}  `{section_label(nums)}`")
                st.divider()