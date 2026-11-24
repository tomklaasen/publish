#!/usr/bin/env python3

import sys
import re
import json
import random
import tempfile
import unicodedata
from datetime import date, datetime, timezone
import shutil
import subprocess
import webbrowser
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent / '.env')

LINKEDIN_URL = "https://www.linkedin.com/feed/"
BLOG_DIR = Path('site/src/content/blog')
IMAGE_DIR = Path('site/public/blog-beelden')
OBSIDIAN_EMBED = re.compile(r'!\[\[([^\]|]+)(?:\|([^\]]*))?\]\]')


def parse_front_matter(content):
    if not content.startswith('---'):
        return {}, content
    end = content.find('---', 3)
    if end == -1:
        return {}, content
    front_matter = content[3:end].strip()
    body = content[end + 3:].strip()
    metadata = {}
    for line in front_matter.splitlines():
        if ':' in line:
            key, _, value = line.partition(':')
            metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, body


def markdown_to_text(md):
    # Remove fenced code blocks (keep content)
    text = re.sub(r'```[^\n]*\n([\s\S]*?)```', r'\1', md)
    # Remove inline code
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Convert headers to plain text
    text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'___(.+?)___', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    # Convert links to plain text
    text = re.sub(r'!\[[^\]]*\]\([^\)]+\)', '', text)  # images
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # links
    # Convert list markers
    text = re.sub(r'^[\*\-\+]\s+', '• ', text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Collapse excess blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def copy_to_clipboard(text):
    subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
    print("[Copied to clipboard]")


def separator(title):
    bar = '=' * 60
    print(f"\n{bar}")
    print(f"  {title}")
    print(f"{bar}\n")


def slugify(title):
    text = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def plain_text(md):
    # Same as platteTekst() in the website repo (site/src/lib/tekst.mjs)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', md)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[*_`#>]', '', text)
    text = re.sub(r'\\([\\\[\]().\-!])', r'\1', text)
    return re.sub(r'\s+', ' ', text).strip()


def make_description(md, minimum=100, maximum=155):
    # Same as inkorten(eersteAlineas(md, 100), 155) in the website repo
    text = ''
    for block in re.split(r'\n{2,}', md):
        if re.match(r'^\s*(!\[|#|<|\[!|:::)', block):
            continue
        text = f"{text} {plain_text(block)}".strip()
        if len(text) >= minimum:
            break
    if len(text) <= maximum:
        return text
    short = text[:maximum - 1]
    return re.sub(r'[\s,;:.–-]+$', '', short[:short.rfind(' ')]) + '…'


def find_attachment(name, root):
    """Find an Obsidian attachment by file name anywhere under root, like Obsidian does."""
    matches = sorted(p for p in root.rglob(Path(name).name) if p.is_file())
    if not matches:
        print(f"Error: image '{name}' not found under {root}")
        sys.exit(1)
    return matches[0]


def convert_images(body, slug, root):
    """Replace Obsidian embeds (![[image.png]]) with markdown images.

    Returns the new body and a list of (source path, file name) to copy to IMAGE_DIR / slug.
    """
    images = []

    def replace(match):
        source = find_attachment(match.group(1).strip(), root)
        name = slugify(source.stem) + source.suffix.lower()
        images.append((source, name))
        alt = (match.group(2) or '').strip()
        if re.fullmatch(r'\d+(x\d+)?', alt):  # ![[image.png|300]] is a width, not alt text
            alt = ''
        return f"![{alt}](/{IMAGE_DIR.relative_to('site/public')}/{slug}/{name})"

    return OBSIDIAN_EMBED.sub(replace, body), images


def blog_post(title, body, now=None):
    now = now or datetime.now(timezone.utc)
    frontmatter = {
        'title': title,
        'slug': slugify(title),
        'date': now.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
        'categories': [],
        'description': make_description(body),
    }
    lines = []
    for key, value in frontmatter.items():
        if isinstance(value, list):
            value = '[' + ', '.join(json.dumps(v, ensure_ascii=False) for v in value) + ']'
        else:
            value = json.dumps(value, ensure_ascii=False)
        lines.append(f"{key}: {value}")
    return frontmatter['slug'], "---\n" + "\n".join(lines) + "\n---\n\n" + body.strip() + "\n"


def run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {' '.join(cmd)} failed:\n{result.stderr.strip() or result.stdout.strip()}")
        sys.exit(1)
    return result.stdout.strip()


def publish_to_website(title, body, attachments_root, create_pr=True):
    """Write the post to the website repo on a new branch, push it and open a PR. Returns the PR URL."""
    website_repo = os.getenv('WEBSITE_REPO')
    if not website_repo:
        print("Error: WEBSITE_REPO is not set in .env")
        sys.exit(1)
    repo = Path(website_repo).expanduser()
    slug = slugify(title)
    if not slug:
        print(f"Error: cannot make a slug from title '{title}'")
        sys.exit(1)
    body, images = convert_images(body, slug, attachments_root)
    _, post = blog_post(title, body)
    branch = f"blog/{slug}"
    run(['git', 'fetch', 'origin', 'main'], repo)
    if run(['git', 'ls-tree', '--name-only', 'origin/main', str(BLOG_DIR / f"{slug}.md")], repo):
        print(f"Error: {BLOG_DIR / f'{slug}.md'} already exists on main in {repo}")
        sys.exit(1)
    if run(['git', 'branch', '--list', branch], repo):
        print(f"Error: branch '{branch}' already exists in {repo}")
        sys.exit(1)

    # A separate worktree, so the checkout in WEBSITE_REPO is left alone.
    worktree = Path(tempfile.mkdtemp(prefix='publish-')) / slug
    run(['git', 'worktree', 'add', '--no-track', '-b', branch, str(worktree), 'origin/main'], repo)
    try:
        target = worktree / BLOG_DIR / f"{slug}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(post, encoding='utf-8')
        print(f"Written: {BLOG_DIR / target.name} on branch {branch}")
        run(['git', 'add', str(target)], worktree)
        for source, name in images:
            image = worktree / IMAGE_DIR / slug / name
            image.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, image)
            print(f"Copied: {source.name} -> {IMAGE_DIR / slug / name}")
            run(['git', 'add', str(image)], worktree)
        run(['git', 'commit', '-m', f"Blogpost: {title}"], worktree)
        if not create_pr:
            return None
        run(['git', 'push', '-u', 'origin', branch], worktree)
        return run(['gh', 'pr', 'create', '--base', 'main', '--head', branch,
                    '--title', f"Blogpost: {title}",
                    '--body', f"Nieuwe blogpost `{slug}`, aangemaakt met publish.py. Mergen zet hem online."],
                   worktree)
    finally:
        subprocess.run(['git', 'worktree', 'remove', '--force', str(worktree)], cwd=repo, capture_output=True)
        shutil.rmtree(worktree.parent, ignore_errors=True)


