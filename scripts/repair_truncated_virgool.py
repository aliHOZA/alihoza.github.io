#!/usr/bin/env python3
"""Restore truncated or malformed Virgool article bodies from the original export (CHATGPT)."""
from __future__ import annotations

import argparse
import html
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

from import_virgool import ArticleParser, FILE_RE, POSTS, ROOT, parse_date, q

REPORT = ROOT / "reports" / "virgool-body-repair.md"


def plain_text(markup: str) -> str:
    """Extract a rough text length for detecting title/description-only stubs."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup))).strip()


def split_front_matter(content: str) -> tuple[str, str]:
    if not content.startswith("---\n"):
        return "", content
    end = content.find("\n---", 4)
    if end < 0:
        return "", content
    return content[: end + 4], content[end + 4 :].lstrip("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", default="virgool-export-2026-01-06--ZtG.zip")
    args = parser.parse_args()
    archive = ROOT / args.archive
    if not archive.exists():
        raise SystemExit(f"Archive not found: {archive}")

    # CHATGPT: repair only short bodies or malformed files; preserve complete articles and valid metadata.
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
            post_id, day = match.group("id"), match.group("date")
            candidates = list(POSTS.glob(f"*{post_id}.md"))
            if not candidates:
                continue
            target = candidates[0]
            current_content = target.read_text(encoding="utf-8")
            front, current_body = split_front_matter(current_content)
            malformed = not bool(front)
            current_len = len(plain_text(current_body)) if not malformed else 0
            if not malformed and current_len >= 300:
                continue

            article = ArticleParser()
            article.feed(zf.read(name).decode("utf-8", errors="replace"))
            source_body = "".join(article.parts).strip()
            source_len = len(plain_text(source_body))
            checked += 1
            if not source_body or source_len < 500:
                continue
            if not malformed and source_len < current_len + 200:
                continue

            if malformed:
                title = html.unescape(article.title.strip()) or base
                summary = plain_text(source_body)[:240]
                try:
                    date = parse_date(article.published, day)
                except (ValueError, TypeError):
                    date = day
                front = (
                    "---\n"
                    f"title: {q(title)}\n"
                    f"date: {q(date)}\n"
                    f"summary: {q(summary)}\n"
                    f"virgool_id: {q(post_id)}\n"
                    f"original_url: {q(article.canonical)}\n"
                    "draft: false\n"
                    "---"
                )
            target.write_text(front + "\n\n" + source_body + "\n", encoding="utf-8")
            repaired.append((target.relative_to(ROOT).as_posix(), current_len, source_len))

    lines = [
        "# Virgool article body repair",
        "",
        "- Purpose: restore existing title/description-only stubs and malformed files from the original export.",
        "- Safety rule: valid posts are only replaced when their body is under 300 text characters and the source has at least 500 characters with a 200-character gain; malformed front matter is reconstructed from the export.",
        f"- Candidate files checked: {checked}",
        f"- Bodies repaired: {len(repaired)}",
        "",
        "## Repaired posts",
        "",
    ]
    lines.extend(f"- `{path}`: {old_len} → {new_len} text characters" for path, old_len, new_len in repaired)
    if not repaired:
        lines.append("- None")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for path, old_len, new_len in repaired:
        print(f"Repaired {path}: {old_len} -> {new_len} text characters")
    print(f"Checked {checked} candidate files; repaired {len(repaired)}.")


if __name__ == "__main__":
    main()
