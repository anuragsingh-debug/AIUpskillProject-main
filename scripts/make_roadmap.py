"""Render a learning ROADMAP png from notes.md (milestone -> evening -> topic).

A vertical timeline: a coloured spine on the left, one big milestone node per
stage, and the evening topics as cards branching to the right.

Run:  ./venv/Scripts/python.exe scripts/make_roadmap.py
Output: docs/diagrams/roadmap.png
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

OUT = Path("docs/diagrams")
OUT.mkdir(parents=True, exist_ok=True)

# (color, milestone label, [ (evening, topic) ... ])
STAGES = [
    ("#9e9e9e", "M0  Setup", [
        ("E0", "venv, .env secrets, LiteLLM key, verify_setup"),
    ]),
    ("#1e88e5", "M1  Async Fetcher", [
        ("E1", "First API fetch (HackerNews IDs -> stories)"),
        ("E2", "Async concurrency: asyncio.gather"),
        ("E3", "Rate limiting via semaphore"),
        ("E4", "Multiple sources + Article model"),
        ("E5", "Resilience: try/except, drop None"),
    ]),
    ("#fbc02d", "M2  SOLID + Patterns", [
        ("E6", "SRP - split transform / storage"),
        ("E7", "OCP + Template Method (BaseFetcher)"),
        ("E8", "DIP + ISP, dependency injection, mocks"),
        ("E9", "Quality gate: ruff + pytest"),
        ("E10", "Factory + Strategy patterns"),
    ]),
    ("#8e24aa", "M3  First Agent + Tools", [
        ("E11", "BaseAgent (Template Method) + LLM smoke test"),
        ("E12", "LLM relevance filtering, structured JSON"),
        ("E13", "Tool use / function-calling loop"),
        ("E14", "pytest.ini, mocked tests, fetch->filter"),
        ("wrap", "Honest errors + per-min/day quota handling"),
    ]),
    ("#fb8c00", "M4  MCP + Multi-Agent", [
        ("E15", "MCP server/client, JSON-RPC stdout rule"),
        ("--", "Async SQLite (aiosqlite) + populate_db"),
        ("--", "Database MCP server (3 tools) + SearchSkill"),
        ("--", "Summarizer -> Writer, complete_pipeline"),
    ]),
    ("#e53935", "M5  Evaluation + Docs", [
        ("--", "Metrics: accuracy / precision / recall / F1"),
        ("--", "90% acc, F1 0.923 vs golden_dataset"),
        ("E24", "Docs: README, architecture, deployment"),
        ("E26", "Prompt tuning: overfitting vs generalisation"),
    ]),
]

# layout sizing
row_h = 0.62          # height per topic card
stage_gap = 0.7       # gap between stages
title_h = 1.0

total_rows = sum(len(t) for _, _, t in STAGES)
fig_h = total_rows * row_h + len(STAGES) * stage_gap + 2.2
fig, ax = plt.subplots(figsize=(13, fig_h))
ax.axis("off")
ax.set_xlim(0, 13)
ax.set_ylim(0, fig_h)

ax.text(0.3, fig_h - 0.55, "AI News Pipeline — Learning Roadmap (M0 -> M5)",
        fontsize=20, fontweight="bold", color="#222")
ax.text(0.3, fig_h - 1.0, "Follow the spine top -> bottom. Each card = one evening's topic.",
        fontsize=10.5, color="#666", style="italic")

spine_x = 1.5
card_x = 2.7
card_w = 9.8

y = fig_h - 1.8
node_centers = []
badge_h = 0.55

for color, label, topics in STAGES:
    n = len(topics)
    badge_y = y                              # badge top of the stage block
    first_card = y - badge_h - 0.45          # first card sits below the badge
    cys = [first_card - i * row_h for i in range(n)]
    node_y = (cys[0] + cys[-1]) / 2          # circle centred on the cards
    node_centers.append((node_y, color))

    # milestone node (big circle on spine)
    ax.add_patch(Circle((spine_x, node_y), 0.42, facecolor=color,
                 edgecolor="white", linewidth=2.5, zorder=4))
    ax.add_patch(Circle((spine_x, node_y), 0.42, facecolor="none",
                 edgecolor=color, linewidth=2, zorder=5))
    # milestone label badge (above the cards)
    ax.add_patch(FancyBboxPatch((card_x - 0.05, badge_y - 0.1), 4.4, 0.5,
                 boxstyle="round,pad=0.02,rounding_size=0.1",
                 facecolor=color, edgecolor=color, zorder=6))
    ax.text(card_x + 0.15, badge_y + 0.15, label, fontsize=12,
            fontweight="bold", color="white", va="center", zorder=7)
    # connector spine -> badge
    ax.plot([spine_x + 0.42, card_x - 0.05], [node_y, badge_y + 0.15],
            color=color, linewidth=1.0, alpha=0.5, zorder=1)

    # topic cards
    for i, (ev, topic) in enumerate(topics):
        cy = cys[i]
        ax.add_patch(FancyBboxPatch((card_x, cy - 0.24), card_w, 0.48,
                     boxstyle="round,pad=0.02,rounding_size=0.07",
                     linewidth=1.2, edgecolor=color, facecolor=color + "16"))
        # evening chip
        ax.add_patch(FancyBboxPatch((card_x + 0.12, cy - 0.16), 0.62, 0.32,
                     boxstyle="round,pad=0.01,rounding_size=0.06",
                     facecolor=color + "44", edgecolor=color, linewidth=1))
        ax.text(card_x + 0.43, cy, ev, fontsize=8, ha="center", va="center",
                fontweight="bold", color="#222")
        ax.text(card_x + 0.95, cy, topic, fontsize=9.5, va="center", color="#1a1a1a")

    y = cys[-1] - row_h - stage_gap

# spine line connecting all nodes
ys = [c[0] for c in node_centers]
ax.plot([spine_x, spine_x], [min(ys) - 0.42, max(ys) + 0.42],
        color="#b0bec5", linewidth=6, zorder=0, solid_capstyle="round")

# START / END markers
ax.text(spine_x, max(ys) + 0.95, "START", fontsize=10, ha="center",
        fontweight="bold", color="#37474f")
ax.text(spine_x, min(ys) - 0.95, "SHIP IT", fontsize=10, ha="center",
        fontweight="bold", color="#37474f")

plt.tight_layout()
fig.savefig(OUT / "roadmap.png", dpi=160, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("wrote", OUT / "roadmap.png")
