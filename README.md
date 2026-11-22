# publish

A script that takes a markdown post and publishes it to the softwarecaptains.be blog (an Astro site) and prepares it for LinkedIn. The blog post is committed to the website repo on a new branch and opened as a pull request; merging it puts the post online. For LinkedIn, the post is converted to plain text, copied to your clipboard and LinkedIn opens in your browser.

## Dependencies

- [uv](https://docs.astral.sh/uv/) (`brew install uv`)
- `git` and the [GitHub CLI](https://cli.github.com/) (`gh`), logged in with push access to the website repo
- A local clone of [`tomklaasen/softwarecaptains-website`](https://github.com/tomklaasen/softwarecaptains-website)

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
| `WEBSITE_REPO`    | Path to the local clone of the website repo                 |

## Usage

```bash
# Pick the file with the oldest publish_date up to today from DRAFTS_DIR
# (or a random file without a publish_date if there is none)
uv run publish.py

# Use a specific file (relative to DRAFTS_DIR)
uv run publish.py my-post.md
```

## Workflow

1. The script prints the blog post (title + body).
2. Press Enter — the post is written to `site/src/content/blog/<slug>.md` in the website repo, committed on a new branch `blog/<slug>` (based on `origin/main`, in a temporary worktree, so your checkout is left alone), pushed, and opened as a pull request. The PR opens in your browser. Merging it to `main` puts the post online.
3. The script prints the LinkedIn post body.
4. Press Enter — the body is copied to your clipboard and LinkedIn opens in your browser. Paste and review before posting.
5. The markdown file is moved to `PUBLISHED_DIR`, with its `publish_date` set to today (added to the front matter if missing).

## File format

The post title is taken from the filename (without extension). The slug is derived from the title (lowercase, accents removed, other characters replaced by `-`); the script stops if that post or branch already exists. The blog post keeps its markdown and gets front matter with `title`, `slug`, `date` (now), `categories` (empty) and a `description` (the first paragraphs, cut at 155 characters, like the website's own import script). YAML front matter is optional and stripped from the body if present. An optional `publish_date` (ISO format, e.g. `2026-10-23`) determines which file is picked when no file is given: the one with the oldest `publish_date` up to and including today wins. Files with a `publish_date` in the future are skipped. Files without a `publish_date` are only picked (randomly) when no file has a `publish_date` up to today.

```markdown
---
publish_date: 2026-10-23
---

Your post content here...
```
