#!/usr/bin/env python3
"""Recover broken Virgool images for the ten affected posts from files.virgool.ir."""
from __future__ import annotations

import hashlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "content" / "posts"
IMAGE_DIR = ROOT / "static" / "images" / "virgool"
REPORT = ROOT / "reports" / "virgool-ir-image-recovery.md"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 350 * 1024 * 1024
TARGET_POST_IDS = {
    "wwpwkvi04ldn", "dftwyxbtorgy", "us1qawarwyzm", "rqur2zllwnwb",
    "pjlio8j11s5r", "y77hw2dw6u2m", "jobe8xigrbdb", "sopv4iukxnyc",
    "bp7t76qarcqn", "ylwd6jgwkugy",
}
URL_RE = re.compile(r"https://files\.virgool\.(?:io|ir)/upload/[^\"'<>\s)]+")
MAGIC_EXTENSIONS = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"RIFF", ".webp"),
)

def image_extension(data: bytes, content_type: str) -> str:
    for signature, extension in MAGIC_EXTENSIONS:
        if data.startswith(signature):
            if extension == ".webp" and data[8:12] != b"WEBP":
                continue
            return extension
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return ".avif"
    stripped = data.lstrip()
    if stripped.startswith(b"<svg") or (
        stripped.startswith(b"<?xml") and b"<svg" in data[:512]
    ):
        return ".svg"
    mime = content_type.split(";", 1)[0].strip().lower()
    mime_extensions = {
        "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
        "image/webp": ".webp", "image/avif": ".avif", "image/svg+xml": ".svg",
    }
    if mime in mime_extensions:
        return mime_extensions[mime]
    raise ValueError(f"could not identify image format (Content-Type: {content_type})")

def source_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.rstrip(".,;"))
    return urllib.parse.urlunsplit(("https", "files.virgool.ir", parsed.path, "", ""))

def main() -> int:
    posts = []
    for post_id in sorted(TARGET_POST_IDS):
        matches = list(POSTS.glob(f"*-{post_id}.md"))
        if len(matches) != 1:
            raise RuntimeError(f"expected one Markdown file for {post_id}, found {len(matches)}")
        posts.append(matches[0])

    found: dict[str, list[Path]] = {}
    for post in posts:
        body = post.read_text(encoding="utf-8")
        for match in URL_RE.findall(body):
            url = match.rstrip(".,;")
            found.setdefault(url, []).append(post)

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    successful: dict[str, tuple[str, bytes]] = {}
    failures: list[tuple[str, str]] = []
    total_bytes = 0

    for index, url in enumerate(sorted(found), 1):
        request = urllib.request.Request(
            source_url(url),
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Referer": "https://virgool.ir/",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                content_type = response.headers.get("Content-Type", "application/octet-stream")
                data = response.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                raise ValueError("image exceeds 20 MiB limit")
            if not content_type.lower().startswith("image/") and not data.lstrip().startswith((b"<svg", b"<?xml")):
                raise ValueError(f"unexpected Content-Type: {content_type}")
            ext = image_extension(data, content_type)
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
            successful[url] = (digest + ext, data)
            total_bytes += len(data)
            if total_bytes > MAX_TOTAL_BYTES:
                raise RuntimeError("batch exceeds 350 MiB safety limit; no post references have been changed")
        except RuntimeError:
            raise
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            failures.append((url, str(exc)))
        print(f"[{index}/{len(found)}] {'OK' if url in successful else 'FAILED'} {url}")

    for name, data in successful.values():
        destination = IMAGE_DIR / name
        if destination.exists() and destination.read_bytes() != data:
            raise RuntimeError(f"refusing to overwrite different existing file: {destination}")
        if not destination.exists():
            destination.write_bytes(data)

    changed_posts = 0
    for post in posts:
        original = post.read_text(encoding="utf-8")
        updated = original
        for url, (name, _data) in successful.items():
            updated = updated.replace(url, "/images/virgool/" + name)
        if updated != original:
            post.write_text(updated, encoding="utf-8")
            changed_posts += 1

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Virgool.ir image recovery report", "",
        "- Scope: the ten affected posts only",
        f"- Posts checked: {len(posts)}",
        f"- Unique image URLs found: {len(found)}",
        f"- Images downloaded and verified: {len(successful)}",
        f"- Posts updated: {changed_posts}",
        f"- Downloaded size: {total_bytes:,} bytes ({total_bytes / (1024 * 1024):.1f} MiB)",
        f"- Failed images: {len(failures)}", "",
        "Only verified image files were added; failed references remain unchanged.",
        "Downloads use files.virgool.ir without x-img transformations. File extensions are detected from the actual image bytes.",
    ]
    if failures:
        lines += ["", "## Failures", ""]
        lines.extend(f"- {url} — {reason.replace('|', chr(92) + '|')}" for url, reason in failures)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines))
    return 0 if not failures else 1

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
