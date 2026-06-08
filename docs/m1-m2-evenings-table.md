# M1 & M2 — Evening-by-Evening (What / Challenge / How Handled)

Simple English, for the meeting. Grouped by evening/session.

---

## MILESTONE 1 — Async News Fetcher

| Evening | What I did | Challenge faced | How I handled it |
|---|---|---|---|
| **E1 — First fetch** | Connect to HackerNews API and pull a list of story IDs, then each story. | HackerNews gives IDs first, then needs **one API call per story (~30 calls)** — one-by-one is very slow. | Will fix with concurrency (E2). Got a basic working fetch first. |
| **E2 — Make it fast (async)** | Fetch all stories **at the same time**. | Sequential calls = slow, doesn't scale. | Used `asyncio.gather` to fire all requests **concurrently** → time = slowest single call, not the sum. |
| **E3 — Don't get banned** | Add a limit on how many requests go out at once. | Firing 30 requests in a burst can get the client **throttled or banned**. | Added a **semaphore** guard (max 10 at a time). *Like an ATM guard letting 2 people in at a time.* |
| **E4 — Add more sources** | Add RSS feeds alongside HackerNews. | Each source speaks a **different language** (HackerNews = JSON, RSS = feed format). | Wrote **one translator per source**; all output the same `Article` format. |
| **E5 — Make it reliable** | Handle calls that fail or return nothing. | One bad network call could **crash the whole fetch**. | Wrapped each call in **try/except**, dropped the `None`s — one failure is skipped, the rest continue. |

**M1 outcome:** working fetcher pulling from live sources **concurrently and safely**.

---

## MILESTONE 2 — SOLID Refactor + Design Patterns

| Evening | What I did | Challenge faced | How I handled it |
|---|---|---|---|
| **E6 — Split the big class (SRP)** | Break the one do-everything fetcher into pieces. | One class did **3 jobs** (fetch + clean + save) — change one thing, break another. | **Single Responsibility:** extracted `ArticleTransformer` (cleaning) and `MarkdownStorage` (saving). Fetcher now only fetches. |
| **E7 — Make it extendable (OCP)** | Add a base template so new sources plug in. | Adding a new source meant **editing old working code** = regression risk. | **Open/Closed:** made a `BaseFetcher` template. Proof → added **GitHub Trending = 1 new file, 0 edits**. |
| **E8 — Make it testable (DIP)** | Use interfaces + fake data so tests run offline. | Tests needed the **real internet** — slow and flaky. | **Dependency Inversion:** storage interface + injected fetchers + mocks; `main.py` wires it all. Proof → swapped to JSON storage in **1 line**. |
| **E9 — Catch hidden bugs** | Run linter + tests on everything. | **Copied tutorial code had real bugs** (missing imports, dead branch, broken async). | Ran `ruff` + `pytest` as a gate → caught them all. *"Works on the slide" → "works in tests."* |
| **E10 — Add patterns** | Add Factory + Strategy patterns. | Needed a clean way to **create fetchers** and **swap rate-limit rules**. | `FetcherFactory` (creates the right fetcher) + `RateLimitStrategy` (Semaphore / TokenBucket, pluggable). |

**M2 outcome:** all 5 SOLID principles + 3 patterns; 3 live sources; **27 tests passing**, `ruff` clean, two zero-/one-edit extension proofs.

---

## If asked "what's the big win?"
- **M1:** *Async made it fast; the rate-limit guard made it safe.*
- **M2:** *We optimised for change — a whole new data source took **1 file and 0 edits**.*

> ⚠️ Note: M1 was built in one big commit and M2 across a few; the evening numbers above are a clean way to **narrate** the steps, mapped to the real challenges (A1–A4, B1–B3, C1) from `challenges-and-strategies.md`.
