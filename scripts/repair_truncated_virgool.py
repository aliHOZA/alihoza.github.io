#!/usr/bin/env python3
"""Restore truncated Virgool article bodies from the original export (CHATGPT)."""
from __future__ import annotations

import argparse
import html
import re
import zipfile
from pathlib import Path

from import_virgool import ArticleParser, FILE_RE, POSTS, ROOT

REPORT = ROOT / "reports" / "virgool-body-repair.md"


def plain_text(markup: str) -> str:
    """Extract a rough text length for detecting title/description-only stubs."""
    return re.sub(r"\\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup))).strip()


def split_front_matter(content: str) -> tuple[str, str]:
    if not content.startswith("---\\n"):
        return "", content
    end = content.find("\\n---", 4)
    if end < 0:
        return "", content
    return content[: end + 4], content[end + 4 :].lstrip("\\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", default="virgool-export-2026-01-06--ZtG.zip")
    args = parser.parse_args()
    archive = ROOT / args.archive
    if not archive.exists():
        raise SystemExit(f"Archive not found: {archive}")

    # CHATGPT: only replace clearly truncated bodies; preserve front matter and every substantive article.
    repaired: list[tuple[str, int, int]] = []
    checked = 0
    with zipfile.ZipFile(archive) as zf:
        for name in sorted(zf.namelist()):
            base = Path(name).name
            if base.startswith("draft--"):
                continue
            match = FILE_RE.match(base)
            if not match:
                continue
            post_id = match.group("id")
            candidates = list(POSTS.glob(f"*{post_id}.md"))
            if not candidates:
                continue
            target = candidates[0]
            current = target.read_text(encoding="utf-8")
            front, current_body = split_front_matter(current)
            current_len = len(plain_text(current_body))
            # A stub is a very short body; don't touch posts with meaningful existing text.
            if current_len >= 300:
                continue

            article = ArticleParser()
            article.feed(zf.read(name).decode("utf-8", errors="replace"))
            source_body = "".join(article.parts).strip()
            source_len = len(plain_text(source_body))
            checked += 1
            if not source_body or source_len < 500 or source_len < current_len + 200:
                continue

            target.write_text(front + "\\n\\n" + source_body + "\\n", encoding="utf-8")
            repaired.append((target.relative_to(ROOT).as_posix(), current_len, source_len))

    lines = [
        "# Virgool article body repair",
        "",
        "- Purpose: restore existing title/description-only stubs from the original export.",
        "- Safety rule: only replace bodies under 300 text characters when the source body has at least 500 characters and adds at least 200 characters.",
        f"- Candidate stubs checked: {checked}",
        f"- Bodies repaired: {len(repaired)}",
        "",
        "## Repaired posts",
        "",
    ]
    lines.extend(f"- `{path}`: {old_len} → {new_len} text characters" for path, old_len, new_len in repaired)
    if not repaired:
        lines.append("- None")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    for path, old_len, new_len in repaired:
        print(f"Repaired {path}: {old_len} -> {new_len} text characters")
    print(f"Checked {checked} candidate stubs; repaired {len(repaired)}.")


if __name__ == "__main__":
    main()
