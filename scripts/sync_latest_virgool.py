#!/usr/bin/env python3
"""Import the newest published posts from the author's live Virgool profile."""
from __future__ import annotations
import re, time
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin, urlparse, unquote
from urllib.request import Request, urlopen
from import_virgool import ArticleParser, parse_date, POSTS, q

PROFILE = "https://virgool.io/@mrali"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128 Safari/537.36"
POST_PATH = re.compile(r"^/@mrali/.+-([a-z0-9]{10,12})/?$", re.I)
ROOT = Path(__file__).resolve().parents[1]

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href:
                self.hrefs.append(href)

def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7"})
    with urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")

def main() -> None:
    POSTS.mkdir(parents=True, exist_ok=True)
    profile_html = ""
    last_error = None
    for attempt in range(3):
        try:
            profile_html = fetch(PROFILE)
            break
        except (URLError, HTTPError, TimeoutError) as exc:
            last_error = exc
            time.sleep(2 * (attempt + 1))
    if not profile_html:
        raise SystemExit(f"Could not fetch Virgool profile after retries: {last_error}")

    parser = Links()
    parser.feed(profile_html)
    candidates, seen = [], set()
    for href in parser.hrefs:
        absolute = urljoin(PROFILE, href)
        path = unquote(urlparse(absolute).path)
        match = POST_PATH.match(path)
        if not match:
            continue
        post_id = match.group(1).lower()
        if post_id not in seen:
            seen.add(post_id)
            candidates.append((post_id, absolute.split("?")[0]))
    candidates = candidates[:30]
    if not candidates:
        raise SystemExit("No recognizable post links found on Virgool profile.")

    existing_ids = set()
    for path in POSTS.glob("*.md"):
        match = re.search(r"([a-z0-9]{10,12})", path.stem, re.I)
        if match:
            existing_ids.add(match.group(1).lower())

    imported = skipped = failed = 0
    failures = []
    for post_id, url in candidates:
        if post_id in existing_ids:
            skipped += 1
            continue
        try:
            raw, last_error = "", None
            for attempt in range(2):
                try:
                    raw = fetch(url)
                    break
                except (URLError, HTTPError, TimeoutError) as exc:
                    last_error = exc
                    time.sleep(attempt + 1)
            if not raw:
                raise RuntimeError(f"fetch failed: {last_error}")
            article = ArticleParser()
            article.feed(raw)
            body = "".join(article.parts)
            if not body.strip():
                raise RuntimeError("no section.e-content found")
            title = re.sub(r"\s*(?:[-|–]\s*)?ویرگول\s*$", "", article.title.strip()).strip() or post_id
            if not article.published:
                raise RuntimeError("no publication time found in article HTML")
            date = parse_date(article.published, article.published[:10])
            dt = datetime.fromisoformat(date)
            target = POSTS / f"{dt.date().isoformat()}-{post_id}.md"
            if target.exists():
                skipped += 1
                existing_ids.add(post_id)
                continue
            canonical = article.canonical or url
            plain = re.sub(r"<[^>]+>", " ", body)
            plain = re.sub(r"\s+", " ", plain).strip()
            summary = plain[:240]
            front = (
                "---\n" + f"title: {q(title)}\n" + f"date: {q(date)}\n"
                + f"summary: {q(summary)}\n" + f"virgool_id: {q(post_id)}\n"
                + f"original_url: {q(canonical)}\n" + "draft: false\n---\n\n"
            )
            target.write_text(front + body + "\n", encoding="utf-8")
            imported += 1
            existing_ids.add(post_id)
            print(f"Imported: {title} ({target.name})")
        except Exception as exc:
            failed += 1
            failures.append(f"{post_id} {url}: {exc}")
            print(f"WARNING: failed to import {post_id}: {exc}")
    report = ROOT / "reports" / "virgool-live-sync-report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# Live Virgool sync report\n\n" + f"- Profile: {PROFILE}\n"
        + f"- Recent posts inspected: {len(candidates)}\n- Imported: {imported}\n"
        + f"- Already present: {skipped}\n- Failed: {failed}\n\n## Failures\n\n"
        + ("\n".join(f"- {item}" for item in failures) if failures else "None") + "\n",
        encoding="utf-8"
    )
    print(f"Live Virgool sync: imported {imported}; already present {skipped}; failed {failed}.")
    if failed and not imported and skipped == 0:
        raise SystemExit("No post was imported and no existing post was found; inspect the report.")

if __name__ == "__main__":
    main()
