/* app.js — drives the pipeline simulation. No network, no LLM, no src/ imports. */

const D = PIPELINE_DATA;
const $ = (id) => document.getElementById(id);
const srcLabel = (id) => (D.sources.find((s) => s.id === id) || { label: id, icon: "•" });

let SPEED = 1;
let running = false;
let pages = [];
let pageIdx = 0;
let MODE = "replay";          // "replay" | "live"
let NEWS = D.summaries;       // summaries used to build the newsletter (swapped in live mode)

const sleep = (ms) => new Promise((r) => setTimeout(r, ms * SPEED));

/* ---------------- console ---------------- */
function log(msg, cls = "c-dim") {
  const el = $("console");
  const line = document.createElement("span");
  line.className = cls;
  line.textContent = msg + "\n";
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}

/* ---------------- stages ---------------- */
function setStage(name, state, pct) {
  const card = document.querySelector(`.stage[data-stage="${name}"]`);
  if (!card) return;
  card.classList.remove("running", "done");
  if (state) card.classList.add(state);
  $("status-" + name).textContent = state === "running" ? "running" : state === "done" ? "done" : "idle";
  if (pct != null) $("bar-" + name).style.width = pct + "%";
}

async function fillBar(name, from, to, steps = 12) {
  for (let i = 0; i <= steps; i++) {
    const pct = from + ((to - from) * i) / steps;
    $("bar-" + name).style.width = pct + "%";
    await sleep(40);
  }
}

/* ---------------- KPIs ---------------- */
const kpi = {
  fetched: 0, kept: 0, binned: 0, topics: 0,
  set(k, v) { this[k] = v; const el = $("kpi-" + k); if (el) el.textContent = v; },
  rate() {
    const r = kpi.fetched ? Math.round((kpi.kept / kpi.fetched) * 100) : 0;
    $("kpi-rate").textContent = r + "%";
  },
};

/* ---------------- main run ---------------- */
async function run() {
  if (running) return;
  running = true;
  NEWS = D.summaries;
  $("startBtn").disabled = true;
  $("resetBtn").disabled = false;

  log("=".repeat(48), "c-dim");
  log("  AI Agent Pipeline — simulation start", "c-info");
  log("=".repeat(48), "c-dim");

  // ---- Stage 1: Fetch ----
  setStage("fetch", "running");
  log("\n📰 Step 1: Fetching articles from sources...", "c-info");
  let fetched = 0;
  for (const a of D.articles) {
    fetched++;
    kpi.set("fetched", fetched);
    $("meta-fetch").textContent = `from ${srcLabel(a.source).label}…`;
    $("bar-fetch").style.width = (fetched / D.articles.length) * 100 + "%";
    if (fetched % 3 === 0 || fetched === D.articles.length)
      log(`   • ${fetched} fetched (${srcLabel(a.source).icon} ${srcLabel(a.source).label})`, "c-dim");
    await sleep(170);
  }
  $("meta-fetch").textContent = `${fetched} articles from 3 sources`;
  setStage("fetch", "done", 100);
  log(`✅ Fetched ${fetched} articles → data/articles/all_articles.md`, "c-ok");

  // ---- Stage 2: Database ----
  setStage("db", "running");
  log("\n💾 Step 2: Saving to database (SQLite via MCP server)...", "c-info");
  await fillBar("db", 0, 100, 14);
  setStage("db", "done", 100);
  $("meta-db").textContent = `${fetched} rows in news_agent.db`;
  log(`✅ Database has ${fetched} articles (3 MCP tools available)`, "c-ok");

  // ---- Stage 3: Filter ----
  setStage("filter", "running");
  log("\n🤖 Step 3: Filtering with AI agent (threshold ≥ " + D.threshold + ")...", "c-info");
  $("feed").innerHTML = "";
  let done = 0;
  for (const a of D.articles) {
    const card = renderJudging(a);
    await sleep(420); // "thinking"
    revealVerdict(card, a);
    done++;
    $("bar-filter").style.width = (done / D.articles.length) * 100 + "%";
    if (a.relevant) { kpi.set("kept", kpi.kept + 1); log(`   ✅ [${a.aiScore}/10] ${trim(a.title)}`, "c-ok"); }
    else { kpi.set("binned", kpi.binned + 1); log(`   ❌ [${a.aiScore}/10] ${trim(a.title)}`, "c-bad"); }
    await sleep(150);
  }
  kpi.rate();
  setStage("filter", "done", 100);
  $("meta-filter").textContent = `${kpi.kept} kept · ${kpi.binned} binned`;
  log(`\n📊 Filtered: ${kpi.kept}/${fetched} relevant (${$("kpi-rate").textContent})`, "c-info");

  // ---- Stage 4: Summarize ----
  setStage("summarize", "running");
  log("\n📝 Step 4: Summarizing with AI agent (group by topic)...", "c-info");
  let t = 0;
  for (const s of D.summaries) {
    t++;
    kpi.set("topics", t);
    $("bar-summarize").style.width = (t / D.summaries.length) * 100 + "%";
    log(`   • ${s.topic} (${s.count} article${s.count > 1 ? "s" : ""})`, "c-dim");
    await sleep(360);
  }
  setStage("summarize", "done", 100);
  $("meta-summarize").textContent = `${D.summaries.length} topic clusters`;
  log(`✅ Summary → data/context/summary.md`, "c-ok");

  // ---- Stage 5: Write ----
  setStage("write", "running");
  log("\n✍️  Step 5: Writing newsletter...", "c-info");
  await fillBar("write", 0, 100, 16);
  buildPages();
  setStage("write", "done", 100);
  $("meta-write").textContent = `${pages.length}-page digest ready`;
  log(`✅ Newsletter → data/output/newsletter.md`, "c-ok");

  log("\n🎉 Pipeline output ready — newsletter below.", "c-ok");
  $("newsletterPanel").hidden = false;

  // ---- Stage 6: Evaluate (Milestone 5) ----
  await runEvaluation();

  log("\n" + "=".repeat(48), "c-dim");
  log("✅ All done — newsletter generated AND filter quality measured.", "c-ok");
  log("=".repeat(48), "c-dim");
  $("evalPanel").scrollIntoView({ behavior: "smooth", block: "start" });
  running = false;
}

