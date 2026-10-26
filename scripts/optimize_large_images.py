#!/usr/bin/env python3
"""Safely convert eligible large raster images to lossy WebP and rewrite references."""
from pathlib import Path
from PIL import Image
import json
import os
from urllib.parse import quote

ROOT = Path(".")
LIMIT = 500_000  # Decimal KB: only files strictly larger than 500 KB.
MIN_SAVING_RATIO = 0.30  # Replace only if the WebP is at least 30% smaller.
QUALITY = 90
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
SKIP_PARTS = {
    "thumb", "thumbs", "thumbnail", "thumbnails",
    "generated-thumbnails", "post-thumbnails",
}
SKIP_DIRS = {".git", "node_modules", "vendor", "public", "resources", "resources_gen"}
TEXT_EXTS = {
    ".md", ".markdown", ".html", ".htm", ".xml", ".toml",
    ".yaml", ".yml", ".json", ".css", ".js",
}
REPORT_MD = Path(".github/image-optimization-report.md")
REPORT_JSON = Path(".github/image-optimization-results.json")

records = []
rejected = []
replacements = {}
sources_to_remove = []
inventory = {
    "large_supported": 0,
    "excluded_large": 0,
    "animated_large": 0,
    "conversion_errors": 0,
    "output_collisions": 0,
}


def is_excluded(path):
    parts = {part.lower() for part in path.parts}
    if parts & SKIP_PARTS or parts & SKIP_DIRS:
        return True
    name = path.stem.lower()
    return any(token in name for token in ("thumbnail", "thumb_", "_thumb", "-thumb", "thumb-"))


# Inventory all eligible source formats above the new threshold. Existing WebP
# files are already optimized and are not re-encoded.
candidates = []
for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
        continue
    try:
        before = path.stat().st_size
    except OSError:
        continue
    if before <= LIMIT:
        continue
    if is_excluded(path):
        inventory["excluded_large"] += 1
        continue
    inventory["large_supported"] += 1
    candidates.append((path, before))

for path, before in candidates:
    temp = None
    try:
        with Image.open(path) as opened:
            # Never discard animation frames or silently change animated assets.
            if getattr(opened, "is_animated", False):
                inventory["animated_large"] += 1
                continue
            opened.load()
            has_alpha = (
                opened.mode in ("RGBA", "LA", "PA")
                or "transparency" in opened.info
            )
            im = opened
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA" if has_alpha else "RGB")

            out = path.with_suffix(".webp")
            # Never overwrite a pre-existing file with the same stem.
            if out.exists():
                inventory["output_collisions"] += 1
                print(f"SKIP {path}: output already exists ({out})")
                continue

            temp = out.with_name(out.stem + ".optimization-tmp.webp")
            im.save(temp, "WEBP", quality=QUALITY, method=6)
            after = temp.stat().st_size
            saving_ratio = (before - after) / before if before else 0

            if saving_ratio < MIN_SAVING_RATIO:
                rejected.append({
                    "source": path.as_posix(),
                    "source_bytes": before,
                    "candidate_bytes": after,
                    "saving_percent": round(saving_ratio * 100, 2),
                    "reason": "WebP is not at least 30% smaller",
                })
                temp.unlink(missing_ok=True)
                temp = None
                # Older optimization passes may have rewritten references even
                # when the original source remains; restore those references.
                replacements[out.as_posix()] = path.as_posix()
                replacements[out.name] = path.name
                continue

            # Complete the new file first. Keep the source until all text
            # references have been rewritten successfully.
            os.replace(temp, out)
            temp = None
            old_rel, new_rel = path.as_posix(), out.as_posix()
            replacements[old_rel] = new_rel
            replacements[path.name] = out.name
            records.append({
                "source": old_rel,
                "before_bytes": before,
                "webp": new_rel,
                "after_bytes": out.stat().st_size,
                "saving_percent": round(saving_ratio * 100, 2),
            })
            sources_to_remove.append(path)
    except Exception as exc:
        inventory["conversion_errors"] += 1
        print(f"SKIP {path}: {exc}")
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)

