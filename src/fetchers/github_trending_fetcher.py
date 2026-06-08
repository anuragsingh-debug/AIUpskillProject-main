"""Fetch from GitHub Trending."""

from src.fetchers.base_fetcher import BaseFetcher  # the shared contract (the "socket")
from typing import List  # for the List[Article] type hint
import aiohttp  # async HTTP client, used to download the page
from bs4 import BeautifulSoup  # library that reads / parses HTML
from datetime import datetime  # to set a published_at time
from src.models.article import Article  # our standard data object


class GitHubTrendingFetcher(BaseFetcher):
    """
    Fetch trending repositories from GitHub.

    NEW fetcher - demonstrates Open/Closed Principle.
    Added WITHOUT modifying any existing code!
    """

    async def fetch_articles(self) -> List[Article]:
        """Scrape the GitHub trending page and return Article objects."""
        url = "https://github.com/trending"  # GitHub has no API, so we scrape this page

        async with aiohttp.ClientSession() as session:  # open one HTTP session
            async with session.get(url) as response:  # request the trending page
                html = await response.text()  # read the response body as text (HTML)

        soup = BeautifulSoup(
            html, "html.parser"
        )  # turn raw HTML into a searchable tree
        repos = soup.select(
            "article.Box-row"
        )  # each repo row is an <article class="Box-row">

        articles = []  # collect the Article objects here
        for repo in repos[:20]:  # keep only the top 20 repos
            # Extract repo info
            title_elem = repo.select_one("h2 a")  # repo name + link lives in <h2><a>
            if not title_elem:  # this row has no link?
                continue  # skip it and move on (stay safe)

            title = (
                title_elem.text.strip().replace("\n", "").replace(" ", "")
            )  # clean "owner / repo" -> "owner/repo"
            href = title_elem["href"]  # the relative link, e.g. "/owner/repo"
            url = f"https://github.com{href}"  # build the full repo URL

            description_elem = repo.select_one(
                "p"
            )  # description sits in a <p> (may be missing)
            description = (
                description_elem.text.strip() if description_elem else ""
            )  # empty if none

            stars_elem = repo.select_one(
                "span.d-inline-block.float-sm-right"
            )  # star count element
            stars = (
                stars_elem.text.strip() if stars_elem else "0"
            )  # use "0" if not found

            article = Article(  # build our standard Article object
                title=title,  # repo name as the title
                url=url,  # full repo URL
                published_at=datetime.now(),  # GitHub gives no date, so use "now"
                source="github_trending",  # mark where it came from
                summary=f"{description} (stars {stars})",  # description + star count
                score=0,  # no numeric score for GitHub, default 0
            )
            articles.append(article)  # add it to the list

        return articles  # hand the list back (BaseFetcher saves it)

    def get_source_name(self) -> str:
        """Return source name (used for the output filename)."""
        return "github_trending"  # file will be github_trending_articles.md
