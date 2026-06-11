"""Generate two PNGs for the AI-News-Pipeline project:

  1. docs/diagrams/project-tree.png    -> top-to-bottom file/folder tree
  2. docs/diagrams/system-design.png   -> architecture / data-flow diagram

Run:  ./venv/Scripts/python.exe scripts/make_diagrams.py
Pure matplotlib (no Graphviz / system deps needed).
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless backend -> write straight to PNG
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path("docs/diagrams")
OUT.mkdir(parents=True, exist_ok=True)

# Milestone colour key reused by both diagrams ------------------------------
M = {
    "M0": "#9e9e9e",  # setup        - grey
    "M1": "#1e88e5",  # async fetch  - blue
    "M2": "#fbc02d",  # SOLID        - yellow
    "M3": "#8e24aa",  # first agent  - purple
    "M4": "#fb8c00",  # MCP pipeline - orange
    "M5": "#e53935",  # evaluation   - red
    "DEMO": "#43a047",  # demo/report - green
    "ROOT": "#37474f",  # root/config - dark slate
}


# =====================================================================
# 1) TOP-TO-BOTTOM FILE TREE
# =====================================================================
def draw_tree():
    # (text, x-indent-level, milestone-colour-key, is_folder)
    rows = [
        ("ai_upskill/  (git repo — branch: feature/milestone-5-evaluation)", 0, "ROOT", True),
        ("README.md  requirements.txt  pytest.ini  ruff.toml  .env  .gitignore  LICENSE", 1, "ROOT", False),
        ("server.py  — LIVE demo backend (real pipeline, SSE stream)", 1, "DEMO", False),
        ("src/  — ALL PRODUCTION CODE", 1, "ROOT", True),
        ("main.py / orchestrator.py / pipeline.py / complete_pipeline.py  (entry points)", 2, "M1", False),
        ("models/article.py  — core Article entity", 2, "M1", False),
        ("fetchers/  base+interfaces, hackernews, rss, github_trending", 2, "M1", False),
        ("transformers/article_transformer.py", 2, "M1", False),
        ("storage/  base, markdown, json", 2, "M2", False),
        ("factories/fetcher_factory.py   strategies/rate_limit_strategy.py", 2, "M2", False),
        ("utils/rate_limiter.py", 2, "M2", False),
        ("agents/  base, news_filter, enhanced_filter, summarizer, writer", 2, "M3", False),
        ("tools/  calculator, web_search    skills/search_skill.py", 2, "M3", False),
        ("mcp/  hello_server, database_server, simple_client", 2, "M4", False),
        ("database/db_manager.py  — SQLite layer", 2, "M4", False),
        ("evaluation/evaluator.py  — precision / recall / F1 vs golden set", 2, "M5", False),
        ("tests/  — 15 pytest files mirroring src/", 1, "ROOT", True),
        ("test_article, test_fetchers, test_storage, test_patterns ... test_db_server", 2, "ROOT", False),
        ("scripts/  verify_setup, practice_async, test_llm, test_summarizer, populate_db", 1, "M0", True),
        ("demo/  index.html, app.js, data.js, styles.css, vendor/html2pdf", 1, "DEMO", True),
        ("data/  articles/  context/  evaluation/(golden_dataset.json)  news_agent.db", 1, "M4", True),
        ("docs/  milestones/(M0..M5)  curriculum/  architecture  final-report", 1, "ROOT", True),
        ("report/  project-report.html  AI-News-Pipeline-Report.pdf", 1, "DEMO", True),
    ]

    fig, ax = plt.subplots(figsize=(15, 13))
    ax.axis("off")
    n = len(rows)
    row_h = 1.0
    x_step = 0.55
    box_left = {0: 0.2, 1: 0.9, 2: 1.7}

    # title
    ax.text(0.2, n + 1.2, "AI News Pipeline — Project File Tree (top -> down)",
            fontsize=20, fontweight="bold", color="#222")

    centers = {}
    for i, (text, lvl, ck, folder) in enumerate(rows):
        y = n - i  # top to bottom
        x = box_left[lvl]
        color = M[ck]
        w = 12.6 - x
        box = FancyBboxPatch((x, y - 0.34), w, 0.68,
                             boxstyle="round,pad=0.02,rounding_size=0.12",
                             linewidth=1.4, edgecolor=color,
                             facecolor=color + "22")
        ax.add_patch(box)
        weight = "bold" if folder else "normal"
        prefix = "[DIR]  " if folder else ""
        ax.text(x + 0.18, y, prefix + text, fontsize=10.3, va="center",
                fontweight=weight, color="#1a1a1a")
        centers[i] = (x, y)

    # connector lines (parent indent guide)
    for i, (text, lvl, ck, folder) in enumerate(rows):
        if lvl == 0:
            continue
        # find nearest previous row with lvl-1
        for j in range(i - 1, -1, -1):
            if rows[j][1] == lvl - 1:
                px, py = centers[j]
                cx, cy = centers[i]
                ax.plot([px + 0.25, px + 0.25, cx], [py - 0.34, cy, cy],
                        color="#90a4ae", linewidth=1.0, zorder=0)
                break

    # legend
    leg_y = 0.2
    items = [("M0 setup", "M0"), ("M1 async fetch", "M1"), ("M2 SOLID", "M2"),
             ("M3 agents", "M3"), ("M4 MCP/DB", "M4"), ("M5 eval", "M5"),
             ("demo/report", "DEMO"), ("root/config", "ROOT")]
    lx = 0.2
    for label, ck in items:
        ax.add_patch(FancyBboxPatch((lx, leg_y), 0.3, 0.45,
                     boxstyle="round,pad=0.02", facecolor=M[ck] + "55",
                     edgecolor=M[ck], linewidth=1.2))
        ax.text(lx + 0.4, leg_y + 0.22, label, fontsize=9.2, va="center")
        lx += 1.62

    ax.set_xlim(0, 13)
    ax.set_ylim(-0.4, n + 2)
    plt.tight_layout()
    fig.savefig(OUT / "project-tree.png", dpi=170, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("wrote", OUT / "project-tree.png")


# =====================================================================
# 2) SYSTEM DESIGN / DATA-FLOW
# =====================================================================
def box(ax, x, y, w, h, text, color, fontsize=10, bold=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0.02,rounding_size=0.12",
                 linewidth=2, edgecolor=color, facecolor=color + "1f"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, fontweight="bold" if bold else "normal",
            color="#1a1a1a")


def arrow(ax, x1, y1, x2, y2, color="#455a64", label=None, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                 arrowstyle="-|>", mutation_scale=20,
                 linewidth=2, color=color, linestyle=ls))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.18, label, fontsize=8.5,
                ha="center", color=color, style="italic")


def draw_system():
    fig, ax = plt.subplots(figsize=(16, 11))
    ax.axis("off")
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 11)

    ax.text(0.3, 10.5, "AI News Pipeline — System Design / Data Flow",
            fontsize=20, fontweight="bold", color="#222")

    # ---- Layer 1: SOURCES (M1) ----
    box(ax, 0.4, 8.2, 2.4, 0.9, "Hacker News API", M["M1"], 9)
    box(ax, 0.4, 7.0, 2.4, 0.9, "RSS Feeds", M["M1"], 9)
    box(ax, 0.4, 5.8, 2.4, 0.9, "GitHub Trending", M["M1"], 9)
    ax.text(1.6, 9.25, "EXTERNAL SOURCES", fontsize=9, ha="center",
            color=M["M1"], fontweight="bold")

    # ---- Orchestrator (M1/M2) ----
    box(ax, 3.6, 6.9, 2.6, 1.4,
        "FetchOrchestrator\n(asyncio.gather)\n+ RateLimiter", M["M2"], 9.5)
    for sy in (8.65, 7.45, 6.25):
        arrow(ax, 2.8, sy, 3.6, 7.6)

    # ---- Transform + Store (M1/M2) ----
    box(ax, 7.0, 7.1, 2.5, 1.0, "ArticleTransformer\n-> Article model", M["M1"], 9)
    arrow(ax, 6.2, 7.6, 7.0, 7.6)
    box(ax, 7.0, 5.6, 2.5, 1.0, "Storage\nmarkdown / json", M["M2"], 9)
    arrow(ax, 8.25, 7.1, 8.25, 6.6)

    # ---- Filter agent (M3) ----
    box(ax, 10.3, 7.1, 2.7, 1.0, "NewsFilterAgent\n(LLM relevance)", M["M3"], 9)
    arrow(ax, 9.5, 7.6, 10.3, 7.6, label="raw articles")
    box(ax, 10.3, 5.7, 2.7, 0.9, "EnhancedFilterAgent\n(tuned prompt)", M["M3"], 8.5)
    arrow(ax, 11.65, 7.1, 11.65, 6.6)

    # ---- Summarizer + Writer (M4) ----
    box(ax, 10.3, 4.1, 2.7, 0.9, "SummarizerAgent", M["M4"], 9)
    arrow(ax, 11.65, 5.7, 11.65, 5.0)
    box(ax, 10.3, 2.7, 2.7, 0.9, "WriterAgent\n-> newsletter", M["M4"], 9)
    arrow(ax, 11.65, 4.1, 11.65, 3.6)

    # ---- BaseAgent shared ----
    box(ax, 13.4, 5.0, 2.2, 1.6,
        "BaseAgent\nGemini LLM\nretry + rate\nlimit", M["M3"], 9)
    arrow(ax, 13.4, 5.9, 13.0, 6.1, ls="--")
    arrow(ax, 13.4, 5.5, 13.0, 4.55, ls="--")
    arrow(ax, 13.4, 5.2, 13.0, 3.15, ls="--")

    # ---- MCP + DB (M4) ----
    box(ax, 7.0, 2.7, 2.5, 1.0, "MCP Server\n(database_server)", M["M4"], 9)
    arrow(ax, 10.3, 3.15, 9.5, 3.2, label="store")
    box(ax, 7.0, 1.2, 2.5, 0.9, "SQLite\nnews_agent.db", M["M4"], 9)
    arrow(ax, 8.25, 2.7, 8.25, 2.1)

    # ---- Evaluation (M5) ----
    box(ax, 3.4, 2.7, 3.0, 1.6,
        "Evaluator (M5)\nprecision / recall / F1\nvs golden_dataset.json\n90% acc | F1 0.923",
        M["M5"], 8.8)
    arrow(ax, 10.3, 2.9, 6.4, 3.3, label="predictions", ls="--")
    box(ax, 3.4, 1.2, 3.0, 0.9, "data/evaluation/\nreports", M["M5"], 8.5)
    arrow(ax, 4.9, 2.7, 4.9, 2.1)

    # ---- Presentation (DEMO) ----
    box(ax, 0.4, 2.7, 2.4, 1.2,
        "server.py (SSE)\n+ demo/  +  report\nPDF / HTML", M["DEMO"], 8.8)
    arrow(ax, 3.4, 3.5, 2.8, 3.4, ls="--")

    # legend
    items = [("M1 fetch", "M1"), ("M2 SOLID", "M2"), ("M3 agents", "M3"),
             ("M4 MCP/DB", "M4"), ("M5 eval", "M5"), ("demo", "DEMO")]
    lx = 0.4
    for label, ck in items:
        ax.add_patch(FancyBboxPatch((lx, 0.25), 0.3, 0.4,
                     boxstyle="round,pad=0.02", facecolor=M[ck] + "55",
                     edgecolor=M[ck], linewidth=1.2))
        ax.text(lx + 0.4, 0.45, label, fontsize=9, va="center")
        lx += 2.2

    plt.tight_layout()
    fig.savefig(OUT / "system-design.png", dpi=170, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("wrote", OUT / "system-design.png")


if __name__ == "__main__":
    draw_tree()
    draw_system()
    print("Done.")
