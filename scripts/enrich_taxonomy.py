#!/usr/bin/env python3
"""Assign a restrained Persian SEO taxonomy to Virgool posts (CHATGPT)."""
from __future__ import annotations
import html, json, re, unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "content" / "posts"
REPORT = ROOT / "reports" / "seo-taxonomy-report.md"

CATEGORIES = {
    "نفت، گاز و انرژی": ["نفت خام", "صادرات نفت", "اقتصاد نفتی", "نفت", "گاز طبیعی", "پتروشیمی", "اوپک", "برنت", "پالایشگاه", "بنزین", "انرژی", "بازار نفت", "نفتی", "گاز", "برق"],
    "اقتصاد ایران و اقتصاد کلان": ["اقتصاد ایران", "اقتصاد", "تورم", "رکود", "بیکاری", "رشد اقتصادی", "یارانه", "بانک مرکزی", "تولید ناخالص", "بودجه", "سرمایه داری", "سرمایه‌داری", "فساد اقتصادی", "تجارت خارجی", "واردات", "صادرات", "توسعه اقتصادی", "فقر", "مالیات", "ارز", "ریال", "دلار", "اقتصاد جهانی"],
    "بازارهای مالی و سرمایه‌گذاری": ["بورس", "بازار سرمایه", "سهام", "صندوق سرمایه گذاری", "صندوق سرمایه‌گذاری", "صندوق اهرمی", "شاخص کل", "اوراق", "سرمایه گذاری", "سرمایه‌گذاری", "بازارهای مالی", "سهام عدالت", "رمزارز", "بیت کوین", "بیت‌کوین", "بازار سهام"],
    "سیاست و روابط بین‌الملل": ["روابط بین الملل", "روابط بین‌الملل", "سیاست خارجی", "دیپلماسی", "تحریم", "انتخابات", "حکومت", "جمهوری اسلامی", "ایالات متحده", "آمریکا", "روسیه", "چین", "اسرائیل", "اوکراین", "عراق", "سوریه", "افغانستان", "ترکیه", "ترامپ", "جنگ", "سیاست", "سیاسی", "مجلس", "دولت"],
    "تاریخ ایران و جهان": ["تاریخ معاصر", "تاریخ ایران", "تاریخ", "قاجار", "پهلوی", "مشروطه", "رضاشاه", "محمدرضاشاه", "ترکمانچای", "صفویه", "ساسانی", "هخامنشی", "انقلاب ۱۳۵۷", "انقلاب اسلامی", "جنگ ایران و عراق", "جنگ جهانی", "تاریخی", "تاریخچه"],
    "جامعه، فرهنگ و اندیشه": ["جامعه", "فرهنگ", "مغالطه", "فلسفه", "کتاب", "ادبیات", "روشنفکر", "روشنفکری", "دین", "مذهب", "حقوق بشر", "آزادی", "آموزش", "رسانه", "اخلاق", "عدالت", "زبان", "زنان", "خانواده", "نژادپرستی", "قانون", "اندیشه", "فرهنگی", "اجتماعی", "آذری", "آذربایجان"],
    "محیط‌زیست و منابع آب": ["محیط زیست", "محیط‌زیست", "کارون", "سد گتوند", "شوری آب", "خشکسالی", "ریزگرد", "آلودگی", "تغییرات آب و هوایی", "تغییر اقلیم", "دریاچه", "تالاب", "منابع طبیعی", "بحران آب", "منابع آب", "آب آشامیدنی"],
    "سفرنامه و جهانگردی": ["سفرنامه", "گردشگری", "جهانگردی", "نیوزیلند", "سنگاپور", "استرالیا", "هنگ کنگ", "هنگ‌کنگ", "مسافرت", "سفر به", "سفر", "گردشگر"],
    "فناوری و زندگی دیجیتال": ["فناوری", "هوش مصنوعی", "اینترنت", "شبکه اجتماعی", "تکنولوژی", "کامپیوتر", "مخابرات", "موبایل", "نرم افزار", "نرم‌افزار", "سخت افزار", "سخت‌افزار", "اندروید", "آیفون", "دیجیتال"],
}
TAGS = [
    ("اقتصاد ایران", "اقتصاد ایران"), ("نفت", "نفت و انرژی"), ("صادرات نفت", "صادرات نفت"),
    ("اقتصاد نفتی", "اقتصاد نفتی"), ("تورم", "تورم"), ("تحریم", "تحریم‌ها"),
    ("بورس", "بورس"), ("بازار سرمایه", "بازار سرمایه"), ("سرمایه گذاری", "سرمایه‌گذاری"),
    ("سرمایه‌گذاری", "سرمایه‌گذاری"), ("روسیه", "روسیه"), ("چین", "چین"),
    ("آمریکا", "ایالات متحده"), ("قاجار", "دوران قاجار"), ("پهلوی", "دوران پهلوی"),
    ("مشروطه", "انقلاب مشروطه"), ("ترکمانچای", "عهدنامه ترکمانچای"), ("فساد", "فساد اقتصادی"),
    ("توسعه اقتصادی", "توسعه اقتصادی"), ("تجارت خارجی", "تجارت خارجی"), ("کارون", "رود کارون"),
    ("سد گتوند", "سد گتوند"), ("مغالطه", "تفکر نقاد"), ("حقوق بشر", "حقوق بشر"),
    ("سفرنامه", "سفرنامه"), ("نیوزیلند", "نیوزیلند"), ("محیط زیست", "محیط‌زیست"),
    ("محیط‌زیست", "محیط‌زیست"), ("بانک مرکزی", "بانک مرکزی"), ("بودجه", "بودجه"),
    ("جنگ", "جنگ"), ("فرهنگ", "فرهنگ"), ("عدالت", "عدالت"),
]