def get_publish_date(path):
    metadata, _ = parse_front_matter(path.read_text(encoding='utf-8'))
    value = metadata.get('publish_date')
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        print(f"Warning: invalid publish_date '{value}' in {path.name} — ignored.")
        return None


def set_publish_date(content, value):
    line = f"publish_date: {value}"
    if content.startswith('---'):
        end = content.find('---', 3)
        if end != -1:
            front_matter = content[3:end]
            pattern = re.compile(r'^publish_date\s*:.*$', flags=re.MULTILINE)
            if pattern.search(front_matter):
                front_matter = pattern.sub(line, front_matter, count=1)
            else:
                front_matter = front_matter.rstrip('\n') + f"\n{line}\n"
            return f"---{front_matter}{content[end:]}"
    return f"---\n{line}\n---\n\n{content}"


def pick_file():
    drafts_dir = os.getenv('DRAFTS_DIR')
    if not drafts_dir:
        print("Error: DRAFTS_DIR is not set in .env")
        sys.exit(1)
    drafts_path = Path(drafts_dir).expanduser()
    files = list(drafts_path.glob('*.md'))
    if not files:
        print(f"Error: no markdown files found in {drafts_path}")
        sys.exit(1)
    today = date.today()
    dated = []
    undated = []
    for f in files:
        publish_date = get_publish_date(f)
        if publish_date is None:
            undated.append(f)
        elif publish_date.date() <= today:
            dated.append((publish_date, f))
    if dated:
        publish_date, chosen = min(dated, key=lambda item: item[0])
        print(f"Selected oldest publish_date ({publish_date.date()}): {chosen.name}")
        return chosen
    if not undated:
        print(f"Error: no files with a publish_date up to today or without a publish_date in {drafts_path}")
        sys.exit(1)
    chosen = random.choice(undated)
    print(f"Randomly selected: {chosen.name}")
    return chosen


def main():
    if len(sys.argv) == 1:
        filepath = pick_file()
    elif len(sys.argv) == 2:
        drafts_dir = os.getenv('DRAFTS_DIR')
        if not drafts_dir:
            print("Error: DRAFTS_DIR is not set in .env")
            sys.exit(1)
        filepath = Path(drafts_dir).expanduser() / sys.argv[1]
    else:
        print(f"Usage: python {sys.argv[0]} [markdown_file]")
        sys.exit(1)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: file '{filepath}' not found.")
        sys.exit(1)

    title = Path(filepath).stem
    _, body = parse_front_matter(content)
    plain_body = markdown_to_text(body)

    # --- Website (Astro) ---
    separator("BLOG POST — softwarecaptains.be")
    print(f"TITLE:\n{title}\n")
    print(f"BODY:\n{body.strip()}")
    input("\nPress Enter to commit this post to the website repo and open a PR...")
    # Obsidian resolves attachments anywhere in the vault; look next to the drafts folder.
    pr_url = publish_to_website(title, body, Path(filepath).parent.parent)
    print(f"Pull request: {pr_url}")
    print("Merging the PR to main puts the post online.")
    webbrowser.open(pr_url)

    # --- LinkedIn ---
    separator("LINKEDIN POST")
    print(plain_body)
    input("\nPress Enter to open LinkedIn in your browser...")
    copy_to_clipboard(plain_body)
    webbrowser.open(LINKEDIN_URL)

    separator("Done")
    print("The PR and LinkedIn are open. Review and merge the PR, paste and review the LinkedIn post.\n")

    published_dir = os.getenv('PUBLISHED_DIR')
    if not published_dir:
        print("Warning: PUBLISHED_DIR is not set in .env — file not moved.")
    else:
        dest = Path(published_dir).expanduser()
        dest.mkdir(parents=True, exist_ok=True)
        Path(filepath).write_text(set_publish_date(content, date.today().isoformat()), encoding='utf-8')
        shutil.move(str(filepath), dest / Path(filepath).name)
        print(f"Moved to: {dest / Path(filepath).name}")


if __name__ == '__main__':
    main()
