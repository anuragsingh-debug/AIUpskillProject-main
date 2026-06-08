"""AI Upskill Project — student code lives here.

Layout as actually built across the milestones:

    models/             Article and other data classes (M1)
    fetchers/           News source fetchers (M1, extended in M2)
    transformers/       Source data -> Article (M2, SRP)
    storage/            Markdown + SQLite storage (M1, M4)
    factories/          FetcherFactory (M2)
    strategies/         Rate-limit strategies (M2)
    utils/              Shared helpers, e.g. rate_limiter (M1)
    agents/             AI agents — Filter, Summarizer, Writer (M3, M4)
    mcp/                MCP server(s) + client — Database (M4)
    skills/             Reusable agent skills, e.g. SearchSkill (M4)
    evaluation/         Golden-dataset evaluator (M5)
    orchestrator.py / pipeline.py / complete_pipeline.py   Pipeline glue
"""
