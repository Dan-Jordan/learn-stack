---
description: End-of-phase wrap-up — docs, consistency check, commit plan, PR text, cleanup
argument-hint: [phase number, e.g. 17]
allowed-tools: Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(git branch:*)
---

## Context (gathered automatically, read-only)

- Current branch: !`git branch --show-current`
- Working tree state: !`git status --porcelain`
- Commits on this branch not on main: !`git log main..HEAD --oneline`
- Files changed vs main: !`git diff main...HEAD --stat`

## Task

Wrap up Phase $ARGUMENTS. Work through these steps **in order**, pausing after
each so I can review before you continue:

1. **Update documentation for the current phase.** Update CLAUDE.md: mark the
   phase Complete with the standard section format (Goal / Built / Verified /
   Design decisions / Risks-gotchas), update the "Current phase" section, add
   any new rows to the Decisions log and Follow-ups tables. Update README.md
   to match (phases table, any new setup steps or env vars).

2. **Consistency check.** Cross-check README.md against CLAUDE.md: tech stack
   tables, API surface, env var lists, and phase status must agree. Report any
   mismatches and fix them.

3. **Archive the completed phase.** Move the full "Phase $ARGUMENTS — Complete ✓"
   section out of CLAUDE.md into `docs/phases/phase-$ARGUMENTS.md` — **verbatim,
   no summarizing or rewording** — with the same archive header the existing
   files there use. Add the phase's line to CLAUDE.md's "Completed phase
   archives" list and fix any "see the Phase $ARGUMENTS section below"
   cross-references. Before moving, confirm every design decision and gotcha in
   the section has a corresponding Decisions log row or Follow-ups entry — add
   any that are missing.

4. **Capture RAG notes via the MCP server.** From what was just archived (the
   phase's Decisions log rows and Follow-ups/gotchas confirmed in step 3),
   identify what's genuinely worth capturing per CLAUDE.md's "What makes a
   good note" rubric — project-specific decisions and their *why*, gotchas
   tied to this project's exact setup, anything that will fade (exact env var
   names, error strings, workarounds). Skip anything generic/tutorial-like.
   Before staging each candidate, call `search_notes` to check whether a
   similar note already exists (by phase, tool, or topic) so the same
   decision or gotcha isn't captured twice. For each note that clears the
   bar, call `create_note` (stages into `pending_notes`, unembedded) with
   `project: learnstack` and an appropriate `tool`/`topic`. Prefer several
   narrow notes over one giant phase-summary note. Tell me what you staged
   and why — I'll review, edit, and approve from the Pending tab. If nothing
   in the phase clears the bar, say so and skip this step.

5. **Commit plan — do NOT run anything.** Give me the git commands in order,
   with changes grouped into logically separate commits (e.g. code, tests,
   docs) where the diff warrants it. Use multiple -m flags for multi-line
   messages, never here-strings. I will run these myself.

6. **PR title and description — do NOT run anything..** Follow the style of
   merged PRs in this repo (see git log): title like "Phase N — short summary",
   description covering what/why, design decisions worth a reviewer's attention,
   and test results.

7. **Local cleanup — do NOT run anything.** Give me the post-merge commands:
   switch to main, pull, delete the local branch, prune remote-tracking refs.
