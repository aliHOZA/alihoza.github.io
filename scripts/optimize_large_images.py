#!/usr/bin/env python3
"""Safely convert eligible large repository images to WebP and rewrite references."""
from pathlib import Path
from PIL import Image
import json
import os
from urllib.parse import quote

ROOT = Path(".")
LIMIT = 700 * 1024
MIN_SAVING_RATIO = 0.10  # Require at least 10% smaller output.
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
SKIP_PARTS = {"thumb", "thumbs", "thumbnail", "thumbnails", "generated-thumbnails", "post-thumbnails"}
SKIP_DIRS = {".git", "node_modules", "vendor", "public", "resources", "resources_gen"}
TEXT_EXTS = {".md", ".markdown", ".html", ".htm", ".xml", ".toml", ".yaml", ".yml", ".json", ".css", ".js"}
REPORT_JSON = Path(".github/image-optimization-results.json")
records = []
rejected = []
replacements = {}
inventory = {"large_supported": 0, "excluded_large": 0, "animated_large": 0, "conversion_errors": 0, "output_collisions": 0}

def is_excluded(path):
    parts = {p.lower() for p in path.parts}
    if parts & SKIP_PARTS or parts & SKIP_DIRS:
        return True
    name = path.stem.lower()
    return any(token in name for token in ("thumbnail", "thumb_", "_thumb", "-thumb", "thumb-"))

# Read the previous report before replacing it. Undo the one previously reported
# non-saving conversion, but only when the original is available in the checkout.
previous_bad = []
try:
    previous = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    for item in previous.get("files", []):
        if item.get("after_bytes", 0) >= item.get("before_bytes", 0):
            source = Path(item["source"])
            webp = Path(item["webp"])
            if source.exists() and webp.exists():
                webp.unlink()
                replacements[webp.as_posix()] = source.as_posix()
                replacements[webp.name] = source.name
                previous_bad.append({"source": source.as_posix(), "webp": webp.as_posix()})
except (OSError, ValueError, KeyError, TypeError):
    pass

# First build an inventory, including excluded large files, so the run is auditable.
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
    try:
        with Image.open(path) as im:
            # Do not silently discard animation frames.
            if getattr(im, "is_animated", False):
                inventory["animated_large"] += 1
                continue
            im.load()
            has_alpha = im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA" if has_alpha else "RGB")
            out = path.with_suffix(".webp")
            # Never overwrite an existing WebP; it may belong to another source with the same stem.
            if out.exists():
                inventory["output_collisions"] += 1
                print(f"SKIP {path}: output already exists ({out})")
                continue
            temp = out.with_name(out.stem + ".optimization-tmp.webp")
            try:
                im.save(temp, "WEBP", quality=90, method=6)
                after = temp.stat().st_size
                saving_ratio = (before - after) / before if before else 0
                if saving_ratio < MIN_SAVING_RATIO:
                    temp.unlink(missing_ok=True)
                    rejected.append({
                        "source": path.as_posix(), "source_bytes": before,
                        "candidate_bytes": after, "reason": "WebP is not at least 10% smaller"
                    })
                    # If this was previously referenced as WebP, restore references to the original.
                    replacements[out.as_posix()] = path.as_posix()
                    replacements[out.name] = path.name
                    continue
                os.replace(temp, out)
            finally:
                temp.unlink(missing_ok=True)

        old_rel, new_rel = path.as_posix(), out.as_posix()
        replacements[old_rel] = new_rel
        replacements[path.name] = out.name
        records.append((old_rel, before, new_rel, out.stat().st_size))
        path.unlink()
    except Exception as exc:
        inventory["conversion_errors"] += 1
        print(f"SKIP {path}: {exc}")

