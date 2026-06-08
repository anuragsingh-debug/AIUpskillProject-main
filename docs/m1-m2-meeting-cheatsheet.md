# M1 & M2 — Simple Explanation (Meeting Cheat-Sheet)

> Project: an AI news pipeline that **fetches** articles from many sources, **cleans** them into one format, and **saves** them.

---

## MILESTONE 1 — Async Fetcher
**Goal:** grab news from many sources, fast.

### The Workflow (what it does)
1. Ask each source (HackerNews, RSS, GitHub) for articles.
2. Pull all the articles **at the same time**, not one by one.
3. Turn each source's messy data into one clean `Article` format.
4. Hand the clean list to the next step.

### Challenges → How I Solved Them
| Problem (simple words) | What I did |
|---|---|
| **Too slow** — fetching one article at a time took forever (~30 calls). | Fetched them **all at once** using `asyncio.gather`. Time went from "all calls added up" to "just the slowest one". |
| **Getting blocked** — firing 30 requests at once can get you banned. | Added a **traffic guard (semaphore)** that lets only 10 through at a time. *Like an ATM with a guard letting 2 people in at a time.* |
| **Every source speaks a different language** — HackerNews is JSON, RSS is a feed, GitHub has no API. | One **translator per source** → all become the same `Article`. |
| **One bad call crashes everything.** | Wrapped each call in **try/except** — one failure is skipped, the rest keep going. |

**One-line takeaway:** *"Async made it fast; the rate-limit guard made it safe."*

---

## MILESTONE 2 — SOLID Refactor (clean code)
**Goal:** make the code easy to grow **without breaking** old working parts.

### The Workflow (what changed)
- Before: one big class did **everything** (fetch + clean + save) — fragile.
- After: split into small pieces, each doing **one job**. Added a "rulebook" (interface) so new sources just plug in.

### Challenges → How I Solved Them
| Problem (simple words) | What I did |
|---|---|
| **One class did 3 jobs** (fetch, clean, save) — change one thing, break another. | **Split it up** (SRP): a fetcher only fetches, a transformer only cleans, storage only saves. |
| **Adding a new source meant editing old working code** (risky). | Made a **base template** (OCP). Proof: adding **GitHub = 1 new file, 0 edits** to old code. |
| **Tests needed the real internet** — slow and flaky. | Used **interfaces + fake (mock) data** (DIP), so tests run offline. Proof: swapping to JSON storage was a **1-line change**. |
| **Copied tutorial code had hidden bugs.** | Ran **`ruff` + `pytest`** on everything — caught missing imports and a broken branch. *"Trust nothing you copied."* |
| **A refactor almost killed the speed-up** from M1. | Kept **tests that guard behaviour** — they flagged it instantly. |

**One-line takeaway:** *"We optimised for change, not just correctness — a whole new source took 1 file and 0 edits."*

---

## If you only remember 4 sentences
1. **M1** = fetch news from many sources **fast** (all at once) and **safely** (traffic guard).
2. **M2** = restructure so each piece does **one job** and new features **plug in without breaking old code**.
3. **Proof it worked:** new GitHub source = 1 file/0 edits; new JSON storage = 1 line.
4. **Discipline:** linters + tests caught real bugs in copied code — *"works on the slide" became "works in tests."*
