# ---------------------------------------------------------------
# app.py: the Streamlit interface
# The student uploads lecture slides and their cheatsheet.
# The app shows which slide sections (and which points on each slide)
# the cheatsheet covered, skipped, or couldn't be checked.
# ---------------------------------------------------------------

import streamlit as st
from pypdf import PdfReader

# Our own files:
#   IntelligentInteractiveSystems.py -> reading, grouping and rendering slides
#   covered.py                       -> the coverage checker (embeddings)
from IntelligentInteractiveSystems import extract_slides, group_slides, render_pages
from covered import check_coverage

st.title("Slide Coverage Cheatsheet")

# ---------------- 1. Slides input ----------------
st.subheader("Your lecture slides")
uploaded = st.file_uploader("Upload lecture slides (PDF)", type="pdf")

# ---------------- 2. Cheatsheet input ----------------
# The student can upload a file OR paste text
st.subheader("Your cheatsheet")
cheat_file = st.file_uploader("Upload cheatsheet (PDF, TXT or MD)",
                              type=["pdf", "txt", "md"])
cheat_text = st.text_area("…or paste it here", height=200)

# Turn whichever input they used into one plain string
cheatsheet = ""
if cheat_file:
    if cheat_file.name.endswith(".pdf"):
        pages = PdfReader(cheat_file).pages
        cheatsheet = "\n".join((p.extract_text() or "") for p in pages)
    else:
        cheatsheet = cheat_file.read().decode("utf-8", errors="ignore")
elif cheat_text.strip():
    cheatsheet = cheat_text

if cheatsheet:
    st.success(f"Cheatsheet loaded ({len(cheatsheet.split())} words)")

# ---------------- 3. Slides and coverage ----------------
if uploaded:
    slides = extract_slides(uploaded)               # individual slides
    groups = group_slides(slides)                   # animation builds merged
    images = render_pages(uploaded.getvalue())      # one PNG per slide (index 0 = slide 1)

    st.subheader("Slide coverage")
    st.write(f"Found {len(slides)} slides → {len(groups)} sections")

    if not cheatsheet:
        st.info("Add your cheatsheet above to check coverage.")
    else:
        # Developer setting: how similar counts as 'covered'
        threshold = st.sidebar.slider("Match threshold", 0.2, 0.8, 0.45, 0.05)

        with st.spinner("Checking coverage…"):
            groups = check_coverage(groups, cheatsheet, threshold)

        summary = st.empty()        # placeholder: counts are filled in after the list
        covered = skipped = cant = 0

        for g in groups:
            nums = g["numbers"]
            label = f"Slide {nums[0]}" if len(nums) == 1 else f"Slides {nums[0]}–{nums[-1]}"
            slide_img = images[nums[-1] - 1]   # last slide of a group = fully built animation

            # --- Image-only sections: can't check, but still show the slide ---
            if g["status"] == "cant_check":
                cant += 1
                with st.expander(f"⚠ {label}: {g['title']} (image only, can't check)"):
                    st.image(slide_img, caption=f"Slide {nums[-1]}")
                continue

            # --- Tick = covered. The student can tick or untick to override the AI. ---
            tag = "" if g["status"] == "covered" else "  :red[skipped]"
            ticked = st.checkbox(f"{label}: {g['title']}{tag}",
                                 value=(g["status"] == "covered"),
                                 key=f"cov_{nums[0]}_{g['status']}")
            covered += ticked
            skipped += not ticked

            # --- Compare panel: slide vs cheatsheet, point by point ---
            with st.expander(f"Compare (similarity {g['score']:.2f})"):
                left, right = st.columns([3, 2])

                with left:                                   # the real slide
                    st.image(slide_img, caption=f"Slide {nums[-1]}")

                with right:                                  # closest cheatsheet lines
                    st.markdown("**Closest cheatsheet lines**")
                    for line, s in g["top_matches"]:
                        st.markdown(f"- {line}  \n  <small>similarity {s:.2f}</small>",
                                    unsafe_allow_html=True)

                # Each point on the slide: covered or missed
                if g["points"]:
                    n_cov = sum(p["covered"] for p in g["points"])
                    st.markdown(f"**Points on this slide: {n_cov}/{len(g['points'])} covered**")
                    for p in g["points"]:
                        icon = "✅" if p["covered"] else "❌"
                        st.markdown(f"{icon} {p['text']}")
                        if p["covered"]:
                            st.caption(f"↳ matched: {p['match']} ({p['score']:.2f})")
                else:
                    st.caption("This slide is mostly a diagram, so there are no text points to compare.")

        # Summary counts at the top (they include the student's overrides)
        with summary.container():
            c1, c2, c3 = st.columns(3)
            c1.metric("Covered", covered)
            c2.metric("Skipped", skipped)
            c3.metric("Can't check", cant)