#!/usr/bin/env python3
"""Convert large, non-thumbnail repository images to lossy WebP and rewrite references."""
from pathlib import Path
from PIL import Image
import re, json, subprocess

ROOT = Path(".")
LIMIT = 700 * 1024
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
SKIP_PARTS = {"thumb", "thumbs", "thumbnail", "thumbnails", "generated-thumbnails", "post-thumbnails"}
SKIP_DIRS = {".git", "node_modules", "vendor", "public", "resources", "resources_gen"}
records = []
replacements = {}

def is_excluded(path):
    parts = {p.lower() for p in path.parts}
    if parts & SKIP_PARTS or parts & SKIP_DIRS:
        return True
    name = path.stem.lower()
    return any(token in name for token in ("thumbnail", "thumb_", "_thumb", "-thumb", "thumb-"))

for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS or is_excluded(path):
        continue
    before = path.stat().st_size
    if before <= LIMIT:
        continue
    try:
        with Image.open(path) as im:
            # Avoid animated files; do not silently discard frames.
            if getattr(im, "is_animated", False):
                continue
            im.load()
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA" if "transparency" in im.info else "RGB")
            out = path.with_suffix(".webp")
            im.save(out, "WEBP", quality=90, method=6)
        after = out.stat().st_size
        if out == path or not out.exists():
            continue
        # Replace exact relative path references in text files, preserving URL-encoded alternatives.
        old_rel = path.as_posix()
        new_rel = out.as_posix()
        replacements[old_rel] = new_rel
        replacements[path.name] = out.name
        records.append((old_rel, before, new_rel, after))
        path.unlink()
    except Exception as exc:
        print(f"SKIP {path}: {exc}")

# Rewrite references in text-based site files only.
text_exts = {".md", ".markdown", ".html", ".htm", ".xml", ".toml", ".yaml", ".yml", ".json", ".css", ".js"}
for file in ROOT.rglob("*"):
    if not file.is_file() or file.suffix.lower() not in text_exts or ".git" in file.parts:
        continue
    try:
        text = file.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    original = text
    for old, new in sorted(replacements.items(), key=lambda kv: len(kv[0]), reverse=True):
        text = text.replace(old, new)
        # Also update root-relative references where the full path was used.
        if old in replacements and "/" in old:
            text = text.replace("/" + old, "/" + new)
    if text != original:
        file.write_text(text, encoding="utf-8")

total_before = sum(r[1] for r in records)
total_after = sum(r[3] for r in records)
saved = total_before - total_after
report = [
    "# گزارش بهینه‌سازی تصاویر بزرگ",
    "",
    "- روش: تبدیل lossy به WebP با کیفیت ۹۰ و method=6",
    "- آستانه: بیش از ۷۰۰ KiB (۷۱۶٬۸۰۰ بایت)",
    "- تصاویر دارای نام/مسیر thumbnail و فایل‌های متحرک از تبدیل مستثنا شدند.",
    f"- تعداد تبدیل موفق: {len(records)}",
    f"- حجم پیش از تبدیل: {total_before / 1024 / 1024:.2f} MiB",
    f"- حجم پس از تبدیل: {total_after / 1024 / 1024:.2f} MiB",
    f"- صرفه‌جویی خالص: {saved / 1024 / 1024:.2f} MiB ({(saved / total_before * 100) if total_before else 0:.1f}%)",
    "",
    "| فایل اصلی | حجم اولیه (KiB) | فایل WebP | حجم WebP (KiB) | صرفه‌جویی (KiB) |",
    "|---|---:|---|---:|---:|",
]
for old, before, new, after in records:
    report.append(f"| `{old}` | {before/1024:.1f} | `{new}` | {after/1024:.1f} | {(before-after)/1024:.1f} |")
Path(".github/image-optimization-report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
Path(".github/image-optimization-results.json").write_text(json.dumps({
    "threshold_bytes": LIMIT, "quality": 90, "converted_count": len(records),
    "before_bytes": total_before, "after_bytes": total_after, "saved_bytes": saved,
    "files": [{"source": a, "before_bytes": b, "webp": c, "after_bytes": d} for a,b,c,d in records]
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Converted {len(records)} files; saved {saved} bytes.")
