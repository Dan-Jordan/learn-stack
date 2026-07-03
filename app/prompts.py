"""Shared prompt assets for the notes tools.

These are the model-facing *words* — tool descriptions and system-prompt prose — kept in one
place so the surfaces that expose the notes tools (the /chat agent loop in app/assistant.py,
the /draft agent in app/agent.py, and the MCP server) can't drift.

Only the genuinely shared parts live here. search_notes is read-only and identical everywhere,
so the whole tool is shared. For create_note, only the *trigger* (when to call) and the
note-quality *policy* (what makes a note worth keeping) are shared; each surface supplies its
own create_note *behavior* sentence (how it persists) — /chat proposes an unsaved draft, the
MCP server stages a pending row — because those genuinely differ. Share the contract and the
policy; keep surface-specific behavior per surface.

The note *data contract* (create_note's input schema, which mirrors the NoteCreate model) is
deliberately NOT here — it lives in app/schemas/note.py next to NoteCreate, so the two views
of the note shape stay adjacent and visibly can't drift. This file is prose; that is a schema.
"""

# search_notes behaves identically on every surface — shared verbatim (name, description, schema).
SEARCH_NOTES_TOOL = {
    "name": "search_notes",
    "description": (
        "Search the user's saved technical notes by meaning (semantic search) and return "
        "the most relevant ones. Call this when the user asks a question their past notes "
        "might answer, or asks what they've written about a topic."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language search query describing what to find",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of notes to return (default 5)",
            },
        },
        "required": ["query"],
    },
}

# When to call create_note — the trigger condition, shared by every surface exposing the tool.
CREATE_NOTE_TRIGGER = "Call this when the user asks to capture, save, or note something."

# What makes a note worth keeping — editorial policy, shared across surfaces. In /chat this
# rides in the system prompt; the MCP server can't set the host's system prompt, so it rides
# on the create_note tool description there instead.
NOTE_QUALITY_GUIDANCE = (
    "Prioritize content worth retrieving later: project-specific facts, configs, "
    "gotchas, errors and their fixes, and decisions with the reasoning behind them — the kind "
    "of detail that fades from memory and would otherwise be re-debugged or re-decided. Trim "
    "general concept explanations the user already understands or could easily re-look-up."
)
