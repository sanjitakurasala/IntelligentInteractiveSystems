# IntelligentInteractiveSystems
AI Lectures Generated Cheatsheets 

## Scope
A student uploads lecture slides, gets an AI-generated cheatsheet and sees which slides the cheatsheet covered and which it skipped with a program which numbers the topics so you can detect which topics have been missed or added.

### In scope (to build)
- Upload lecture slides (PDF)
- Extract text from each slide
- Generate a cheatsheet with an LLM (one call, all slides)
- Check coverage slide by slide with an embedding model,
  separate from the generator
- Coverage panel: each slide marked covered / skipped
- Click a skipped slide to view its content

### Planned (not building now)
- Add a skipped slide back into the cheatsheet
- Weight slides by importance, not just covered/skipped
- LLM-based coverage checker as an alternative to embeddings
- User study with students

### Out of scope
- Measuring whether students learn more
- Support for formats other than PDF
