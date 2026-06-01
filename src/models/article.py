# dataclass = auto-writes __init__, __repr__ etc. for us, so we don't type them by hand.
from dataclasses import dataclass

# datetime = the type we use for the article's publish time.
from datetime import datetime


@dataclass
class Article:
    """
    Represents a news article.

    Using dataclass for automatic __init__, __repr__, etc.
    """

    # These are the "fields". dataclass turns them into __init__ arguments.
    title: str  # headline of the article (required)
    url: str  # link to the article (required)
    published_at: datetime  # when it was published
    source: str  # where it came from, e.g. "hackernews"
    summary: str = ""  # short text; "= " means it's optional (default empty)
    score: int = 0  # upvotes/points; optional, defaults to 0

    def __post_init__(self):
        """Runs automatically right after __init__ — good place to check data."""
        # Don't allow an article with no title.
        if not self.title:
            raise ValueError("Article must have a title.")
        # Don't allow an article with no URL.
        if not self.url:
            raise ValueError("Article must have a URL.")

    def to_markdown(self) -> str:
        """Build a markdown string from this one article's fields."""
        # f-strings let us drop self.<field> values straight into the text.
        return (
            f"### [{self.title}]({self.url})\n\n"
            f"**Source:** {self.source}\n\n"
            f"**Published At:** {self.published_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"**Score:** {self.score}\n\n"
            f"{self.summary}"
        )


# This block only runs when you do `python src/models/article.py` directly.
# It is skipped when another file does `from src.models.article import Article`.
if __name__ == "__main__":
    # Make one sample article to check things work.
    article = Article(
        title="Sample Article",
        url="https://example.com/sample-article",
        published_at=datetime.now(),  # current date/time
        source="Example News",
    )

    print(article.to_markdown())  # show it as markdown
    print("Article Model Works!")  # simple "it ran" confirmation
