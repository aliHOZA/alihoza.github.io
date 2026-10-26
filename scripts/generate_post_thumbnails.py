#!/usr/bin/env python3
"""[CHATGPT] Generate compact WebP thumbnails from each post's first image, local or remote."""
from __future__ import annotations

import re
import sys
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "content" / "posts"
STATIC = ROOT / "static"
THUMBNAILS = STATIC / "images" / "thumbnails"
HTML_IMG_RE = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.I)
MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
WIDTH, HEIGHT = 200, 150
QUALITY = 80
MAX_REMOTE_BYTES = 20 * 1024 * 1024


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


def source_image(src: str) -> Image.Image | None:
    if not src:
        return None
    src = src.strip()
    if src.startswith("//"):
        src = "https:" + src
    if src.startswith(("https://", "http://")):
        if urlparse(src).scheme != "https":
            return None
        request = Request(src, headers={"User-Agent": "Mozilla/5.0 (compatible; BlogThumbnailBot/1.0)"})
        try:
            with urlopen(request, timeout=15) as response:
                data = response.read(MAX_REMOTE_BYTES + 1)
            if len(data) > MAX_REMOTE_BYTES:
                raise ValueError("remote image exceeds 20 MiB")
            image = Image.open(BytesIO(data))
            image.load()
            return image
        except Exception as exc:
            print(f"Could not download image {src}: {exc}", file=sys.stderr)
            return None

    path = local_source(src)
    if path is None:
        return None
    try:
        image = Image.open(path)
        image.load()
        return image
    except (OSError, ValueError) as exc:
        print(f"Could not open image {path}: {exc}", file=sys.stderr)
        return None


def main() -> int:
    THUMBNAILS.mkdir(parents=True, exist_ok=True)
    posts = sorted(POSTS.rglob("*.md"))
    made = skipped = 0
    total_bytes = 0

    for post in posts:
        source = first_image(post.read_text(encoding="utf-8")) or ""
        original = source_image(source)
        if original is None:
            skipped += 1
            continue
        target = THUMBNAILS / f"{post.stem}.webp"
        try:
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
        finally:
            original.close()

    print(f"Posts scanned: {len(posts)}")
    print(f"Thumbnails generated: {made}")
    print(f"Posts skipped (missing, inaccessible, or unconvertible first image): {skipped}")
    print(f"Total thumbnail size: {total_bytes:,} bytes ({total_bytes / 1024:.1f} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
