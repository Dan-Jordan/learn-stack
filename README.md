# LearnStack

A personal technical knowledge system built from the ground up — designed to help you capture, organize, retrieve, and grow what you know.

## The vision

The destination is a **RAG-powered learning system**: a knowledge base you can have a conversation with. You ask "what have I learned about dbt testing?" or "what errors have I run into with Docker Compose?" and the system retrieves the relevant notes you actually wrote, grounds its answer in them, and cites its sources. Not a generic LLM response — a response drawn from your own captured experience.

That capability — Retrieval-Augmented Generation, or RAG — is built on a simple foundation: your notes get split into chunks, those chunks get converted into vector embeddings that encode meaning, and when you ask a question the system finds the chunks whose meaning is closest to your question and hands them to the model as context. The result is answers that are grounded in what *you* know, not just what the model was trained on.

Getting there requires the foundation to exist first. You cannot do semantic search across an empty database. So LearnStack is built in phases, starting with the most basic useful thing — saving and retrieving notes — and adding intelligence only after the underlying system is solid and populated.

LearnStack is not a second brain or an AI agent. It is a backend application that earns its complexity over time. But it is being built toward something specific: a system where your saved knowledge actively helps you keep learning.

First, the basics have to work.

---

## What it does (Phase 1)

- Save technical notes with structured metadata
- Retrieve and search notes by keyword
- Organize by tool, topic, project, and note type
- Store everything in Postgres via a FastAPI backend

---

## Why it exists

Technical learning tends to scatter. Notes live in chat windows, code comments, scratch files, and browser tabs. The goal of LearnStack is to give that learning somewhere permanent and searchable to live — and to build it in a way that reinforces the exact skills the notes are about.

The project serves two purposes simultaneously:

**Practical** — a real tool for capturing and retrieving what you are learning about Python, FastAPI, dbt, Docker, Postgres, GitHub Actions, and data engineering.

**Educational** — a realistic application for practicing backend development, database modeling, API design, testing, and eventually RAG and semantic search.

---

## Tech stack

| Layer | Tool |
|---|---|
| Backend | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Schemas | Pydantic |
| Environment | Docker Compose |
| Testing | pytest |
| Version control | Git / GitHub |
| API docs | FastAPI Swagger / ReDoc |

Later additions: embeddings, pgvector, semantic search, optional frontend.

---

## Project phases

### Phase 1 — Basic notes app
Save, retrieve, update, delete, and keyword-search technical notes. Core CRUD. Postgres backend. Docker Compose. Tests.

**Done when:** I can create a note about `dbt seed`, save it, find it by searching `dbt`, and retrieve it cleanly.

### Phase 2 — Better organization
Add tags, filters, status, source, and confidence fields. Find all notes for a given tool or project. No AI required.

**Done when:** I can filter to all Docker notes, or all notes marked `needs_review`.

### Phase 3 — Search improvements
Improved keyword search, full-text search, sort/filter by date, pagination. Lay groundwork for Phase 4.

**Done when:** Searching `GitHub Actions secrets` returns relevant notes quickly.

### Phase 4 — Semantic search / RAG
This is what the whole project is building toward. Notes get split into chunks, embeddings are generated for each chunk and stored in Postgres via pgvector, and a semantic search layer enables question-answering across the full knowledge base. Answers are grounded in retrieved notes and include source citations — not generic LLM output, but responses drawn from what you actually wrote.

**Done when:** I can ask "what have I learned about dbt?" and get a grounded, cited answer drawn from my own saved notes.

### Phase 5 — Job search support
Save job postings, track applications, extract required skills, compare postings to saved notes, surface skill gaps.

**Done when:** I can identify recurring skills across saved roles and see which ones I have notes on.

### Phase 6 — Learning session workflow
AI-assisted workflow: start a learning session on a new topic, ask questions, generate a draft summary, review it, approve it, and save it as a technical note. Human approval required before anything enters the knowledge base.

**Done when:** A learning conversation produces a clean, reviewed technical note that links to related topics.

---

## Development philosophy

Build in small, working increments. Each step should produce something usable before moving to the next.

```
Build the smallest working version
→ Test it
→ Use it manually
→ Notice what is missing
→ Add the next most useful feature
```

Avoid over-engineering. If a feature does not help capture or retrieve learning, defer it.

---

## Getting started

> Setup instructions will be added as the project is built out.

```bash
# Clone the repo
git clone https://github.com/your-username/learnstack.git
cd learnstack

# Start services
docker compose up --build

# API docs available at
http://localhost:8000/docs
```

---

## Project boundary

The guiding question for every feature decision:

> What is the smallest useful addition that helps me retain and retrieve what I am learning, while strengthening relevant backend and data engineering skills?

If a feature does not answer that question, it waits.
