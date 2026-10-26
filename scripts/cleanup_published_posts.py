#!/usr/bin/env python3
"""Permanently remove imported Virgool 'سایر مطالب' blocks from published post sources."""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "content" / "posts"
OTHER_POSTS = re.compile(
    r"(?is)(?:<hr\b[^>]*>\s*(?:</hr>\s*)?)?"
    r"<h([1-6])\b[^>]*>\s*(?:<[^>]+>\s*)*سایر\s+مطالب\s*:?"
    r"\s*(?:</[^>]+>\s*)*</h\1>\s*<ul\b[^>]*>.*?</ul>"
)

def main() -> None:
    changed = blocks = 0
    for path in sorted(POSTS.glob("*.md")):
        if path.name == "_index.md":
            continue
        original = path.read_text(encoding="utf-8")
        match = re.match(r"\A---\n.*?\n---(?:\n|$)", original, re.S)
        if not match:
            continue
        front, body = original[:match.end()], original[match.end():]
        cleaned, count = OTHER_POSTS.subn("", body)
        if count:
            path.write_text(front + cleaned, encoding="utf-8")
            changed += 1
            blocks += count
    print(f"Removed {blocks} 'سایر مطالب' block(s) from {changed} published post(s).")

if __name__ == "__main__":
    main()