/* ---------------- Stage 6: Evaluation ---------------- */
async function runEvaluation() {
  const E = D.eval;
  setStage("evaluate", "running");
  log("\n🧪 Step 6: Evaluating filter quality vs golden dataset...", "c-info");
  $("evalPanel").hidden = false;
  $("cases").innerHTML = "";
  $("metrics").innerHTML = "";
  $("baRow").innerHTML = "";
  $("caseCount").textContent = `(${E.cases.length} cases · threshold ≥ ${E.threshold})`;

  let pass = 0, tp = 0, fp = 0, fn = 0;
  for (let i = 0; i < E.cases.length; i++) {
    const c = E.cases[i];
    const predicted = c.score >= E.threshold;
    const ok = predicted === c.expected;
    if (ok) pass++;
    if (c.expected && predicted) tp++;
    if (!c.expected && predicted) fp++;
    if (c.expected && !predicted) fn++;
    renderCase(c, ok);
    $("bar-evaluate").style.width = ((i + 1) / E.cases.length) * 100 + "%";
    log(`   ${ok ? "✅" : "❌"} [${c.score}/10] ${trim(c.title, 44)} (exp ${c.expected ? "AI" : "not"})`, ok ? "c-ok" : "c-bad");
    await sleep(110);
  }

  const accF = pass / E.cases.length;
  const precF = tp + fp ? tp / (tp + fp) : 1;
  const recF = tp + fn ? tp / (tp + fn) : 1;
  const f1 = precF + recF ? (2 * precF * recF) / (precF + recF) : 0;

  renderMetrics({ accuracy: Math.round(accF * 100), precision: Math.round(precF * 100), recall: Math.round(recF * 100), f1 });
  renderBA();
  setStage("evaluate", "done", 100);
  $("meta-evaluate").textContent = `${pass}/${E.cases.length} correct · F1 ${f1.toFixed(3)}`;
  log(`\n📊 Evaluation: accuracy ${Math.round(accF * 100)}% · precision ${Math.round(precF * 100)}% · recall ${Math.round(recF * 100)}% · F1 ${f1.toFixed(3)}`, "c-info");
  log(`🎯 ${pass}/${E.cases.length} golden cases passed — Docker false positive fixed.`, "c-ok");
}

function renderCase(c, ok) {
  const el = document.createElement("div");
  el.className = "case " + (ok ? "pass" : "fail") + (c.trap ? " trap" : "");
  el.innerHTML = `
    <span class="ck">${ok ? "✓" : "✗"}</span>
    <span class="c-title">${escapeHtml(c.title)}</span>
    <span class="c-exp">${c.expected ? "expect: AI" : "expect: not"}</span>
    <span class="c-score">${c.score}/10</span>`;
  $("cases").appendChild(el);
}

