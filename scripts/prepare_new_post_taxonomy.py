#!/usr/bin/env python3
"""Apply the site's existing taxonomy logic to newly imported posts only."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "content" / "posts"
TAXONOMY_SCRIPT = ROOT / "scripts" / "enrich_taxonomy.py"
REPORT = ROOT / "reports" / "new-post-taxonomy-report.md"


def main() -> int:
    result = subprocess.run(
        [
            "git", "ls-files", "--others", "--exclude-standard",
            "--", "content/posts",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    new_posts = [
        ROOT / line.strip()
        for line in result.stdout.splitlines()
        if line.strip().endswith(".md")
        and (ROOT / line.strip()).is_file()
        and (ROOT / line.strip()).name != "_index.md"
    ]

    if not new_posts:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(
            "# Taxonomy report for newly imported posts\n\n"
            "- No new Markdown posts detected.\n",
            encoding="utf-8",
        )
        print("No new posts to categorize.")
        return 0

    with tempfile.TemporaryDirectory(prefix="virgool-taxonomy-") as temp:
        temp_posts = Path(temp) / "posts"
        temp_posts.mkdir()

        for post in new_posts:
            shutil.copy2(post, temp_posts / post.name)

        spec = importlib.util.spec_from_file_location(
            "site_taxonomy", TAXONOMY_SCRIPT
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load the existing taxonomy script.")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Reuse the site's existing rules, scoped to temporary copies.
        module.POSTS = temp_posts
        module.REPORT = REPORT
        module.main()

        for post in new_posts:
            shutil.copy2(temp_posts / post.name, post)

    print(f"Applied taxonomy to {len(new_posts)} newly imported posts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
