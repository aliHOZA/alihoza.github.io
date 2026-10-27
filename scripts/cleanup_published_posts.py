#!/usr/bin/env python3
"""Clean imported Virgool recommendation blocks and localize links to known posts."""
from __future__ import annotations
import html, re, unicodedata
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "content" / "posts"
REPORT = ROOT / "reports" / "post-cleanup-report.md"
TAG_RE = re.compile(r"<[^>]+>")
HEADING_RE = re.compile(r"(?is)<h([1-6])\b[^>]*>(.*?)</h\1\s*>")
HREF_RE = re.compile(r"""(?is)(\bhref\s*=\s*)(["'])(.*?)\2""")
VIRGOOL_RE = re.compile(r"(?:https?://)?(?:www\.)?virgool\.io/", re.I)
RAW_URL_RE = re.compile(r"""https?://(?:www\.)?(?:virgool\.io|vrgl\.ir)/[^\s<>\\"']+""", re.I)
SHORT_LINKS = {"https://vrgl.ir/qofQV": "ruqoesirf9vj"}

def normalize_heading(value: str) -> str:
    value = html.unescape(TAG_RE.sub(" ", value))
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    value = value.replace("\u200c", "").replace("\u200f", "").replace("\ufeff", "")
    value = re.sub(r"\s+", " ", value).strip()
    return re.sub(r"[：:!！.،؛\-–—]+$", "", value).strip()

def split_front_matter(text: str) -> tuple[str, str]:
    match = re.match(r"\A(---\s*\n.*?\n---\s*\n)", text, re.S)
    return (match.group(1), text[match.end():]) if match else ("", text)

def remove_recommendation_blocks(body: str) -> tuple[str, int]:
    removed = 0
    while True:
        match = next((m for m in HEADING_RE.finditer(body)
                      if normalize_heading(m.group(2)) == "سایر مطالب"), None)
        if not match:
            break
        start = match.start()
        hr = re.search(r"(?is)(?:<hr\b[^>]*>\s*(?:</hr>\s*)*)\s*$", body[:start])
        if hr:
            start = hr.start()
        closing = re.search(r"(?is)</section\s*>", body[match.end():])
        end = match.end() + closing.start() if closing else len(body)
        body = body[:start] + "\n" + body[end:]
        removed += 1
    return body, removed

def main() -> None:
    files = sorted(POSTS.glob("*.md"))
    id_to_url: dict[str, str] = {}
    for path in files:
        front, _ = split_front_matter(path.read_text(encoding="utf-8"))
        m = re.search(r'(?m)^virgool_id:\s*["\']?([a-z0-9]{10,16})', front)
        post_id = m.group(1) if m else None
        if not post_id:
            m = re.search(r"([a-z0-9]{10,16})$", path.stem)
            post_id = m.group(1) if m else None
        if post_id:
            id_to_url[post_id] = f"https://alihoza.github.io/posts/{path.stem}/"

    changed_posts = blocks_removed = links_rewritten = scanned = 0
    rewritten_urls: set[str] = set()
    for path in files:
        original = path.read_text(encoding="utf-8")
        front, body = split_front_matter(original)
        body, removed = remove_recommendation_blocks(body)
        local_links_this_post = 0
        def rewrite_href(match: re.Match[str]) -> str:
            nonlocal links_rewritten, local_links_this_post
            raw_url = html.unescape(match.group(3)).strip()
            if not VIRGOOL_RE.search(raw_url):
                return match.group(0)
            decoded = unquote(raw_url)
            parsed = urlparse(decoded if decoded.startswith(("http://", "https://")) else "https://" + decoded)
            path_part = parsed.path.rstrip("/")
            for post_id, local_url in id_to_url.items():
                if re.search(rf"(?:/|-){re.escape(post_id)}$", path_part):
                    links_rewritten += 1
                    local_links_this_post += 1
                    rewritten_urls.add(raw_url)
                    replacement = local_url + (("#" + parsed.fragment) if parsed.fragment else "")
                    return match.group(1) + match.group(2) + html.escape(replacement, quote=True) + match.group(2)
            return match.group(0)
        body = HREF_RE.sub(rewrite_href, body)
        # Also localize raw Virgool URLs in imported embed blocks and standalone text.
        def rewrite_raw_url(match: re.Match[str]) -> str:
            original_url = match.group(0)
            suffix = ""
            while original_url and original_url[-1] in ".,;:!?،؛؟)]}":
                suffix = original_url[-1] + suffix
                original_url = original_url[:-1]
            parsed = urlparse(original_url)
            short_key = f"https://{parsed.netloc.lower()}{parsed.path}"
            post_id = SHORT_LINKS.get(short_key)
            if not post_id and re.search(r"virgool\.io", parsed.netloc, re.I):
                decoded_path = unquote(parsed.path).rstrip("/")
                for known_id in id_to_url:
                    if re.search(rf"(?:/|-){re.escape(known_id)}$", decoded_path):
                        post_id = known_id
                        break
            if post_id and post_id in id_to_url:
                rewritten_urls.add(original_url)
                return id_to_url[post_id] + suffix
            return match.group(0)
        body = RAW_URL_RE.sub(rewrite_raw_url, body)
        updated = front + body
        scanned += 1
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed_posts += 1
            blocks_removed += removed
            print(f"Updated {path.relative_to(ROOT)}: removed {removed} recommendation block(s), rewrote {local_links_this_post} links")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Post cleanup report\n\n"
        f"- Posts scanned: {scanned}\n- Posts changed: {changed_posts}\n"
        f"- “سایر مطالب” blocks removed: {blocks_removed}\n"
        f"- Virgool links converted to local post URLs: {links_rewritten}\n"
        f"- Distinct source URLs converted: {len(rewritten_urls)}\n"
        f"- Local URL pattern: https://alihoza.github.io/posts/<post-filename>/\n",
        encoding="utf-8",
    )
    print(f"Scanned {scanned}; changed {changed_posts}; removed {blocks_removed} blocks; rewrote {links_rewritten} links.")

if __name__ == "__main__":
    main()
