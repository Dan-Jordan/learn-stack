---
description: Mid-phase session checkpoint — align docs to current progress, optional commit, resume prompt
argument-hint: [phase number, e.g. 17]
allowed-tools: Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(git branch:*)
---

## Context (gathered automatically, read-only)

- Current branch: !`git branch --show-current`
- Working tree state: !`git status --porcelain`
- Commits on this branch not on main: !`git log main..HEAD --oneline`
- Files changed vs main: !`git diff main...HEAD --stat`

## Task

Checkpoint progress on Phase $ARGUMENTS at the end of this session — the phase
is **not** finishing yet, just pausing. Work through these steps **in order**,
pausing after each so I can review before you continue:

1. **Align documentation with current progress — do not mark the phase
   Complete.** In CLAUDE.md, check off (`- [x]`) any planned-component
   checklist items that were actually built and verified this session; leave
   unfinished items unchecked. Update any Goal/Why/Built-so-far prose for the
   phase to reflect what's actually done vs. still planned. Do **not** change
   the "Current phase" heading/status and do **not** write a "Complete ✓"
   section or a Decisions-log/Follow-ups row for anything not yet finished —
   those are wrap-phase's job, once the phase actually closes.

2. **Consistency check.** Cross-check README.md against CLAUDE.md: tech stack
   tables, API surface, env var lists, and phase status must agree. Report
   any mismatches and fix them.

3. **Commit plan — only if there's something worth committing, and do NOT run
   anything.** Judge whether this session's changes are at a sensible commit
   point (working state, not mid-edit). If so, give me the git commands in
   order, with changes grouped into logically separate commits (e.g. code,
   tests, docs) where the diff warrants it. Use multiple -m flags for
   multi-line messages, never here-strings. I will run these myself. If
   nothing is commit-worthy yet, say so instead of forcing a commit plan.

4. **Resume prompt.** Write one self-contained prompt I can paste at the start
   of the next session, in a fenced code block so I can copy it directly.
   Cover: which phase/step we're on, what's done vs. still remaining, any
   decisions made this session that aren't in CLAUDE.md yet, and any open
   questions or blockers to pick up first. Write it so it stands alone without
   this session's conversation history. Also call out, separately, any
   note-worthy detail from this session (per CLAUDE.md's "What makes a good
   note" rubric — a gotcha, an exact error string, a workaround) that step 1
   didn't already fold into CLAUDE.md's Decisions log or phase prose — this is
   the safety net against it fading before wrap-phase's MCP note-capture step
   runs at the end of the phase.