# Rewrite only text-based site files. Binary assets are never edited.
# Longest paths first so full paths are handled before their basenames.
for file in sorted(ROOT.rglob("*")):
    if not file.is_file() or file.suffix.lower() not in TEXT_EXTS or ".git" in file.parts:
        continue
    try:
        original = file.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    updated = original
    for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        updated = updated.replace(quote(old, safe="/"), quote(new, safe="/"))
        updated = updated.replace(old, new)
        if "/" in old:
            updated = updated.replace("/" + old, "/" + new)
    if updated != original:
        file.write_text(updated, encoding="utf-8")

# Only now remove the sources for successfully converted images.
for source in sources_to_remove:
    source.unlink()

total_before = sum(item["before_bytes"] for item in records)
total_after = sum(item["after_bytes"] for item in records)
saved = total_before - total_after
saved_percent = (saved / total_before * 100) if total_before else 0

report = [
    "# گزارش بهینه‌سازی تصاویر بزرگ",
    "",
    f"- روش: تبدیل lossy به WebP با کیفیت {QUALITY} و method=6",
    f"- آستانه: بیش از ۵۰۰٬۰۰۰ بایت (۵۰۰ KB)",
    "- شرط جایگزینی: فایل WebP باید دست‌کم ۳۰٪ کوچک‌تر باشد.",
    "- تصاویر بندانگشتی و فایل‌های متحرک تبدیل نمی‌شوند؛ فایل WebP موجود نیز بازنویسی نمی‌شود.",
    f"- تصاویر بزرگِ قابل‌بررسی: {inventory['large_supported']}",
    f"- تصاویر بزرگِ مستثناشده به‌دلیل thumbnail: {inventory['excluded_large']}",
    f"- فایل‌های متحرکِ بزرگِ ردشده: {inventory['animated_large']}",
    f"- برخورد با نام خروجی موجود: {inventory['output_collisions']}",
    f"- خطاهای تبدیل: {inventory['conversion_errors']}",
    f"- تعداد تبدیل و جایگزینی: {len(records)}",
    f"- تعداد تبدیل‌های ردشده به‌دلیل صرفه‌جویی کمتر از ۳۰٪: {len(rejected)}",
    f"- حجم تصاویر جایگزین‌شده پیش از تبدیل: {total_before / 1024 / 1024:.2f} MiB",
    f"- حجم WebPهای جایگزین‌شده: {total_after / 1024 / 1024:.2f} MiB",
    f"- صرفه‌جویی خالص: {saved / 1024 / 1024:.2f} MiB ({saved_percent:.1f}%)",
    "",
    "| فایل اصلی | حجم اولیه (KiB) | فایل WebP | حجم WebP (KiB) | صرفه‌جویی (KiB) |",
    "|---|---:|---|---:|---:|",
]
for item in records:
    report.append(
        f"| `{item['source']}` | {item['before_bytes']/1024:.1f} "
        f"| `{item['webp']}` | {item['after_bytes']/1024:.1f} "
        f"| {(item['before_bytes']-item['after_bytes'])/1024:.1f} |"
    )
if rejected:
    report += [
        "", "## تصاویر حفظ‌شده به‌صورت اصلی", "",
        "| فایل اصلی | حجم اصلی (KiB) | WebP آزمایشی (KiB) | صرفه‌جویی | دلیل |",
        "|---|---:|---:|---:|---|",
    ]
    for item in rejected:
        report.append(
            f"| `{item['source']}` | {item['source_bytes']/1024:.1f} "
            f"| {item['candidate_bytes']/1024:.1f} | {item['saving_percent']:.1f}% "
            "| صرفه‌جویی کمتر از ۳۰٪ |"
        )

REPORT_MD.write_text("\n".join(report) + "\n", encoding="utf-8")
REPORT_JSON.write_text(json.dumps({
    "threshold_bytes": LIMIT,
    "quality": QUALITY,
    "minimum_saving_ratio": MIN_SAVING_RATIO,
    "inventory": inventory,
    "converted_count": len(records),
    "before_bytes": total_before,
    "after_bytes": total_after,
    "saved_bytes": saved,
    "saved_percent": round(saved_percent, 2),
    "rejected": rejected,
    "files": records,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(
    f"Inventory: {inventory}; converted {len(records)}; rejected {len(rejected)}; "
    f"net saved {saved} bytes ({saved_percent:.1f}%)."
)