function renderMetrics(m) {
  const b = D.eval.before;
  const items = [
    { lbl: "Accuracy", val: m.accuracy + "%", delta: `+${(m.accuracy - b.accuracy).toFixed(0)} pts` },
    { lbl: "Precision", val: m.precision + "%", delta: `+${(m.precision - b.precision).toFixed(1)} pts` },
    { lbl: "Recall", val: m.recall + "%", delta: `±0 (was ${b.recall}%)` },
    { lbl: "F1 Score", val: m.f1.toFixed(3), delta: `+${(m.f1 - b.f1).toFixed(3)}` },
  ];
  $("metrics").innerHTML = items.map((it) => `
    <div class="metric"><div class="m-ring"></div>
      <div class="m-num">${it.val}</div>
      <div class="m-lbl">${it.lbl}</div>
      <div class="m-delta">${it.delta}</div>
    </div>`).join("");
}

function renderBA() {
  const b = D.eval.before, a = D.eval.after;
  $("baRow").innerHTML = `
    <div class="ba-chip before"><b>${b.accuracy}%</b><small>before · ${b.total} cases · F1 ${b.f1}</small></div>
    <div class="ba-arrow">→</div>
    <div class="ba-chip after"><b>${a.accuracy}%</b><small>after · ${a.total} cases · F1 ${a.f1.toFixed(3)}</small></div>
    <div class="ba-fix"><b>Fixed:</b> ${escapeHtml(D.eval.fixedCase)} 🪤<br><span class="hint">${escapeHtml(D.eval.fixNote)}</span></div>`;
}

/* ---------------- feed cards ---------------- */
function trim(s, n = 52) { return s.length > n ? s.slice(0, n - 1) + "…" : s; }

function renderJudging(a) {
  const card = document.createElement("div");
  card.className = "card judging";
  card.innerHTML = `
    <div class="score thinking"><span class="dots"></span></div>
    <div>
      <p class="card-title">${escapeHtml(a.title)}</p>
      <div class="card-meta"><span class="src-pill">${srcLabel(a.source).icon} ${srcLabel(a.source).label}</span> · ▲ ${a.points}</div>
      <div class="card-reason judging-note c-dim">agent judging relevance…</div>
    </div>
    <div class="verdict">…</div>`;
  $("feed").prepend(card);
  return card;
}

function revealVerdict(card, a) {
  const keep = a.relevant;
  card.classList.remove("judging");
  card.classList.add(keep ? "keep" : "bin");
  const score = card.querySelector(".score");
  score.classList.remove("thinking");
  score.classList.add(keep ? "keep" : "bin");
  score.innerHTML = a.aiScore;
  const verdict = card.querySelector(".verdict");
  verdict.className = "verdict " + (keep ? "keep" : "bin");
  verdict.textContent = keep ? "KEEP" : "BIN";
  const note = card.querySelector(".card-reason");
  note.classList.remove("c-dim");
  const tags = a.topics.map((tp) => `<span class="tag">${escapeHtml(tp)}</span>`).join("");
  note.innerHTML = escapeHtml(a.reasoning) + (tags ? `<div>${tags}</div>` : "");
}

/* ---------------- newsletter pages ---------------- */
function todayStr() {
  return new Date().toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" });
}

function buildPages() {
  pages = [];
  if (!NEWS.length) NEWS = D.summaries;
  // Cover page
  const toc = NEWS.map((s) => `<li><span>${escapeHtml(s.topic)}</span><span>${s.count}</span></li>`).join("");
  pages.push(`
    <div class="kicker">AI / ML Daily Digest</div>
    <h1>Today in AI</h1>
    <div class="date">${todayStr()}</div>
    <p>Your automated briefing on the most relevant AI &amp; machine-learning stories,
    curated by a multi-agent pipeline that fetched, filtered, summarized, and wrote this issue.</p>
    <div class="stat-row">
      <div class="stat"><b>${kpi.fetched}</b><span>fetched</span></div>
      <div class="stat"><b>${kpi.kept}</b><span>AI stories</span></div>
      <div class="stat"><b>${NEWS.length}</b><span>topics</span></div>
    </div>
    <h2>In this issue</h2>
    <ul class="toc">${toc}</ul>
    <div class="footer-note">Generated by the AI News Pipeline · Filter → Summarize → Write</div>`);

  // Content pages: 2 topic sections per page
  for (let i = 0; i < NEWS.length; i += 2) {
    const chunk = NEWS.slice(i, i + 2);
    const sections = chunk.map((s) =>
      `<h2>${escapeHtml(s.topic)} <span class="src">· ${s.count} article${s.count > 1 ? "s" : ""}</span></h2>
       <p>${escapeHtml(s.text)}</p>`).join("");
    pages.push(`<div class="kicker">AI / ML Daily Digest</div>${sections}
      <div class="footer-note">Page ${pages.length + 1} · ${todayStr()}</div>`);
  }

  pageIdx = 0;
  renderPages();
}

