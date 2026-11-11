# publish

A script that takes a markdown post and prepares it for publishing to a Squarespace blog and LinkedIn. It converts the markdown to plain text, copies it to your clipboard, and opens the relevant pages in your browser.

## Dependencies

- [uv](https://docs.astral.sh/uv/) (`brew install uv`)

Dependencies are declared in `pyproject.toml`. Create the virtual environment (`.venv`) with:

```bash
uv sync
```

## Setup

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable          | Description                                                 |
|-------------------|-------------------------------------------------------------|
| `DRAFTS_DIR`      | Directory containing markdown files ready to publish        |
| `PUBLISHED_DIR`   | Directory where files are moved after the script runs       |
| `SQUARESPACE_URL` | URL of the Squarespace blog editor page                     |

## Usage

```bash
# Pick the file with the oldest publish_date up to today from DRAFTS_DIR
# (or a random file without a publish_date if there is none)
uv run publish.py

# Use a specific file (relative to DRAFTS_DIR)
uv run publish.py my-post.md
```

## Workflow

1. The script prints the blog post (title + body) and copies it to your clipboard.
2. Press Enter — Squarespace opens in your browser. Paste the title and body.
3. The script prints the LinkedIn post body and copies it to your clipboard.
4. Press Enter — LinkedIn opens in your browser. Paste and review before posting.
5. The markdown file is moved to `PUBLISHED_DIR`, with its `publish_date` set to today (added to the front matter if missing).

## File format

The post title is taken from the filename (without extension). YAML front matter is optional and stripped from the body if present. An optional `publish_date` (ISO format, e.g. `2026-10-23`) determines which file is picked when no file is given: the one with the oldest `publish_date` up to and including today wins. Files with a `publish_date` in the future are skipped. Files without a `publish_date` are only picked (randomly) when no file has a `publish_date` up to today.

```markdown
---
publish_date: 2026-10-23
---

Your post content here...
```
