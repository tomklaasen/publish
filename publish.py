#!/usr/bin/env python3

import sys
import re
import random
import shutil
import subprocess
import webbrowser
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent / '.env')

SQUARESPACE_URL = "https://springtail-gopher-mt8f.squarespace.com/config/pages/5e2573cadcc09322ea070baa"
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


def pick_random_file():
    drafts_dir = os.getenv('DRAFTS_DIR')
    if not drafts_dir:
        print("Error: DRAFTS_DIR is not set in .env")
        sys.exit(1)
    drafts_path = Path(drafts_dir).expanduser()
    files = list(drafts_path.glob('*.md'))
    if not files:
        print(f"Error: no markdown files found in {drafts_path}")
        sys.exit(1)
    chosen = random.choice(files)
    print(f"Randomly selected: {chosen.name}")
    return chosen


def main():
    if len(sys.argv) == 1:
        filepath = pick_random_file()
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
    input("\nPress Enter to open Squarespace in your browser...")
    webbrowser.open(SQUARESPACE_URL)

    # --- LinkedIn ---
    separator("LINKEDIN POST")
    linkedin_text = f"{title}\n\n{plain_body}"
    print(linkedin_text)
    copy_to_clipboard(linkedin_text)
    input("\nPress Enter to open LinkedIn in your browser...")
    webbrowser.open(LINKEDIN_URL)

    separator("Done")
    print("Both pages are open. Paste and review before publishing.\n")

    published_dir = os.getenv('PUBLISHED_DIR')
    if not published_dir:
        print("Warning: PUBLISHED_DIR is not set in .env — file not moved.")
    else:
        dest = Path(published_dir).expanduser()
        dest.mkdir(parents=True, exist_ok=True)
        shutil.move(str(filepath), dest / Path(filepath).name)
        print(f"Moved to: {dest / Path(filepath).name}")


if __name__ == '__main__':
    main()
