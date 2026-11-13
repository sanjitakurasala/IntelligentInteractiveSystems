# ---------------------------------------------------------------
# app.py: the Streamlit interface
# The student uploads their lecture slides and their cheatsheet.
# Later (Step 3.3) the app will check which slides the cheatsheet covers.
# ---------------------------------------------------------------

import streamlit as st              # Streamlit builds the web page from Python
from pypdf import PdfReader         # used to read text out of a PDF cheatsheet

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

# ---------------- 3. Show the slides ----------------
# Everything below only runs once a slides PDF has been uploaded.
if uploaded:
    slides = extract_slides(uploaded)    # list of individual slides
    groups = group_slides(slides)        # list of merged sections

    # Count sections with too little text for the checker to judge
    no_text = sum(1 for g in groups if not g["has_text"])

    st.subheader("Slides")
    st.write(f"Found {len(slides)} slides → {len(groups)} sections "
             f"({no_text} with too little text to check)")

    # One expandable row per section
    for g in groups:
        nums = g["numbers"]              # slide numbers in this section, e.g. [64, 65, …, 71]

        # Label it "Slide 5" for one slide or "Slides 64–71" for a group
        if len(nums) == 1:
            label = f"Slide {nums[0]}"
        else:
            label = f"Slides {nums[0]}–{nums[-1]}"

        # Add a warning for image-only sections
        flag = "" if g["has_text"] else "  ⚠ image only"

        # st.expander makes a row that opens when clicked
        with st.expander(f"{label}: {g['title']}{flag}"):
            st.text(g["text"] or "(no text found)")

    # Placeholder for Step 3.3: this is where coverage checking will go
    if cheatsheet:
        st.info("Both inputs loaded. Coverage checking comes in the next step.")