function renderPages() {
  const wrap = $("pages");
  wrap.innerHTML = "";
  pages.forEach((html, i) => {
    const p = document.createElement("div");
    p.className = "page" + (i === pageIdx ? "" : " hidden");
    p.innerHTML = html;
    wrap.appendChild(p);
  });
  $("pageInd").textContent = `Page ${pageIdx + 1} / ${pages.length}`;
  $("prevPage").disabled = pageIdx === 0;
  $("nextPage").disabled = pageIdx === pages.length - 1;
}

/* ---------------- downloads ---------------- */
function newsletterMarkdown() {
  let md = `# AI / ML Daily Digest\n\n_${todayStr()}_\n\n`;
  md += `**Fetched:** ${kpi.fetched} · **AI stories:** ${kpi.kept} · **Topics:** ${NEWS.length}\n\n---\n\n`;
  for (const s of NEWS) {
    md += `## ${s.topic} (${s.count} article${s.count > 1 ? "s" : ""})\n\n${s.text}\n\n`;
  }
  md += `---\n\n_Generated by the AI News Pipeline (Fetch → Filter → Summarize → Write)._\n`;
  return md;
}

function newsletterHtml() {
  const body = pages.map((p) => `<section style="max-width:720px;margin:0 auto 40px;font-family:Georgia,serif;line-height:1.65">${p}</section>`).join("");
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>AI/ML Daily Digest</title></head><body style="background:#fbfbf8;color:#1a1a1a;padding:40px">${body}</body></html>`;
}

function download(filename, text, type) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
  log(`⬇ Downloaded ${filename}`, "c-info");
}

/* Real PDF: render every newsletter page into one .pdf via html2pdf (bundled). */
function downloadPdf() {
  if (typeof html2pdf === "undefined") {
    log("⚠️ PDF library not loaded — using Print dialog instead.", "c-warn");
    window.print();
    return;
  }
  // Build an off-screen container holding ALL pages (not just the visible one).
  const holder = document.createElement("div");
  holder.style.background = "#fff";
  pages.forEach((html, i) => {
    const p = document.createElement("div");
    p.className = "page";
    p.style.cssText = "box-shadow:none;max-width:720px;margin:0 auto;" + (i ? "page-break-before:always;" : "");
    p.innerHTML = html;
    holder.appendChild(p);
  });
  log("🖨 Generating PDF…", "c-info");
  html2pdf().set({
    margin: 0,
    filename: "AI-Newsletter.pdf",
    image: { type: "jpeg", quality: 0.98 },
    html2canvas: { scale: 2, backgroundColor: "#ffffff" },
    jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
    pagebreak: { mode: ["css", "legacy"] },
  }).from(holder).save().then(() => log("⬇ Downloaded AI-Newsletter.pdf", "c-ok"));
}

/* ---------------- LIVE mode (real backend, real LLM) ---------------- */
function startRun() {
  if (running) return;
  if (MODE === "live") runLive();
  else run();
}

function runLive() {
  running = true;
  $("startBtn").disabled = true;
  $("resetBtn").disabled = false;
  reset(true);                 // clear UI but keep running=true
  NEWS = [];                   // will be filled from real summaries
  const liveSummaries = [];
  const cards = {};            // title -> card element

  log("=".repeat(48), "c-dim");
  log("🔴 LIVE mode — calling the real backend (real fetch + real LLM)…", "c-info");
  log("   (needs the local server: ./venv/Scripts/python.exe -m server)", "c-dim");

  let es;
  try {
    es = new EventSource("/api/run");
  } catch (e) {
    liveError("Could not reach the backend. Start it with: python -m server");
    return;
  }

  const finish = () => { try { es.close(); } catch (_) {} running = false; $("startBtn").disabled = false; };

  es.onmessage = (ev) => {
    let e; try { e = JSON.parse(ev.data); } catch (_) { return; }
    switch (e.type) {
      case "log": log(e.msg, e.cls || "c-dim"); break;
      case "stage": setStage(e.stage, e.state, e.state === "done" ? 100 : null); break;
      case "kpi": kpi.set(e.key, e.val); if (e.key === "kept" || e.key === "fetched") kpi.rate(); break;
      case "article-start": {
        const a = { title: e.title, source: e.source, points: e.points || 0 };
        cards[e.title] = renderJudging(a);
        break;
      }
      case "article-verdict": {
        const card = cards[e.title];
        if (card) revealVerdict(card, {
          relevant: e.keep, aiScore: e.error ? "!" : e.score,
          reasoning: e.reasoning || "", topics: e.topics || [],
        });
        break;
      }
      case "summary": {
        liveSummaries.push({ topic: e.topic, count: e.count, text: e.text });
        log(`   • ${e.topic} (${e.count})`, "c-dim");
        break;
      }
      case "newsletter": {
        NEWS = liveSummaries.length ? liveSummaries : NEWS;
        buildPages();
        $("newsletterPanel").hidden = false;
        $("meta-write").textContent = `${pages.length}-page digest ready`;
        break;
      }
      case "eval-verified": renderEvalStatic(true); break;
      case "fatal": liveError(e.msg); finish(); break;
      case "done":
        log("\n🎉 LIVE run complete.", "c-ok");
        $("evalPanel").scrollIntoView({ behavior: "smooth", block: "start" });
        finish();
        break;
    }
  };
  es.onerror = () => {
    if (running) liveError("Backend not reachable. Run the server, then use http://localhost:8000 (not file:// or GitHub Pages).");
    finish();
  };
}

function liveError(msg) {
  log("🛑 " + msg, "c-bad");
}

/* Instant (non-animated) eval render — used in live mode to show the VERIFIED numbers. */
function renderEvalStatic(verified) {
  const E = D.eval;
  $("evalPanel").hidden = false;
  $("cases").innerHTML = "";
  E.cases.forEach((c) => renderCase(c, (c.score >= E.threshold) === c.expected));
  renderMetrics({ accuracy: E.after.accuracy, precision: E.after.precision, recall: E.after.recall, f1: E.after.f1 });
  renderBA();
  $("caseCount").textContent = `(${E.cases.length} cases · ${verified ? "verified run — live eval skipped to save quota" : ""})`;
  $("meta-evaluate").textContent = `verified: F1 ${E.after.f1.toFixed(3)}`;
}

/* ---------------- reset ---------------- */
function reset(keepRunning) {
  if (!keepRunning) running = false;
  NEWS = D.summaries;
  ["fetch", "db", "filter", "summarize", "write", "evaluate"].forEach((s) => { setStage(s, null, 0); $("bar-" + s).style.width = "0%"; });
  ["fetched", "kept", "binned", "topics"].forEach((k) => kpi.set(k, 0));
  $("kpi-rate").textContent = "—";
  $("meta-fetch").textContent = "Pull articles from sources";
  $("meta-db").textContent = "Store in SQLite (MCP)";
  $("meta-filter").textContent = "AI agent judges relevance";
  $("meta-summarize").textContent = "Group by topic + summarize";
  $("meta-write").textContent = "Compose the newsletter";
  $("meta-evaluate").textContent = "Score vs golden dataset";
  $("feed").innerHTML = `<div class="empty">Press <b>Start Pipeline</b> to begin the simulation.</div>`;
  $("console").innerHTML = "";
  $("newsletterPanel").hidden = true;
  $("evalPanel").hidden = true;
  $("cases").innerHTML = "";
  $("metrics").innerHTML = "";
  $("baRow").innerHTML = "";
  if (!keepRunning) { $("startBtn").disabled = false; $("resetBtn").disabled = true; }
}

/* ---------------- util ---------------- */
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------------- wire up ---------------- */
$("speed").addEventListener("change", (e) => { SPEED = parseFloat(e.target.value); });
$("mode").addEventListener("change", (e) => {
  MODE = e.target.value;
  $("modeNote").innerHTML = MODE === "live"
    ? "<b>Live</b> mode · real fetch + real LLM · needs local server (<code>python -m server</code>)"
    : "<b>Replay</b> mode · no LLM calls · runs anywhere";
  $("startBtn").textContent = MODE === "live" ? "▶ Run LIVE pipeline" : "▶ Start Pipeline";
});
$("startBtn").addEventListener("click", startRun);
$("resetBtn").addEventListener("click", () => reset());
$("prevPage").addEventListener("click", () => { if (pageIdx > 0) { pageIdx--; renderPages(); } });
$("nextPage").addEventListener("click", () => { if (pageIdx < pages.length - 1) { pageIdx++; renderPages(); } });
$("dlPdf").addEventListener("click", downloadPdf);
$("dlMd").addEventListener("click", () => download("newsletter.md", newsletterMarkdown(), "text/markdown"));
$("dlHtml").addEventListener("click", () => download("newsletter.html", newsletterHtml(), "text/html"));
$("printBtn").addEventListener("click", () => window.print());
