"""SQLite database manager for articles."""

import sqlite3  # used only for sqlite3.Row and the IntegrityError type
import aiosqlite  # async sqlite — keeps DB calls from blocking the event loop
from pathlib import Path
from typing import List, Dict
from datetime import datetime


class DatabaseManager:
    """Manages SQLite database for articles."""

    def __init__(self, db_path: str = "data/news_agent.db"):
        self.db_path = db_path
        # Make sure the parent folder (e.g. data/) exists before SQLite
        # creates the file. exist_ok=True = don't error if it's already there.
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            # IF NOT EXISTS makes this idempotent — safe to call on every startup.
            # url is UNIQUE: it's the de-dup guard so the same article can't be
            # inserted twice.
            await db.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    source TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    summary TEXT,
                    score INTEGER DEFAULT 0,
                    relevance_score INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indexes to speed up the columns we filter and sort on below.
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_source ON articles(source)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_published ON articles(published_at)
            """)

            await db.commit()

        print(f"✅ Database initialized: {self.db_path}")

    async def insert_article(self, article: Dict):
        """Insert article into database."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                # Parameterized query (the ? placeholders) — prevents SQL
                # injection; never build the values into the string by hand.
                # .get(...) gives optional fields a default instead of crashing
                # on a missing key.
                await db.execute(
                    """
                    INSERT INTO articles
                    (title, url, source, published_at, summary, score, relevance_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        article["title"],
                        article["url"],
                        article["source"],
                        article["published_at"],
                        article.get("summary", ""),
                        article.get("score", 0),
                        article.get("relevance_score", 0),
                    ),
                )
                await db.commit()
            except sqlite3.IntegrityError:
                # Duplicate URL hit the UNIQUE constraint — silently skip so
                # re-running the fetch pipeline stays safe.
                pass

    async def query_articles(self, source: str = None, limit: int = 50) -> List[Dict]:
        """Query articles from database."""
        # Build the query piece by piece: optional source filter, then always
        # newest-first with a row cap.
        query = "SELECT * FROM articles"
        params = []

        if source:
            query += " WHERE source = ?"
            params.append(source)

        query += " ORDER BY published_at DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            # row_factory = sqlite3.Row lets us access columns by name and turn
            # each row into a plain dict, so callers get clean dictionaries
            # instead of raw tuples.
            db.row_factory = sqlite3.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


# Test it
async def test_db():
    """Test database."""
    db = DatabaseManager()
    await db.initialize()

    # Insert test article
    await db.insert_article(
        {
            "title": "Test Article",
            "url": "https://test.com/article1",
            "source": "test",
            "published_at": datetime.now().isoformat(),
            "summary": "Test summary",
        }
    )

    # Query
    articles = await db.query_articles(limit=10)
    print(f"✅ Found {len(articles)} articles")
    for article in articles:
        print(f"  - {article['title']}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_db())
