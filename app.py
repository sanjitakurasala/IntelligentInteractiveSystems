# ---------------------------------------------------------------
# app.py: the Streamlit interface (styled version)
# ---------------------------------------------------------------

import streamlit as st
from pypdf import PdfReader
from IntelligentInteractiveSystems import extract_slides, group_slides, render_pages
from covered import check_coverage

# Must be the first Streamlit command: wide layout, browser tab title
st.set_page_config(page_title="Slide Coverage", page_icon="📘", layout="wide")

# Load our custom styling from style.css
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ---------------- Header banner ----------------
st.markdown("""
<div class="hero">
  <h1>Slide Coverage Cheatsheet</h1>
  <p>See what your AI cheatsheet covered, what it skipped, and what it couldn't check.</p>
  <code>embeddings: all-MiniLM-L6-v2</code><code>runs locally</code><code>v0.3</code>
</div>
""", unsafe_allow_html=True)

# ---------------- Sidebar: developer settings ----------------
with st.sidebar:
    st.markdown('<div class="label">Settings</div>', unsafe_allow_html=True)
    threshold = st.slider("Match threshold", 0.2, 0.8, 0.45, 0.05,
                          help="How similar a slide must be to a cheatsheet line to count as covered.")
    st.markdown('<div class="label">How it works</div>', unsafe_allow_html=True)
    st.markdown('<p class="mono">1. slides → text + images<br>'
                '2. cheatsheet → lines<br>'
                '3. embed both → similarity<br>'
                '4. score ≥ threshold → covered</p>', unsafe_allow_html=True)

# ---------------- Inputs: two columns side by side ----------------
col_slides, col_cheat = st.columns(2, gap="large")

with col_slides:
    st.markdown('<div class="label">01 · Lecture slides</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload lecture slides (PDF)", type="pdf",
                                label_visibility="collapsed")

with col_cheat:
    st.markdown('<div class="label">02 · Your cheatsheet</div>', unsafe_allow_html=True)
    cheat_file = st.file_uploader("Upload cheatsheet (PDF, TXT or MD)",
                                  type=["pdf", "txt", "md"], label_visibility="collapsed")
    cheat_text = st.text_area("…or paste it here", height=140,
                              placeholder="…or paste your cheatsheet here")

# Turn whichever cheatsheet input was used into one string
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

    st.markdown('<div class="label">03 · Coverage</div>', unsafe_allow_html=True)
    st.caption(f"{len(slides)} slides → {len(groups)} sections"
               + (f" · cheatsheet {len(cheatsheet.split())} words" if cheatsheet else ""))

    if not cheatsheet:
        st.info("Add your cheatsheet to check coverage.")
    else:
        with st.spinner("Checking coverage…"):
            groups = check_coverage(groups, cheatsheet, threshold)

        summary = st.empty()          # summary cards are filled in after the list
        covered = skipped = cant = 0

        for g in groups:
            nums = g["numbers"]
            label = f"Slide {nums[0]}" if len(nums) == 1 else f"Slides {nums[0]}–{nums[-1]}"
            slide_img = images[nums[-1] - 1]

            # Image-only: can't check, but still show the slide
            if g["status"] == "cant_check":
                cant += 1
                with st.expander(f"{label} · {g['title']}  :orange-background[can't check]"):
                    st.image(slide_img, caption=f"Slide {nums[-1]}")
                continue

            # Tick = covered. The student can override.
            tag = (":green-background[covered]" if g["status"] == "covered"
                   else ":red-background[skipped]")
            ticked = st.checkbox(f"**{label}** · {g['title']}  {tag}",
                                 value=(g["status"] == "covered"),
                                 key=f"cov_{nums[0]}_{g['status']}")
            covered += ticked
            skipped += not ticked

            # Compare panel
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

        # Summary cards at the top, including the student's overrides
        checked = covered + skipped
        with summary.container():
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Covered", covered)
            c2.metric("Skipped", skipped)
            c3.metric("Can't check", cant)
            c4.metric("Coverage", f"{round(100 * covered / checked) if checked else 0}%")