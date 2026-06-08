# populate_db.py
# One-time loader: reads the markdown files under data/articles/ and imports
# each article into the SQLite database. Safe to re-run — insert_article skips
# duplicate URLs, so nothing gets inserted twice.
import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path

from src.database.db_manager import DatabaseManager

# Windows cp1252 console can't print the ✅ emoji that db_manager.py uses —
# force UTF-8 so the status prints don't crash (same E2 fix as the agents).
sys.stdout.reconfigure(encoding="utf-8")


async def populate_from_markdown():
    """Populate database from markdown files."""
    db = DatabaseManager()
    await db.initialize()  # create the table if it doesn't exist yet

    # Read articles from markdown
    articles_dir = Path("data/articles")

    # Walk every .md file in the folder, one at a time.
    for md_file in articles_dir.glob("*.md"):
        print(f"Reading {md_file.name}...")
        # Read as UTF-8 explicitly — the default on Windows is cp1252, which
        # chokes on non-Latin bytes in the article text (E2 on the file boundary).
        content = md_file.read_text(encoding="utf-8")

        # Simple parsing: split the file into sections on the --- separator,
        # so each section holds one article.
        sections = content.split("---")

        for section in sections:
            # Skip anything without a heading — it's not an article block.
            if "##" not in section:
                continue

            # Extract title from the "## Title" line.
            title_match = re.search(r"## (.+)", section)
            if not title_match:
                continue
            title = title_match.group(1).strip()

            # Extract URL — required. No URL = skip this section.
            url_match = re.search(r"\*\*URL:\*\* (.+)", section)
            if not url_match:
                continue
            url = url_match.group(1).strip()

            # Extract source — optional, fall back to 'unknown' if missing.
            source_match = re.search(r"\*\*Source:\*\* (.+)", section)
            source = source_match.group(1).strip() if source_match else "unknown"

            # Use the last non-empty, non-bold line as the summary.
            lines = [
                ln
                for ln in section.split("\n")
                if ln.strip() and not ln.startswith("**")
            ]
            summary = lines[-1] if lines else ""

            # Insert into the DB. published_at is set to "now" because the
            # markdown doesn't carry a real publish date.
            await db.insert_article(
                {
                    "title": title,
                    "url": url,
                    "source": source,
                    "published_at": datetime.now().isoformat(),
                    "summary": summary,
                }
            )

    # Check count — read everything back to confirm how much landed.
    articles = await db.query_articles(limit=1000)
    print(f"\n✅ Database populated with {len(articles)} articles")


if __name__ == "__main__":
    asyncio.run(populate_from_markdown())
