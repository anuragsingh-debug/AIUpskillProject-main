"""Render a REAL branching tree (left -> right) of the project.

Root on the left, milestone branches in the middle, file leaves on the right.
Every leaf shows  <file>  +  the concept/topic it teaches.

Run:  ./venv/Scripts/python.exe scripts/make_tree.py
Output: docs/diagrams/project-tree-branches.png
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path("docs/diagrams")
OUT.mkdir(parents=True, exist_ok=True)

M = {
    "M1": "#1e88e5", "M2": "#fbc02d", "M3": "#8e24aa",
    "M4": "#fb8c00", "M5": "#e53935", "DEMO": "#43a047", "TEST": "#00897b",
}

# tree[branch] = (color_key, branch_title, [ (file, concept), ... ])
TREE = [
    ("M1", "M1  Async Fetching", [
        ("models/article.py", "dataclass / domain entity, type hints"),
        ("fetchers/hackernews_fetcher.py", "async/await, aiohttp, HN API"),
        ("fetchers/rss_fetcher.py", "RSS feed parsing"),
        ("fetchers/github_trending_fetcher.py", "web scraping"),
        ("orchestrator.py", "concurrency: asyncio.gather (fan-out/in)"),
        ("transformers/article_transformer.py", "normalization, separation of concerns"),
        ("main.py", "composition root / entry point"),
    ]),
    ("M2", "M2  SOLID Refactor", [
        ("fetchers/interfaces.py", "Interface Segregation (ISP), ABC"),
        ("fetchers/base_fetcher.py", "Dependency Inversion (DIP)"),
        ("storage/base_storage.py", "abstract storage interface"),
        ("storage/markdown_storage.py", "Liskov substitution (swappable)"),
        ("storage/json_storage.py", "Liskov substitution (swappable)"),
        ("factories/fetcher_factory.py", "Factory pattern (Open/Closed)"),
        ("strategies/rate_limit_strategy.py", "Strategy pattern"),
        ("utils/rate_limiter.py", "token-bucket rate limiting"),
    ]),
    ("M3", "M3  First Agent + Tools", [
        ("agents/base_agent.py", "LLM client, retry/backoff, prompts"),
        ("agents/news_filter_agent.py", "LLM-as-classifier (relevance)"),
        ("agents/enhanced_filter_agent.py", "prompt engineering, fix over-inclusion"),
        ("tools/calculator.py", "function-calling / tool use"),
        ("tools/web_search.py", "tool use (web search)"),
        ("skills/search_skill.py", "reusable skill wrapper"),
        ("pipeline.py", "Fetch -> Filter composition"),
    ]),
    ("M4", "M4  MCP + Multi-Agent", [
        ("mcp/hello_server.py", "MCP basics (server)"),
        ("mcp/database_server.py", "expose DB as MCP tools"),
        ("mcp/simple_client.py", "MCP client"),
        ("database/db_manager.py", "SQLite CRUD, repository pattern"),
        ("agents/summarizer_agent.py", "LLM summarization"),
        ("agents/writer_agent.py", "newsletter generation (agent chain)"),
        ("complete_pipeline.py", "full orchestration Fetch->...->Store"),
    ]),
    ("M5", "M5  Evaluation", [
        ("evaluation/evaluator.py", "precision / recall / F1, 1 batched LLM call"),
        ("data/evaluation/golden_dataset.json", "labeled ground truth"),
        ("data/evaluation/evaluation_report.md", "metrics: 90% acc, F1 0.923"),
    ]),
    ("DEMO", "Demo / Report", [
        ("server.py", "Server-Sent Events (SSE), live pipeline"),
        ("demo/app.js + index.html", "zero-quota replay UI"),
        ("demo/vendor/html2pdf.js", "client-side PDF export"),
        ("report/AI-News-Pipeline-Report.pdf", "final deliverable"),
    ]),
    ("TEST", "Tests / Tooling", [
        ("tests/ (15 files)", "pytest, fixtures (conftest), mocking"),
        ("tests/test_substitutability.py", "verifies Liskov substitution"),
        ("pytest.ini / ruff.toml", "test config + lint/format standards"),
    ]),
]

# ---- layout -----------------------------------------------------------
leaf_h = 0.62          # vertical slot per leaf
gap_between_branches = 0.5
x_root = 0.3
x_branch = 3.4
x_leaf = 7.3
leaf_w = 8.5
branch_w = 3.2

# compute total leaves to size the canvas
total_leaves = sum(len(files) for _, _, files in TREE)
total_slots = total_leaves + len(TREE) * 0  # branches share leaf rows
fig_h = total_leaves * leaf_h + len(TREE) * gap_between_branches + 2
fig, ax = plt.subplots(figsize=(17, fig_h))
ax.axis("off")

ax.text(x_root, fig_h - 0.6, "AI News Pipeline  —  Project Tree (with concepts per file)",
        fontsize=20, fontweight="bold", color="#222")

y = fig_h - 1.6
branch_centers = []
leaf_points = []   # (x_left, y, color) for connector endpoints

for ck, title, files in TREE:
    color = M[ck]
    n = len(files)
    block_top = y
    block_bottom = y - (n - 1) * leaf_h
    branch_y = (block_top + block_bottom) / 2
    branch_centers.append((branch_y, color, title))

    # branch node
    ax.add_patch(FancyBboxPatch((x_branch, branch_y - 0.32), branch_w, 0.64,
                 boxstyle="round,pad=0.02,rounding_size=0.1",
                 linewidth=2.2, edgecolor=color, facecolor=color + "33"))
    ax.text(x_branch + branch_w / 2, branch_y, title, ha="center", va="center",
            fontsize=11, fontweight="bold", color="#1a1a1a")

    # leaves
    for i, (fname, concept) in enumerate(files):
        ly = block_top - i * leaf_h
        ax.add_patch(FancyBboxPatch((x_leaf, ly - 0.27), leaf_w, 0.54,
                     boxstyle="round,pad=0.02,rounding_size=0.08",
                     linewidth=1.3, edgecolor=color, facecolor=color + "18"))
        ax.text(x_leaf + 0.15, ly + 0.005,
                f"$\\bf{{{fname.replace('_', chr(92)+'_')}}}$",
                fontsize=9.0, va="center", color="#111")
        ax.text(x_leaf + 0.15, ly - 0.165, concept, fontsize=8.0,
                va="center", color="#444", style="italic")
        # elbow connector branch -> leaf
        xb = x_branch + branch_w
        midx = (xb + x_leaf) / 2
        ax.plot([xb, midx, midx, x_leaf],
                [branch_y, branch_y, ly, ly],
                color=color, linewidth=1.1, zorder=0)

    # root -> branch connector
    xr = x_root + 2.2
    midx = (xr + x_branch) / 2
    ax.plot([xr, midx, midx, x_branch],
            [fig_h - 4, fig_h - 4, branch_y, branch_y],
            color="#607d8b", linewidth=1.4, zorder=0)

    y = block_bottom - leaf_h - gap_between_branches

# root node
root_y = fig_h - 4
ax.add_patch(FancyBboxPatch((x_root, root_y - 0.5), 2.2, 1.0,
             boxstyle="round,pad=0.02,rounding_size=0.12",
             linewidth=2.6, edgecolor="#37474f", facecolor="#37474f22"))
ax.text(x_root + 1.1, root_y, "ai_upskill/\n(repo root)", ha="center",
        va="center", fontsize=11, fontweight="bold", color="#1a1a1a")

ax.set_xlim(0, x_leaf + leaf_w + 0.4)
ax.set_ylim(0, fig_h)
plt.tight_layout()
fig.savefig(OUT / "project-tree-branches.png", dpi=160, bbox_inches="tight",
            facecolor="white")
plt.close(fig)
print("wrote", OUT / "project-tree-branches.png")
