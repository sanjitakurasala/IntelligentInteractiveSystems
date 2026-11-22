# IntelligentInteractiveSystems

# Slide Coverage AI Cheatsheet

**README prose word count: 830** (code, commands, tables of file names and links not counted)

A Streamlit prototype that checks a student's AI-made revision cheatsheet against their own lecture slides. It marks each slide section as **covered**, **skipped** or **can't check**, and sorts every slide under the lecture's **learning objectives**.


**Submitted version:** release `v1.0` (commit `[hash]`)

![Architecture](docs/architecture.png)

---

## Project status

**Works**
- Upload lecture slides (PDF) and a cheatsheet (PDF, TXT, MD or pasted text)
- Slides are read, titles cleaned, animation builds merged into sections, and each slide rendered as an image
- **Coverage tab:** summary counts, a filter, and a covered / skipped / can't check card for each section
- **Compare panel:** slide image beside its 3 closest cheatsheet lines, with ✓ / ✗ for each point
- The student can tick or untick any section; counts update and the choice is remembered
- **Objectives tab:** objectives read from slide 1 (editable), every slide sorted under its best objective, uncovered objectives flagged
- Sidebar: match threshold, minimum relevance, reset overrides

**Simulated:** nothing; everything runs on real files.

**Unfinished**
- LLM accuracy check on request (similarity cannot tell if a matched line is wrong)
- Reading image only slides with a vision model
- Adding skipped topics back into the cheatsheet, with student approval
- Finding objectives in lectures that don't use "We will…" wording
- Generating a cheatsheet inside the app
- A user study with students

**Limitations:** similarity measures topic overlap, not correct explanation, so a passing mention can count as covered, no AI model to actually check the content is accurate

---

## Technology stack

| Technology | What it does |
|---|---|
| Python 3.10+ | Main language |
| Streamlit | Interface: uploads, tabs, checkboxes, panels |
| pypdf | Extracts text from PDFs |
| PyMuPDF (`fitz`) | Renders each slide as an image |
| sentence-transformers, `all-MiniLM-L6-v2` | **The AI component.** Embeds slides, cheatsheet lines and objectives; cosine similarity decides coverage and objective links. Runs locally |
| `style.css`, `.streamlit/config.toml` | Blue and white light theme |

**Undecided:** which LLM and vision model to use for the planned accuracy check.

---

## Running the project

No API key is needed. Requires Python 3.10 or later.

```bash
git clone https://github.com/sanjitakurasala/IntelligentInteractiveSystems.git
cd IntelligentInteractiveSystems
python -m venv .venv
# Windows: .venv\Scripts\activate   (use "py" if "python" isn't found)
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run app.py
```

The first run downloads the embedding model (about 90 MB).

**To try it:** upload a lecture PDF, paste a cheatsheet an AI chatbot (Claude, GPT...) using prompt make a single pdf cheatsheet, then open the Coverage and Objectives tabs.

**API keys:** none are used now. `.env.example` shows the variable the planned LLM check will read. A reviewer would copy it to `.env` and add their own key; `.env` and `.streamlit/secrets.toml` are in `.gitignore`, so keys are never committed.

| File | Purpose |
|---|---|
| `app.py` | Interface: uploads, both tabs, sidebar |
| `IntelligentInteractiveSystems.py` | Reads slides: text, titles, sections, images |
| `covered.py` | Coverage checker (section and point level) |
| `objectives.py` | Finds objectives and sorts slides under them |
| `style.css`, `.streamlit/config.toml` | Styling and theme |

---

## Development record

**1. Setup and scope** ([0e66c60](https://github.com/sanjitakurasala/IntelligentInteractiveSystems/commit/0e66c60), [6fe7c90](https://github.com/sanjitakurasala/IntelligentInteractiveSystems/commit/6fe7c90))
- Wrote the scope first; anything outside it became "planned"
- Set up `.gitignore` so keys and the virtual environment are never committed

**2. Reading slides** ([70ffe6c](https://github.com/sanjitakurasala/IntelligentInteractiveSystems/commit/70ffe6c))
- Testing on a 23-slide HCI deck showed "titles" that were page numbers or image links, and animation builds repeating one slide
- Added title filtering and merged consecutive same title slides into sections

**3. Student uploads their own cheatsheet** ([70ffe6c](https://github.com/sanjitakurasala/IntelligentInteractiveSystems/commit/70ffe6c))
- First planned to generate the cheatsheet with an LLM. Switched to uploading the student's own, because students use different AI tools and the checker is then separate from the generator

**4. Coverage checker** ([aef6e71](https://github.com/sanjitakurasala/IntelligentInteractiveSystems/commit/aef6e71))
- Chose a local embedding model, one section at a time, instead of asking an LLM to check its own summary
- Image only slides were being marked "skipped", so I added "can't check"
- Added tick boxes so the student can override the system

**5. Slide images and point-level checks** ([bdd7935](https://github.com/sanjitakurasala/IntelligentInteractiveSystems/commit/bdd7935))
- Extracted text was hard to read, so the panel shows the real slide
- Whole section scores hid missing points from the lectures, so each point is now checked separately

**6. Learning objectives** ([fde0d5d](https://github.com/sanjitakurasala/IntelligentInteractiveSystems/commit/fde0d5d), [ec6a84f](https://github.com/sanjitakurasala/IntelligentInteractiveSystems/commit/ec6a84f))
- First version showed only the top 3 slides per objective; changed to sort every slide
- Detection picked up slide 2 when the PDF lost its bullet symbols; it now reads objective wording on slide 1 only and leaves the box empty rather than guessing

**7. Interface redesign** ([64638e5](https://github.com/sanjitakurasala/IntelligentInteractiveSystems/commit/64638e5), [05c15e9](https://github.com/sanjitakurasala/IntelligentInteractiveSystems/commit/05c15e9))
- Summary cards, a red / amber / green status system and a coverage bar, so the result is clear at a glance
- Dark mode made text unreadable, so the theme is now fixed to light
- Fixed: ticks were lost when the page reloaded (now stored per file), and image-only slides crashed the objectives view

**What I checked:** after each change I ran the app on real lecture decks and compared its marks against the slides myself.

---

## AI assistance

I used **Claude (Anthropic)**.

**Asked it to help with:** Writing and debugging the Python code, adding comments that explain the code, fixing setup problems, diagrams briefly with report and readme but I worked on the report and readme mainly on my own.

**How I used or changed its suggestions**
- Key design changes were my decisions after testing: uploading the student's own cheatsheet, showing slide images, point level checks and sorting by learning objectives
- When objectives were read from the wrong slide, or only 3 slides were shown, I found the problem and had it changed
- I rejected some interface suggestions (for example a see through sidebar) and adjusted the styling to my preferences

**How I checked the results:** ran the app on real decks after each change, checked "skipped" and "covered" marks against the slides, asked for explanations of code before committing it, and checked report claims against the lecture slides.

---

## Additional files

- `docs/architecture.png`: application architecture diagram (also Figure 2 in the report)
- The report is submitted separately. No ZIP file is needed.
