#!/usr/bin/env python3
"""[CHATGPT] Remove imported Virgool 'سایر مطالب' recommendation blocks from published posts."""
from __future__ import annotations

import html
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "content" / "posts"

# Match an optional separator, a heading, and its immediately following link list.
BLOCK_RE = re.compile(
    r"(?is)(?P<hr>(?:<hr\b[^>]*>\s*(?:</hr>\s*)*)?)"
    r"<h(?P<level>[1-6])\b[^>]*>(?P<heading>.*?)</h(?P=level)>"
    r"(?P<tail>\s*(?:<ul\b[^>]*>.*?</ul>)?)"
)
TAG_RE = re.compile(r"<[^>]+>")


def normalize_heading(value: str) -> str:
    value = html.unescape(TAG_RE.sub(" ", value))
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    value = value.replace("\u200c", "").replace("\u200f", "").replace("\ufeff", "")
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"[：:!！.،؛\-–—]+$", "", value).strip()
    return value


def remove_blocks(text: str) -> tuple[str, int]:
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        if normalize_heading(match.group("heading")) != "سایر مطالب":
            return match.group(0)
        count += 1
        # Drop the Virgool recommendation heading, list, and its separator only.
        return "\n" if match.group("hr") else ""

    return BLOCK_RE.sub(replace, text), count


def main() -> None:
    changed = removed = scanned = 0
    for path in sorted(POSTS.glob("*.md")):
        original = path.read_text(encoding="utf-8")
        updated, count = remove_blocks(original)
        scanned += 1
        if count:
            path.write_text(updated, encoding="utf-8")
            changed += 1
            removed += count
            print(f"Cleaned {path.relative_to(ROOT)}: removed {count} block(s)")
    print(f"Scanned {scanned} posts; removed {removed} block(s) from {changed} posts.")


if __name__ == "__main__":
    main()