def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", html.unescape(value or "")).lower()
    value = value.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک").replace("ـ", "")
    value = re.sub(r"[\u064b-\u065f\u0670]", "", value)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def read_scalar(front: str, key: str) -> str:
    m = re.search(rf"(?m)^{re.escape(key)}:\s*(.*?)\s*$", front)
    if not m:
        return ""
    try:
        return str(json.loads(m.group(1)))
    except (json.JSONDecodeError, TypeError):
        return m.group(1).strip('"').strip("'")

def score_terms(terms, title, summary, body):
    score = 0
    for raw in terms:
        term = normalize(raw)
        if term in title: score += 8
        if term in summary: score += 4
        count = body.count(term)
        if count: score += min(count, 3)
    return score

def main():
    counts, tag_counts = Counter(), Counter()
    changed, unclassified = 0, []
    files = sorted(POSTS.glob("*.md"))
    for path in files:
        original = path.read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", original, re.S)
        if not match: continue
        front, body = match.group(1), original[match.end():]
        title, summary = normalize(read_scalar(front, "title")), normalize(read_scalar(front, "summary"))
        plain = normalize(re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", body, flags=re.I | re.S))
        has_categories = bool(re.search(r"(?m)^categories\s*:", front))
        has_tags = bool(re.search(r"(?m)^tags\s*:", front))
        categories, tags = [], []

        if has_categories:
            m = re.search(r"(?m)^categories:\s*(\[.*\])\s*$", front)
            try: categories = json.loads(m.group(1)) if m else ["دسته‌بندی موجود"]
            except json.JSONDecodeError: categories = ["دسته‌بندی موجود"]
            if "یادداشت‌ها و جستارها" in categories:
                unclassified.append(f"- {path.name}: {read_scalar(front, 'title')}")
        else:
            ranked = sorted(((score_terms(terms, title, summary, plain), name) for name, terms in CATEGORIES.items()), reverse=True)
            best, name = ranked[0]
            if best < 4:
                categories = ["یادداشت‌ها و جستارها"]
                unclassified.append(f"- {path.name}: {read_scalar(front, 'title')}")
            else:
                categories = [name]
                if len(ranked) > 1 and ranked[1][0] >= 9 and ranked[1][0] >= best * .62:
                    categories.append(ranked[1][1])

        if has_tags:
            m = re.search(r"(?m)^tags:\s*(\[.*\])\s*$", front)
            try: tags = json.loads(m.group(1)) if m else ["برچسب موجود"]
            except json.JSONDecodeError: tags = ["برچسب موجود"]
            # CHATGPT: "water" alone is too broad to be a reliable SEO tag; keep it only with clear environmental context.
            if "بحران آب" in tags:
                env_terms = ["بحران آب", "کارون", "سد گتوند", "شوری آب", "خشکسالی", "ریزگرد", "محیط زیست", "محیط‌زیست", "منابع آب", "تالاب", "دریاچه"]
                explicit_context = any(normalize(term) in title or normalize(term) in summary for term in env_terms)
                if not explicit_context and "محیط‌زیست و منابع آب" not in categories:
                    tags = [tag for tag in tags if tag != "بحران آب"]
        else:
            ranked_tags = []
            for raw, label in TAGS:
                term = normalize(raw)
                points = (5 if term in title else 0) + (3 if term in summary else 0)
                count = plain.count(term)
                if count >= 2: points += min(count, 3)
                if points >= 3 and label not in [item[1] for item in ranked_tags]:
                    ranked_tags.append((points, label))
            ranked_tags.sort(key=lambda item: (-item[0], item[1]))
            tags = [label for _, label in ranked_tags[:4]]

        counts.update(categories); tag_counts.update(tags)
        updated_front = front
        if not has_categories:
            updated_front += "\ncategories: " + json.dumps(categories, ensure_ascii=False)
        if has_tags:
            # CHATGPT: write back the cleaned list only when removing the overly broad water tag.
            front_lines = updated_front.splitlines()
            for index, line in enumerate(front_lines):
                if line.startswith("tags:"):
                    try:
                        original_tag_values = json.loads(line.split(":", 1)[1].strip())
                    except json.JSONDecodeError:
                        original_tag_values = []
                    if "بحران آب" in original_tag_values and "بحران آب" not in tags:
                        front_lines[index] = "tags: " + json.dumps(tags, ensure_ascii=False)
                    break
            updated_front = "\n".join(front_lines)
        else:
            updated_front += "\ntags: " + json.dumps(tags, ensure_ascii=False)
        updated = "---\n" + updated_front + "\n---\n" + body
        if updated != original:
            path.write_text(updated, encoding="utf-8"); changed += 1

    lines = ["# SEO taxonomy report", "", f"- Markdown posts scanned: {len(files)}", f"- Files updated with taxonomy: {changed}", "- Categories use weighted title, summary, and body matches. Weak matches use the catch-all category.", "", "## Category distribution", ""]
    lines += [f"- {name}: {count}" for name, count in counts.most_common()]
    lines += ["", "## Most common assigned tags", ""]
    lines += [f"- {name}: {count}" for name, count in tag_counts.most_common(25)]
    lines += ["", "## Posts needing manual category review", ""]
    lines += unclassified[:100] or ["- None"]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Scanned {len(files)} posts; updated {changed}.")
    print("Category distribution:", dict(counts))
    print(f"Posts needing review: {len(unclassified)}")

if __name__ == "__main__":
    main()
