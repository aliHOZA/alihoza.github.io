#!/usr/bin/env python3
"""Build content-based related-post rankings using TF-IDF cosine similarity.

Input is Hugo's generated index.json, so URLs and rendered article text match
the actual published site. The script uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

# Common Persian function words and editorial filler; kept small and transparent.
STOP_WORDS = set("""
از با به برای بر در را که و یا اگر اما ولی تا چون هم نیز هر همه این آن
اینکه آنکه یک دو چند بسیار بیشتر کمتر شده شود هستند است بود باشد می من ما
تو شما ایشان او آنها خود خودشان پس پیش بعد قبل میان درباره مورد نسبت طریق
عنوان مطلب مقاله نوشته گزارش بررسی تحلیل بخش قسمت نکته نکات نتیجه نتایج
امروز دیروز اکنون همچنین البته مثلا مثلاى چرا چگونه کدام چه کسی کسانی چیزی
های هایش شان تر ترین می‌شود نمی‌شود شده‌اند می‌کند کردند دارد دارند داشت
خواهد خواهند باید شاید ممکن استند بوده بودند هستند نیست نیستند بوسیله
ایران ایرانی کشور کشورهای جهان سال سالی سالها ماه روز زمان دوره دوران
بر اساس یکدیگر آنچه همان دیگر دیگران جدید تازه نخست دوم اول آخر اصلی کلی
""".split())

TOKEN_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FFa-zA-Z0-9]+")


def normalize(text: str) -> str:
    text = text.lower().translate(str.maketrans({
        "ي": "ی", "ى": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه",
        "ؤ": "و", "إ": "ا", "أ": "ا", "ٱ": "ا",
    }))
    return re.sub(r"[\u064B-\u065F\u0670\u0640]", "", text)


def tokens(text: str) -> list[str]:
    return [
        token for token in TOKEN_RE.findall(normalize(text))
        if len(token) > 1 and token not in STOP_WORDS
    ]


def weighted_terms(post: dict) -> Counter[str]:
    # Titles are deliberately weighted more heavily than summaries and body text.
    result: Counter[str] = Counter()
    result.update({term: count * 3 for term, count in Counter(tokens(post.get("title", ""))).items()})
    result.update({term: count * 2 for term, count in Counter(tokens(post.get("summary", ""))).items()})
    result.update(Counter(tokens(post.get("content", ""))))
    return result


def build_rankings(posts: list[dict], limit: int = 12) -> dict[str, list[str]]:
    documents = [weighted_terms(post) for post in posts]
    doc_count = len(documents)
    document_frequency: Counter[str] = Counter()
    for document in documents:
        document_frequency.update(document.keys())

    vectors: list[dict[str, float]] = []
    norms: list[float] = []
    for document in documents:
        vector = {
            term: (1.0 + math.log(count)) *
                  (math.log((1 + doc_count) / (1 + document_frequency[term])) + 1.0)
            for term, count in document.items()
        }
        vectors.append(vector)
        norms.append(math.sqrt(sum(value * value for value in vector.values())))

    rankings: dict[str, list[str]] = {}
    for i, post in enumerate(posts):
        scored: list[tuple[float, str]] = []
        for j, candidate in enumerate(posts):
            if i == j:
                continue
            if not norms[i] or not norms[j]:
                continue
            # Iterate over the smaller vector for an efficient sparse dot product.
            left, right = (vectors[i], vectors[j]) if len(vectors[i]) <= len(vectors[j]) else (vectors[j], vectors[i])
            dot = sum(value * right.get(term, 0.0) for term, value in left.items())
            score = dot / (norms[i] * norms[j])
            if score > 0:
                scored.append((score, candidate.get("url", "")))
        scored.sort(key=lambda item: (-item[0], item[1]))
        rankings[post.get("url", "")] = [url for _, url in scored[:limit] if url]
    return rankings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, help="Path to Hugo's generated index.json")
    parser.add_argument("--output", required=True, help="Output JSON file (normally data/related-posts.json)")
    parser.add_argument("--limit", type=int, default=12, help="Candidates per article (default: 12)")
    args = parser.parse_args()

    source = Path(args.index)
    output = Path(args.output)
    if args.limit < 4:
        parser.error("--limit must be at least 4")

    try:
        posts = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Cannot read Hugo index {source}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(posts, list) or len(posts) < 2:
        print("Hugo index must contain at least two published posts.", file=sys.stderr)
        return 1

    posts = [
        post for post in posts
        if isinstance(post, dict) and post.get("url") and post.get("title")
    ]
    urls = [post["url"] for post in posts]
    if len(urls) != len(set(urls)):
        print("Hugo index contains duplicate post URLs; refusing to generate rankings.", file=sys.stderr)
        return 1

    rankings = build_rankings(posts, args.limit)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(rankings, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    # Lightweight integrity checks: every key is a published post, no self-links,
    # no duplicates, and every recommendation points to a published post.
    published = set(urls)
    for url, recommendations in rankings.items():
        if url not in published or url in recommendations:
            print(f"Invalid related-post entry for {url}", file=sys.stderr)
            return 1
        if len(recommendations) != len(set(recommendations)) or not set(recommendations) <= published:
            print(f"Invalid recommendations for {url}", file=sys.stderr)
            return 1

    print(f"Generated TF-IDF rankings for {len(rankings)} posts at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
