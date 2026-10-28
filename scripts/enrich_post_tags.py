#!/usr/bin/env python3
"""Rebuild tags for every Hugo post from the controlled topic vocabulary.

Existing tags are intentionally discarded. Only relevant shared topics occurring
in at least five posts in the current corpus can be assigned, with up to five tags
per post. The script can run in CI or in a content-preparation workflow.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

POSTS_DIR = Path("content/posts")
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)
TITLE_RE = re.compile(r"(?m)^title:\s*(.*?)\s*$")
TAG_LINE_RE = re.compile(r"(?m)^tags:\s*(.*?)\s*$")
CATEGORY_LINE_RE = re.compile(r"(?m)^categories:\s*(.*?)\s*$")
QUOTED_RE = re.compile(r"""['"]([^'"]+)['"]""")

# Labels and representative words/phrases. Keep this vocabulary broad enough
# for genuine cross-post discovery, but do not assign one-off, article-specific tags.
TOPICS = [
    ("اقتصاد ایران", r"اقتصاد ایران|اقتصاد کشور|اقتصاد ملی|اقتصاد داخلی"),
    ("نفت و انرژی", r"نفت|گاز طبیعی|انرژی|پالایشگاه|پتروشیمی|اوپک|برنت|نفت خام"),
    ("سیاست ایران", r"سیاست ایران|سیاست داخلی|دولت ایران|مجلس شورای اسلامی|حکومت ایران"),
    ("تاریخ معاصر ایران", r"تاریخ معاصر|تاریخ ایران|دوران قاجار|دوران پهلوی|مشروطه|رضاشاه|محمدرضا شاه"),
    ("روابط ایران و آمریکا", r"ایران و آمریکا|ایران-آمریکا|ایران و ایالات متحده|آمریکا و ایران"),
    ("تحریم‌ها", r"تحریم|تحریم‌های اقتصادی|تحریم نفتی"),
    ("توسعه اقتصادی", r"توسعه اقتصادی|رشد اقتصادی|توسعه صنعتی|توسعه کشور"),
    ("تورم", r"تورم|گرانی|شاخص قیمت مصرف‌کننده|قدرت خرید"),
    ("بازار سرمایه", r"بازار سرمایه|بورس|سهام|فرابورس|شاخص کل"),
    ("صادرات نفت", r"صادرات نفت|صادرات نفتی|صادرات گاز|صادرات انرژی"),
    ("تجارت خارجی", r"تجارت خارجی|واردات|صادرات غیرنفتی|تراز تجاری"),
    ("فساد اقتصادی", r"فساد اقتصادی|رانت|اختلاس|تعارض منافع"),
    ("اقتصاد نفتی", r"اقتصاد نفتی|درآمدهای نفتی|وابستگی به نفت|بودجه نفتی"),
    ("روسیه", r"روسیه|مسکو|کرملین"),
    ("چین", r"چین|پکن|اقتصاد چین"),
    ("جنگ و صلح", r"جنگ|صلح|درگیری نظامی|جنگ ایران و عراق"),
    ("جامعه و فرهنگ", r"جامعه|فرهنگ|جامعه‌شناسی|سبک زندگی"),
    ("حقوق و عدالت", r"حقوق بشر|عدالت اجتماعی|قوه قضائیه|حقوق شهروندی"),
    ("آب و محیط زیست", r"محیط زیست|منابع آب|بحران آب|خشکسالی|آلودگی هوا"),
    ("بودجه و یارانه", r"بودجه|یارانه|کسری بودجه|هزینه‌های دولت"),
    ("بانک مرکزی", r"بانک مرکزی|سیاست پولی|پایه پولی|نقدینگی"),
    ("صنعت و تولید", r"صنعت|تولید صنعتی|بنگاه تولیدی|کارخانه|زنجیره تأمین"),
    ("شرکت‌های دانش‌بنیان", r"دانش‌بنیان|شرکت دانش بنیان|اقتصاد دانش‌بنیان|نوآوری و شکوفایی"),
    ("سرمایه‌گذاری", r"سرمایه‌گذاری|سرمایه‌گذار|سرمایه‌گذاری خارجی"),
    ("بازار کار", r"بازار کار|اشتغال|بیکاری|دستمزد|حداقل دستمزد"),
    ("مسکن", r"مسکن|اجاره‌بها|قیمت خانه|بازار املاک"),
    ("حمل‌ونقل", r"حمل‌ونقل|راه‌آهن|کشتیرانی|ترانزیت|بنادر"),
    ("امنیت ملی", r"امنیت ملی|امنیت منطقه‌ای|دفاعی|نیروهای مسلح"),
    ("رسانه و مطبوعات", r"رسانه|مطبوعات|خبرگزاری|روزنامه‌نگاری"),
    ("انتخابات", r"انتخابات|رأی‌دهندگان|رأی‌گیری|نامزد انتخاباتی"),
    ("فناوری و اینترنت", r"فناوری|اینترنت|هوش مصنوعی|شبکه‌های اجتماعی|دیجیتال"),
]
def normalize_text(value: str) -> str:
    value = value.replace("\u200c", " ").replace("\u200d", " ")
    value = value.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    value = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def compile_topic_pattern(pattern: str) -> re.Pattern[str]:
    # TOPICS uses pipe-separated literal phrases, not arbitrary regex fragments.
    alternatives = [normalize_text(part.strip()) for part in pattern.split("|") if part.strip()]
    escaped = "|".join(re.escape(part) for part in alternatives)
    return re.compile(r"(?<![\w])(?:" + escaped + r")(?![\w])", re.I)


COMPILED_TOPICS = [(label, compile_topic_pattern(pattern)) for label, pattern in TOPICS]


def parse_list(value: str | None) -> list[str]:
    if not value or value in ("[]", "null", "~"):
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except (json.JSONDecodeError, TypeError):
        pass
    return [item.strip() for item in QUOTED_RE.findall(value) if item.strip()]


def get_frontmatter_value(front: str, pattern: re.Pattern[str]) -> list[str]:
    match = pattern.search(front)
    return parse_list(match.group(1)) if match else []


def topic_is_relevant(record: dict, pattern: re.Pattern[str]) -> bool:
    """Reject incidental mentions: title/category/summary evidence or repeated body evidence."""
    if pattern.search(record["title"]):
        return True
    if pattern.search(" ".join(record["categories"])):
        return True
    if pattern.search(record["summary"]):
        return True
    return len(list(pattern.finditer(record["text"]))) >= 2


def main() -> None:
    files = sorted(p for p in POSTS_DIR.glob("*.md") if p.name != "_index.md")
    records = []
    for path in files:
        raw = path.read_text(encoding="utf-8")
        match = FRONT_MATTER.match(raw)
        if not match:
            continue
        front = match.group(1)
        body = raw[match.end():]
        title_match = TITLE_RE.search(front)
        title = title_match.group(1).strip().strip("'\"") if title_match else path.stem
        # Existing tags are deliberately ignored so stale labels cannot survive.
        categories = get_frontmatter_value(front, CATEGORY_LINE_RE)
        text = re.sub(r"<[^>]+>", " ", body)
        text = re.sub(r"https?://\S+", " ", text)
        text = re.sub(r"!?(?:\[[^\]]*\])\([^)]*\)", " ", text)
        text = normalize_text(text)
        title = normalize_text(title)
        categories = [normalize_text(item) for item in categories]
        summary_match = re.search(r"(?m)^summary:\s*(.*?)\s*$", front)
        summary = normalize_text(summary_match.group(1).strip("'").strip('"') if summary_match else "")
        records.append({
            "path": path, "raw": raw, "front": front, "body": body,
            "title": title, "summary": summary, "categories": categories,
            "text": text,
        })

    # A candidate must be relevant to at least five separate posts.
    topic_counts = Counter()
    for record in records:
        for label, pattern in COMPILED_TOPICS:
            if topic_is_relevant(record, pattern):
                topic_counts[label] += 1

    updated = 0
    under_tagged = []
    for record in records:
        title = record["title"]
        text = record["text"]
        candidates: dict[str, int] = {}

        for label, pattern in COMPILED_TOPICS:
            if topic_counts[label] < 5 or not topic_is_relevant(record, pattern):
                continue
            score = 1
            if pattern.search(title):
                score += 30
            if pattern.search(" ".join(record["categories"])):
                score += 12
            if pattern.search(record["summary"]):
                score += 8
            if pattern.search(text[:3000]):
                score += 4
            candidates[label] = max(candidates.get(label, 0), score + topic_counts[label] / 1000)

        # Rebuild tags from scratch; never carry forward existing labels.
        chosen = [
            tag for tag, _score in sorted(
                candidates.items(), key=lambda pair: (-pair[1], pair[0])
            )[:5]
        ]

        if len(chosen) < 3:
            under_tagged.append((record["path"].name, len(chosen)))
        front = record["front"]
        rendered_tags = "tags: " + json.dumps(chosen, ensure_ascii=False)
        if TAG_LINE_RE.search(front):
            front = TAG_LINE_RE.sub(lambda _: rendered_tags, front, count=1)
        else:
            front += "\n" + rendered_tags
        new_raw = "---\n" + front + "\n---\n" + record["body"]
        if new_raw != record["raw"]:
            record["path"].write_text(new_raw, encoding="utf-8")
            updated += 1

    print(f"Tag enrichment: scanned {len(records)} posts; updated {updated}; "
          f"{len(under_tagged)} post(s) have fewer than three valid shared tags.")
    if under_tagged:
        print("Review needed (first 30): " + ", ".join(f"{name} ({count})" for name, count in under_tagged[:30]))


if __name__ == "__main__":
    main()
