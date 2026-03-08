# publish

A script that takes a markdown post and prepares it for publishing to a Squarespace blog and LinkedIn. It converts the markdown to plain text, copies it to your clipboard, and opens the relevant pages in your browser.

## Dependencies

- Python 3
- [python-dotenv](https://pypi.org/project/python-dotenv/)

```bash
pip install python-dotenv
```

## Setup

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable       | Description                                                    |
|----------------|----------------------------------------------------------------|
| `DRAFTS_DIR`   | Directory containing markdown files ready to publish           |
| `PUBLISHED_DIR`| Directory where files are moved after the script runs          |

## Usage

```bash
# Pick a random file from DRAFTS_DIR
python publish.py

# Use a specific file (relative to DRAFTS_DIR)
python publish.py my-post.md
```

## Workflow

1. The script prints the blog post (title + body) and copies it to your clipboard.
2. Press Enter — Squarespace opens in your browser. Paste the title and body.
3. The script prints the LinkedIn post and copies it to your clipboard.
4. Press Enter — LinkedIn opens in your browser. Paste and review before posting.
5. The markdown file is moved to `PUBLISHED_DIR`.

## File format

The post title is taken from the filename (without extension). YAML front matter is optional and stripped from the body if present.

```markdown
---
any: metadata
---

Your post content here...
```
