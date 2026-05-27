"""
import_notes.py — reads markdown files from notes-inbox/ and POSTs them to the LearnStack API.

Usage:
    python import_notes.py

Files starting with '_' are skipped (templates, drafts).
Successfully imported files are moved to notes-inbox/processed/.
"""

import re
import shutil
import urllib.request
import urllib.error
import json
from pathlib import Path

INBOX = Path("notes-inbox")
PROCESSED = INBOX / "processed"
API_URL = "http://localhost:8000/notes"

VALID_TYPES = {
    "technical_note", "command", "error_fix",
    "project_note", "concept", "question",
}


def parse_note(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")

    # Split frontmatter block
    if text.startswith("---"):
        parts = text.split("---", 2)
        fm_text = parts[1] if len(parts) >= 3 else ""
        body = parts[2].strip() if len(parts) >= 3 else text.strip()
    else:
        fm_text, body = "", text.strip()

    # Parse key: value pairs from frontmatter
    meta = {}
    for line in fm_text.strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip()
            if val:
                meta[key.strip()] = val

    # Title from frontmatter or first H1 heading
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = meta.get("title") or (title_match.group(1).strip() if title_match else path.stem)

    # Remove the H1 line from content so it isn't duplicated
    if title_match:
        body = body[title_match.end():].strip()

    note_type = meta.get("type", "technical_note")
    if note_type not in VALID_TYPES:
        raise ValueError(
            f"'{note_type}' is not a valid type. Choose from: {', '.join(sorted(VALID_TYPES))}"
        )

    payload = {
        "title": title,
        "content": body,
        "note_type": note_type,
    }
    for field in ("tool", "topic", "project"):
        if field in meta:
            payload[field] = meta[field]

    return payload


def post_note(payload: dict) -> str:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["id"]


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)

    files = sorted(f for f in INBOX.glob("*.md") if not f.name.startswith("_"))
    if not files:
        print("No notes found in notes-inbox/ (files starting with _ are skipped).")
        return

    success, failed = 0, 0
    for path in files:
        try:
            payload = parse_note(path)
            note_id = post_note(payload)
            shutil.move(str(path), str(PROCESSED / path.name))
            print(f"  saved  {path.name}  →  {note_id}")
            success += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"  ERROR  {path.name}: HTTP {e.code} — {body}")
            failed += 1
        except urllib.error.URLError:
            print(f"  ERROR  Cannot connect to {API_URL} — is the API running?")
            break
        except Exception as e:
            print(f"  ERROR  {path.name}: {e}")
            failed += 1

    print(f"\n{success} imported, {failed} failed.")


if __name__ == "__main__":
    main()
