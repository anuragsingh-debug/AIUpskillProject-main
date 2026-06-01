"""Save articles to markdown files."""

from pathlib import Path
from typing import List
from datetime import datetime
from src.models.article import Article


class MarkdownStorage:
    """
    Saves articles to markdown files.

    Creates files in data/articles/ directory.
    """

    def __init__(self, base_path: str = "data/articles"):
        """
        Initialize storage.

        Args:
            base_path: Directory to save articles
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, articles: List[Article], filename: str = None) -> Path:
        """
        Save articles to markdown file.

        Args:
            articles: List of articles to save
            filename: Optional filename, auto-generated if not provided

        Returns:
            Path to saved file
        """
        if filename is None:
            # Auto-generate filename with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            filename = f"articles_{timestamp}.md"

        filepath = self.base_path / filename

        # Write articles to file
        with open(filepath, "w", encoding="utf-8") as f:
            # Header
            f.write("# News Articles\n\n")
            f.write(
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )
            f.write(f"**Total Articles:** {len(articles)}\n\n")
            f.write("---\n\n")

            # Articles
            for article in articles:
                f.write(article.to_markdown())
                f.write("\n---\n\n")

        print(f"💾 Saved {len(articles)} articles to: {filepath}")
        return filepath


# Test it
if __name__ == "__main__":
    from src.models.article import Article

    # Create test article
    test_article = Article(
        title="Test Article",
        url="https://example.com",
        published_at=datetime.now(),
        source="test",
        summary="This is a test article.",
    )

    # Save it
    storage = MarkdownStorage()
    path = storage.save([test_article], "test.md")

    # Verify
    assert path.exists()
    print(f"✅ Saved to: {path}")
    print("✅ File contents:")
    print(path.read_text()[:200])
