#!/usr/bin/env python3
"""[CHATGPT] Generate compact WebP thumbnails for the homepage from each post's first local image."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "content" / "posts"
STATIC = ROOT / "static"
THUMBNAILS = STATIC / "images" / "thumbnails"
# Match HTML image tags in exported Virgool posts and ordinary Markdown image syntax.
HTML_IMG_RE = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.I)
MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
WIDTH, HEIGHT = 160, 120
QUALITY = 68


def first_image(text: str) -> str | None:
    match = HTML_IMG_RE.search(text) or MD_IMG_RE.search(text)
    return match.group(1).strip() if match else None


def local_source(src: str) -> Path | None:
    src = unquote(src.split("?", 1)[0])
    if src.startswith(("https://", "http://", "data:", "//")):
        return None
    if src.startswith("/"):
        candidate = (STATIC / src.lstrip("/")).resolve()
    else:
        candidate = (ROOT / src).resolve()
    try:
        candidate.relative_to(STATIC.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def main() -> int:
    THUMBNAILS.mkdir(parents=True, exist_ok=True)
    posts = sorted(POSTS.rglob("*.md"))
    made = skipped = 0
    total_bytes = 0

    for post in posts:
        source = local_source(first_image(post.read_text(encoding="utf-8")) or "")
        if source is None:
            skipped += 1
            continue
        target = THUMBNAILS / f"{post.stem}.webp"
        try:
            with Image.open(source) as original:
                image = ImageOps.exif_transpose(original)
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGBA" if "transparency" in image.info else "RGB")
                image = ImageOps.fit(image, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                if image.mode == "RGBA":
                    image.save(target, "WEBP", quality=QUALITY, method=6)
                else:
                    image.convert("RGB").save(target, "WEBP", quality=QUALITY, method=6)
            made += 1
            total_bytes += target.stat().st_size
        except (OSError, ValueError) as exc:
            print(f"Skipping {post.relative_to(ROOT)}: {exc}", file=sys.stderr)
            skipped += 1

    print(f"Posts scanned: {len(posts)}")
    print(f"Thumbnails generated: {made}")
    print(f"Posts skipped (no local first image or conversion error): {skipped}")
    print(f"Total thumbnail size: {total_bytes:,} bytes ({total_bytes / 1024:.1f} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
