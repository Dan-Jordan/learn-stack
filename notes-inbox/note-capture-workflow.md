---
type: project_note
tool:
topic: workflow
project: learnstack
---

# Note capture workflow using markdown inbox

While the LearnStack API is not yet running, notes are written as markdown files
and stored in notes-inbox/ for later import.

To create a note, tell Claude Code "create a note about X". It writes a new file
to notes-inbox/ using _template.md as the format guide.

Each file has a frontmatter block at the top:
- type: one of concept, command, error_fix, technical_note, project_note, question
- tool, topic, project: optional metadata fields

The title comes from the first H1 heading in the file body. Everything below that
is the note content, written in plain prose or Markdown.

Once the API is running, import_notes.py reads all .md files in the inbox, posts
each one to POST /notes, and moves the file to notes-inbox/processed/ on success.
Files starting with _ are skipped (used for templates and drafts).

This workflow means notes can be captured now and the import becomes a natural
capstone exercise once the API is built.