# Rewrite references only in text-based site files; binary files are never edited.
for file in ROOT.rglob("*"):
    if not file.is_file() or file.suffix.lower() not in TEXT_EXTS or ".git" in file.parts:
        continue
    try:
        original = file.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    text = original
    for old, new in sorted(replacements.items(), key=lambda kv: len(kv[0]), reverse=True):
        # Rewrite literal and URL-encoded references before deleting the source.
        text = text.replace(quote(old, safe="/"), quote(new, safe="/"))
        text = text.replace(old, new)
        if "/" in old:
            text = text.replace("/" + old, "/" + new)
    if text != original:
        file.write_text(text, encoding="utf-8")

total_before = sum(r[1] for r in records)
total_after = sum(r[3] for r in records)
saved = total_before - total_after
report = [
    "# گزارش بهینه‌سازی تصاویر بزرگ", "",
    "- روش: تبدیل lossy به WebP با کیفیت ۹۰ و method=6",
    "- آستانه: بیش از ۷۰۰ KiB (۷۱۶٬۸۰۰ بایت)",
    "- شرط جایگزینی: فایل WebP باید دست‌کم ۱۰٪ کوچک‌تر باشد.",
    "- تصاویر thumbnail و فایل‌های متحرک تبدیل نمی‌شوند.",
    f"- تصاویر بزرگِ قابل‌بررسی: {inventory['large_supported']}",
    f"- تصاویر بزرگِ مستثناشده به‌دلیل thumbnail: {inventory['excluded_large']}",
    f"- فایل‌های متحرکِ بزرگِ ردشده: {inventory['animated_large']}",
    f"- خطاهای تبدیل: {inventory['conversion_errors']}",
    f"- تعداد تبدیل و جایگزینی: {len(records)}",
    f"- تعداد تبدیل‌های ردشده به‌دلیل صرفه‌جویی ناکافی: {len(rejected)}",
    f"- حجم تصاویر جایگزین‌شده پیش از تبدیل: {total_before / 1024 / 1024:.2f} MiB",
    f"- حجم WebPهای جایگزین‌شده: {total_after / 1024 / 1024:.2f} MiB",
    f"- صرفه‌جویی خالص: {saved / 1024 / 1024:.2f} MiB ({(saved / total_before * 100) if total_before else 0:.1f}%)",
    "", "| فایل اصلی | حجم اولیه (KiB) | فایل WebP | حجم WebP (KiB) | صرفه‌جویی (KiB) |",
    "|---|---:|---|---:|---:|",
]
for old, before, new, after in records:
    report.append(f"| `{old}` | {before/1024:.1f} | `{new}` | {after/1024:.1f} | {(before-after)/1024:.1f} |")
if rejected:
    report += ["", "## تصاویر حفظ‌شده به‌صورت اصلی", "", "| فایل اصلی | حجم اصلی (KiB) | WebP آزمایشی (KiB) | دلیل |", "|---|---:|---:|---|"]
    for item in rejected:
        report.append(f"| `{item['source']}` | {item['source_bytes']/1024:.1f} | {item['candidate_bytes']/1024:.1f} | صرفه‌جویی کمتر از ۱۰٪ |")
if previous_bad:
    report += ["", "## اصلاح تبدیل ناموفق قبلی", ""]
    for item in previous_bad:
        report.append(f"- فایل اصلی `{item['source']}` حفظ شد و خروجی نامناسب `{item['webp']}` حذف شد.")
Path(".github/image-optimization-report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
REPORT_JSON.write_text(json.dumps({
    "threshold_bytes": LIMIT, "quality": 90, "minimum_saving_ratio": MIN_SAVING_RATIO,
    "inventory": inventory, "converted_count": len(records),
    "before_bytes": total_before, "after_bytes": total_after, "saved_bytes": saved,
    "rejected": rejected, "repaired_previous_non_saving": previous_bad,
    "files": [{"source": a, "before_bytes": b, "webp": c, "after_bytes": d} for a,b,c,d in records]
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Inventory: {inventory}; converted {len(records)}; rejected {len(rejected)}; net saved {saved} bytes.")
