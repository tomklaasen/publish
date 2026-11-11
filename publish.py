#!/usr/bin/env python3

import sys
import re
import random
from datetime import date, datetime
import shutil
import subprocess
import webbrowser
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent / '.env')

LINKEDIN_URL = "https://www.linkedin.com/feed/"


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

    # --- Squarespace ---
    separator("BLOG POST — Squarespace")
    print(f"TITLE:\n{title}\n")
    print(f"BODY:\n{plain_body}")
    copy_to_clipboard(f"{title}\n\n{plain_body}")
    squarespace_url = os.getenv('SQUARESPACE_URL')
    if not squarespace_url:
        print("Error: SQUARESPACE_URL is not set in .env")
        sys.exit(1)
    input("\nPress Enter to open Squarespace in your browser...")
    webbrowser.open(squarespace_url)

    # --- LinkedIn ---
    separator("LINKEDIN POST")
    print(plain_body)
    input("\nPress Enter to open LinkedIn in your browser...")
    copy_to_clipboard(plain_body)
    webbrowser.open(LINKEDIN_URL)

    separator("Done")
    print("Both pages are open. Paste and review before publishing.\n")

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
