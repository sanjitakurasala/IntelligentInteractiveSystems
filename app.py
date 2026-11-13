# ---------------------------------------------------------------
# app.py: the Streamlit interface
# The student uploads their lecture slides and their cheatsheet.
# Later (Step 3.3) the app will check which slides the cheatsheet covers.
# ---------------------------------------------------------------

import streamlit as st              # Streamlit builds the web page from Python
from pypdf import PdfReader    
from covered import check_coverage     # used to read text out of a PDF cheatsheet

# Our own functions from IntelligentInteractiveSystems.py:
#   extract_slides -> reads each slide's number, title and text from the PDF
#   group_slides   -> merges repeated animation slides into one section
from IntelligentInteractiveSystems import extract_slides, group_slides

# Page heading
st.title("Slide Coverage Cheatsheet")

# ---------------- 1. Slides input ----------------
# A file upload box that only accepts PDFs.
# 'uploaded' is None until the student picks a file.
st.subheader("Your lecture slides")
uploaded = st.file_uploader("Upload lecture slides (PDF)", type="pdf")

# ---------------- 2. Cheatsheet input ----------------
# The student can either upload a file OR paste text.
st.subheader("Your cheatsheet")
cheat_file = st.file_uploader("Upload cheatsheet (PDF, TXT or MD)",
                              type=["pdf", "txt", "md"])
cheat_text = st.text_area("…or paste it here", height=200)

# Turn whichever input they used into one plain string: 'cheatsheet'
cheatsheet = ""
if cheat_file:                                   # a file was uploaded
    if cheat_file.name.endswith(".pdf"):
        # PDF: read every page's text and join them with new lines
        pages = PdfReader(cheat_file).pages
        cheatsheet = "\n".join((p.extract_text() or "") for p in pages)
    else:
        # TXT or MD: the file is already text, so decode the bytes
        cheatsheet = cheat_file.read().decode("utf-8", errors="ignore")
elif cheat_text.strip():                         # nothing uploaded, but text was pasted
    cheatsheet = cheat_text

# Confirm the cheatsheet loaded and show its length
if cheatsheet:
    st.success(f"Cheatsheet loaded ({len(cheatsheet.split())} words)")

# ---------------- 3. Slides and coverage ----------------
if uploaded:
    slides = extract_slides(uploaded)
    groups = group_slides(slides)
    st.subheader("Slide coverage")
    st.write(f"Found {len(slides)} slides → {len(groups)} sections")

    if not cheatsheet:
        st.info("Add your cheatsheet above to check coverage.")
    else:
        # Developer setting: how similar counts as 'covered'
        threshold = st.sidebar.slider("Match threshold", 0.2, 0.8, 0.45, 0.05)

        with st.spinner("Checking coverage…"):
            groups = check_coverage(groups, cheatsheet, threshold)

        summary = st.empty()            # counts get filled in after the list
        covered = skipped = cant = 0

        for g in groups:
            nums = g["numbers"]
            label = f"Slide {nums[0]}" if len(nums) == 1 else f"Slides {nums[0]}–{nums[-1]}"

            if g["status"] == "cant_check":
                cant += 1
                st.caption(f"⚠ {label}: {g['title']} (image only, can't check)")
                continue

            # Ticked = covered. The student can override by ticking or unticking.
            tag = "" if g["status"] == "covered" else "  :red[skipped]"
            ticked = st.checkbox(f"{label}: {g['title']}{tag}",
                                 value=(g["status"] == "covered"),
                                 key=f"cov_{nums[0]}_{g['status']}")
            covered += ticked
            skipped += not ticked

            # Show why: the slide text and its closest cheatsheet line
            with st.expander(f"Why? (similarity {g['score']:.2f})"):
                st.markdown(f"**Closest cheatsheet line:** {g['match']}")
                st.text(g["text"])

        with summary.container():
            c1, c2, c3 = st.columns(3)
            c1.metric("Covered", covered)
            c2.metric("Skipped", skipped)
            c3.metric("Can't check", cant)