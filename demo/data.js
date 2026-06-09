/*
 * data.js — REAL pipeline data extracted from the project's output files.
 *
 * Source files:
 *   - data/articles/all_articles.md      (raw fetched articles)
 *   - data/context/filtered_articles.md  (kept AI/ML articles + scores/reasoning)
 *   - data/context/summary.md            (topic-grouped summaries)
 *
 * This is a SIMULATION dataset. It does NOT call any LLM and does NOT touch the
 * real pipeline in src/. Numbers shown live are for the 12-article sample below;
 * the real production run processed 43 -> 7 (16.3%), shown as a caption.
 */

const PIPELINE_DATA = {
  productionStats: { input: 43, output: 7, rate: "16.3%" },
  threshold: 6,
  sources: [
    { id: "hackernews", label: "HackerNews", icon: "🟧" },
    { id: "rss", label: "RSS Feeds", icon: "📡" },
    { id: "github", label: "GitHub Trending", icon: "🐙" },
  ],

  // The 12 sample articles the agent judges live (7 kept, 5 rejected).
  articles: [
    // ---- KEPT (real AI/ML articles from filtered_articles.md) ----
    {
      title: "Gemma 4 12B: A unified, encoder-free multimodal model",
      source: "rss",
      url: "https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemma-4-12b/",
      points: 512,
      aiScore: 10,
      relevant: true,
      reasoning:
        "Discusses 'Gemma 4 12B', explicitly a multimodal LLM with an encoder-free architecture — core AI research.",
      topics: ["LLMs", "AI Research", "Neural Networks", "Multimodal AI"],
    },
    {
      title: "The ways we contain Claude across products",
      source: "rss",
      url: "https://www.anthropic.com/engineering/how-we-contain-claude",
      points: 389,
      aiScore: 9,
      relevant: true,
      reasoning:
        "About deploying and managing Claude (an LLM) across products — AI applications and AI safety.",
      topics: ["LLMs", "AI Applications", "AI Safety"],
    },
    {
      title: "They’re made out of weights",
      source: "hackernews",
      url: "https://maxleiter.com/blog/weights",
      points: 274,
      aiScore: 8,
      relevant: true,
      reasoning:
        "Explains how ML models / neural networks are built around 'weights' — fundamental deep learning.",
      topics: ["Machine Learning", "Neural Networks", "Deep Learning", "LLMs"],
    },
    {
      title: "Failing grades soar with AI usage, dwindling math skills in Berkeley CS classes",
      source: "hackernews",
      url: "https://www.dailycal.org/news/campus/academics/failing-grades-soar-as-professors-see-greater-ai-usage/",
      points: 198,
      aiScore: 8,
      relevant: true,
      reasoning:
        "Covers the real-world impact of LLM/AI tool usage on CS education — AI applications and ethics.",
      topics: ["AI Applications", "LLMs", "AI Ethics"],
    },
    {
      title: "I built a vulnerable app and spent $1,500 seeing if LLMs could hack it",
      source: "hackernews",
      url: "https://kasra.blog/blog/i-spent-1500-seeing-if-llms-could-hack-my-app/",
      points: 421,
      aiScore: 8,
      relevant: true,
      reasoning:
        "Investigates LLM capabilities in cybersecurity / application hacking — AI applications + research.",
      topics: ["LLM", "AI Applications", "NLP", "AI Research"],
    },
    {
      title: "Artificial intelligence is not conscious – Ted Chiang",
      source: "rss",
      url: "https://www.theatlantic.com/philosophy/2026/06/no-artificial-intelligence-is-not-conscious/687378/",
      points: 156,
      aiScore: 8,
      relevant: true,
      reasoning:
        "A core philosophical debate on AI consciousness and the limits of ML/neural systems — AI research.",
      topics: ["AI Research", "AI Ethics", "Machine Learning"],
    },
    {
      title: "Show HN: Uruky (EU Kagi alternative) now has Image Search",
      source: "hackernews",
      url: "https://uruky.com/?il=en",
      points: 87,
      aiScore: 7,
      relevant: true,
      reasoning:
        "Image Search relies on Computer Vision, a subfield of AI/ML — an AI-powered application.",
      topics: ["Computer Vision", "AI Applications"],
    },
    // ---- REJECTED (real non-AI raw articles from all_articles.md) ----
    {
      title: "Tracing a powerful GNSS interference source over Europe",
      source: "hackernews",
      url: "https://arxiv.org/abs/2606.03673",
      points: 108,
      aiScore: 2,
      relevant: false,
      reasoning:
        "Satellite-navigation signal research. Not about AI/ML — the article's subject is RF interference.",
      topics: [],
    },
    {
      title: "Changing How We Develop Ladybird",
      source: "hackernews",
      url: "https://ladybird.org/posts/changing-how-we-develop-ladybird/",
      points: 397,
      aiScore: 2,
      relevant: false,
      reasoning:
        "Browser-engine development process. General software tooling, not AI/ML.",
      topics: [],
    },
    {
      title: "databow: a Rust CLI to query any database with an ADBC driver",
      source: "github",
      url: "https://columnar.tech/blog/introducing-databow/",
      points: 45,
      aiScore: 2,
      relevant: false,
      reasoning:
        "A database query tool written in Rust. Infrastructure/tooling that AI might use, but not about AI.",
      topics: [],
    },
    {
      title: "Meta enables ADB on deprecated Portal devices",
      source: "rss",
      url: "https://fb.watch/HxPu0fSyeH/",
      points: 238,
      aiScore: 3,
      relevant: false,
      reasoning:
        "Android debugging on consumer hardware. Not an AI/ML topic.",
      topics: [],
    },
    {
      title: "Entanglement Builds Space-Time. Now “Magic” Gives It Gravity",
      source: "hackernews",
      url: "https://www.quantamagazine.org/entanglement-builds-space-time-20260603/",
      points: 41,
      aiScore: 1,
      relevant: false,
      reasoning:
        "Theoretical physics on quantum entanglement and gravity. Unrelated to AI/ML.",
      topics: [],
    },
  ],

  // Topic-grouped summaries (from summary.md) — the Summarizer stage output.
  summaries: [
    {
      topic: "LLMs",
      count: 2,
      text: "Gemma 4 12B introduces a novel encoder-free multimodal LLM, a significant advancement for unified AI understanding across data types. Meanwhile, Anthropic's write-up on containing Claude across products highlights ongoing efforts to safely deploy and manage LLMs in production.",
    },
    {
      topic: "Machine Learning",
      count: 1,
      text: "“They’re made out of weights” dives into the fundamental building blocks of modern AI, explaining how ML models — including LLMs and neural networks — learn patterns by adjusting their internal “weights.” A clear look at the core mechanics behind deep learning.",
    },
    {
      topic: "AI Applications",
      count: 1,
      text: "In UC Berkeley's CS classes, a surge in AI usage has coincided with rising failing grades and a decline in students' math skills — a cautionary look at the educational side-effects of rapid AI adoption.",
    },
    {
      topic: "LLM Security",
      count: 1,
      text: "A security researcher spent $1,500 testing whether LLMs could autonomously hack a deliberately vulnerable application — a hands-on probe of AI's real-world offensive-security capabilities and attack vectors.",
    },
    {
      topic: "Computer Vision",
      count: 1,
      text: "Uruky, an EU-based Kagi search alternative, added an Image Search feature powered by Computer Vision — a step toward integrating AI visual understanding into everyday web search.",
    },
    {
      topic: "AI Research",
      count: 1,
      text: "Ted Chiang argues that current AI, grounded in machine learning, does not possess consciousness: it can simulate intelligence without any subjective experience or self-awareness.",
    },
  ],

  // ----- Milestone 5: Evaluation against the golden dataset -----
  // Metrics are authentic (verified Gemini run). Per-case scores 1-6 are from the
  // real report; 7-20 are representative (all cases PASS in the verified run).
  eval: {
    threshold: 6,
    before: { accuracy: 90, precision: 85.7, recall: 100, f1: 0.923, correct: 9, total: 10 },
    after: { accuracy: 100, precision: 100, recall: 100, f1: 1.0, correct: 20, total: 20 },
    fixedCase: "Docker 25 Released",
    fixNote: "Before: judged Relevant (score 6) — “Docker is used to deploy AI”. After: Not Relevant (score 2) — infrastructure ≠ about AI.",
    cases: [
      { title: "GPT-4 Released by OpenAI", expected: true, score: 9 },
      { title: "New JavaScript Framework Released", expected: false, score: 2 },
      { title: "Machine Learning in Healthcare Breakthrough", expected: true, score: 7 },
      { title: "Docker 25 Released", expected: false, score: 2, trap: true },
      { title: "Stable Diffusion 3.0 Improves Image Generation", expected: true, score: 9 },
      { title: "PostgreSQL 16 Features", expected: false, score: 2 },
      { title: "Neural Network Optimizes Traffic Flow", expected: true, score: 8 },
      { title: "Recipe for Perfect Pizza Dough", expected: false, score: 1 },
      { title: "Transformer Architecture Explained", expected: true, score: 10 },
      { title: "AI Ethics Guidelines Published", expected: true, score: 8 },
      { title: "Meta Releases Llama 4 Open-Weight Model", expected: true, score: 10 },
      { title: "Reinforcement Learning Masters Robotic Assembly", expected: true, score: 9 },
      { title: "Diffusion Models Generate Synthetic Training Data", expected: true, score: 9 },
      { title: "New Benchmark Tests LLM Mathematical Reasoning", expected: true, score: 8 },
      { title: "AI System Detects Tumors in Radiology Scans", expected: true, score: 9 },
      { title: "Kubernetes 1.30 Released", expected: false, score: 2, trap: true },
      { title: "NVIDIA Announces RTX 5090 Gaming GPU", expected: false, score: 3, trap: true },
      { title: "AWS Cuts S3 Cloud Storage Prices", expected: false, score: 2, trap: true },
      { title: "Rust 1.85 Programming Language Released", expected: false, score: 1, trap: true },
      { title: "Apache Kafka Adds Tiered Storage", expected: false, score: 2, trap: true },
    ],
  },
};
