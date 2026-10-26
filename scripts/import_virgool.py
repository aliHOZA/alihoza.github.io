#!/usr/bin/env python3
"""Import published Virgool HTML exports into Hugo content/posts."""
from __future__ import annotations
import argparse, html, json, re, zipfile
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "content" / "posts"
REPORT = ROOT / "reports" / "virgool-import-report.md"
FILE_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-----.*---(?P<id>[a-z0-9]+)\.html$")

class ArticleParser(HTMLParser):
    VOID = {"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_section = False
        self.content_tag = None
        self.depth = 0
        self.parts = []
        self.title = ""
        self.published = ""
        self.canonical = ""
        self.image_srcs = []
        self.title_depth = 0
        self.title_parts = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in {"title", "h1"} and not self.title and not self.title_depth:
            self.title_depth = 1
            self.title_parts = []
        if tag == "time" and a.get("datetime"):
            self.published = a["datetime"].strip()
        if tag == "a" and "p-canonical" in a.get("class", "").split():
            self.canonical = a.get("href", "")
        content_classes = set(a.get("class", "").lower().split())
        if not self.in_section and content_classes.intersection({"e-content", "article-content", "post-content", "article-body", "post-body", "article__content", "post__content"}):
            self.in_section = True
            self.content_tag = tag
            self.depth = 1
            self.parts.append(self.get_starttag_text())
            return
        if self.in_section:
            if tag == "img":
                self.image_srcs.append(a.get("src", ""))
            self.parts.append(self.get_starttag_text())
            if tag not in self.VOID:
                self.depth += 1
    def handle_endtag(self, tag):
        if self.in_section:
            self.parts.append(f"</{tag}>")
            if tag not in self.VOID:
                self.depth -= 1
            if tag == self.content_tag and self.depth <= 0:
                self.in_section = False
                self.content_tag = None
                self.depth = 0
        if self.title_depth and tag in {"h1", "title"}:
            if not self.title:
                self.title = " ".join("".join(self.title_parts).split())
            self.title_depth = 0
    def handle_data(self, data):
        if self.in_section:
            self.parts.append(html.escape(data, quote=False))
        if self.title_depth:
            self.title_parts.append(data)

def q(value):
    return json.dumps(value, ensure_ascii=False)

def parse_date(value, fallback):
    try:
        dt = datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError:
        dt = datetime.fromisoformat(fallback + "T12:00:00")
    return dt.isoformat(timespec="seconds") + ("+03:30" if dt.tzinfo is None else "")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", default="virgool-export-2026-01-06--ZtG.zip")
    args = ap.parse_args()
    archive = ROOT / args.archive
    if not archive.exists():
        raise SystemExit(f"Archive not found: {archive}")
    POSTS.mkdir(parents=True, exist_ok=True)
    existing_ids = set()
    for path in POSTS.glob("*.md"):
        m = re.search(r"([a-z0-9]{10,12})", path.stem)
        if m:
            existing_ids.add(m.group(1))
    imported = skipped = drafts = images = 0
    invalid, missing_image_posts = [], []
    external_hosts = Counter()
    with zipfile.ZipFile(archive) as zf:
        html_files = [n for n in zf.namelist() if n.lower().endswith(".html")]
        drafts = sum(Path(n).name.startswith("draft--") for n in html_files)
        for name in sorted(html_files):
            base = Path(name).name
            if base.startswith("draft--"):
                continue
            m = FILE_RE.match(base)
            if not m:
                invalid.append(base)
                continue
            post_id, day = m.group("id"), m.group("date")
            if post_id in existing_ids:
                skipped += 1
                continue
            raw = zf.read(name).decode("utf-8", errors="replace")
            article = ArticleParser()
            article.feed(raw)
            title = html.unescape(article.title.strip()) or base
            body = "".join(article.parts)
            if not body.strip():
                invalid.append(base + " (no e-content section)")
                continue
            plain = html.unescape(re.sub(r"<[^>]+>", " ", body))
            summary = re.sub(r"\s+", " ", plain).strip()[:240]
            date = parse_date(article.published, day)
            target = POSTS / f"{day}-{post_id}.md"
            if target.exists():
                skipped += 1
                continue
            front = (
                "---\n"
                f"title: {q(title)}\n"
                f"date: {q(date)}\n"
                f"summary: {q(summary)}\n"
                f"virgool_id: {q(post_id)}\n"
                f"original_url: {q(article.canonical)}\n"
                "draft: false\n"
                "---\n\n"
            )
            target.write_text(front + body + "\n", encoding="utf-8")
            imported += 1
            for src in article.image_srcs:
                images += 1
                if not src.strip():
                    missing_image_posts.append((title, target.as_posix().replace(str(ROOT) + "/", "")))
                elif urlparse(src).netloc:
                    external_hosts[urlparse(src).netloc] += 1
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Virgool import report", "",
        f"- Published HTML files in archive: {len(html_files) - drafts}",
        f"- Imported in this run: {imported}",
        f"- Skipped because already present: {skipped}",
        f"- Draft files intentionally excluded: {drafts}",
        f"- Images referenced by imported posts: {images}",
        f"- External image hosts preserved: {len(external_hosts)}",
        f"- Images missing a src attribute: {len(missing_image_posts)}",
        f"- Files that could not be imported: {len(invalid)}", "",
        "## External image hosts", ""
    ]
    lines += [f'- "{host}" — {count} image reference(s)' for host, count in external_hosts.most_common()]
    lines += ["", "## Posts with missing image sources", ""]
    lines += [f"- {title} ({path})" for title, path in missing_image_posts]
    lines += ["", "## Unimported files", ""]
    lines += [f"- {item}" for item in invalid]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Imported {imported}; skipped existing {skipped}; excluded drafts {drafts}; invalid {len(invalid)}.")

if __name__ == "__main__":
    main()
