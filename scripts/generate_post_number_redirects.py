#!/usr/bin/env python3
"""Generate SEO-aware short URL redirects for stable numbered posts.

Numbers live in data/post-numbers.json. The --assign-new option appends
numbers for newly added Markdown posts without changing existing assignments.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "content" / "posts"
MAPPING_FILE = ROOT / "data" / "post-numbers.json"
OUTPUT_DIR = ROOT / "static" / "posts"
BASE_URL = "https://alihoza.github.io"
PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--assign-new",
        action="store_true",
        help="append stable numbers for posts not yet present in the mapping",
    )
    args = parser.parse_args()

    mapping = json.loads(MAPPING_FILE.read_text(encoding="utf-8"))
    posts = {
        path.stem: path
        for path in POSTS_DIR.glob("*.md")
        if path.name != "_index.md"
    }
    missing = sorted(set(posts) - set(mapping))
    stale = sorted(set(mapping) - set(posts))

    if missing and args.assign_new:
        next_number = max(
            (item.get("number", 0) for item in mapping.values()), default=0
        ) + 1
        for slug in missing:
            mapping[slug] = {
                "number": next_number,
                "display": str(next_number).translate(PERSIAN_DIGITS),
            }
            next_number += 1
        MAPPING_FILE.write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Assigned stable numbers to {len(missing)} new post(s).")
        missing = []

    if missing or stale:
        details = []
        if missing:
            details.append("posts missing stable numbers: " + ", ".join(missing))
        if stale:
            details.append("number mappings without a post: " + ", ".join(stale))
        raise SystemExit(
            "Update data/post-numbers.json before building the site; "
            + "; ".join(details)
        )

    numbers: dict[int, str] = {}
    for slug, item in mapping.items():
        number = item.get("number")
        if not isinstance(number, int) or number < 1:
            raise SystemExit(f"Invalid number for {slug}: {number!r}")
        if number in numbers:
            raise SystemExit(
                f"Duplicate post number {number}: {numbers[number]} and {slug}"
            )
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-.+", slug):
            raise SystemExit(f"Unexpected post slug: {slug}")
        numbers[number] = slug

    if len(numbers) != len(posts):
        raise SystemExit("Number mapping count does not match the post count")

    for number, slug in numbers.items():
        target_path = f"/posts/{slug}/"
        canonical_url = BASE_URL + target_path
        target_html = html.escape(target_path, quote=True)
        canonical_html = html.escape(canonical_url, quote=True)
        display = html.escape(mapping[slug].get("display", str(number)))
        page = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>انتقال به نوشته شماره {display} | وبلاگ علی آقا</title>
  <link rel="canonical" href="{canonical_html}">
  <meta http-equiv="refresh" content="0; url={target_html}">
  <script>window.location.replace({json.dumps(target_path)});</script>
</head>
<body>
  <p>در حال انتقال به <a href="{target_html}">آدرس اصلی نوشته شماره {display}</a>…</p>
</body>
</html>
"""
        output = OUTPUT_DIR / str(number) / "index.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(page, encoding="utf-8")

    print(f"Generated {len(numbers)} numbered short-URL redirects.")


if __name__ == "__main__":
    main()
