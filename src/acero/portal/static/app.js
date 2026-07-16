"use strict";
// ACERO portal SPA — zero-dependency vanilla JS. Talks to the real API under /portal/api.
const $ = (sel) => document.querySelector(sel);
const api = async (path, opts) => {
  const r = await fetch(path, opts);
  const body = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, body };
};
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
const kv = (k, v) => `<div class="kv"><span>${esc(k)}</span><b>${esc(v)}</b></div>`;
const panel = (title, inner) => `<div class="panel"><h2>${esc(title)}</h2>${inner}</div>`;

const VIEWS = {
  "Overview": async () => {
    const { body } = await api("/portal/api/overview");
    $("#version").textContent = "v" + (body.version || "?");
    const q = Object.entries(body.runtime_queue || {}).map(([k, v]) => `${k}:${v}`).join(" ") || "empty";
    return panel("System overview",
      kv("env", body.env) + kv("LLM provider", body.llm_provider) + kv("sandbox", body.sandbox) +
      kv("gate rules", body.gate_rules) + kv("runtime queue", q) +
      kv("readiness ceiling", body.readiness_ceiling) +
      kv("auto-publication", body.auto_publication ? "ON (!)" : "OFF"));
  },
  "Research Programs": async () => {
    const { body } = await api("/portal/api/programs");
    if (!body.length) return panel("Research Programs", "<p class='loading'>none yet — create with <code>acero program create</code></p>");
    return panel("Research Programs", body.map((p) =>
      `<div class="kv"><span>${esc(p.mission)} <span class="pill ok">${esc(p.status)}</span></span>` +
      `<b>${esc((p.domains || []).join(","))}</b></div>`).join(""));
  },
  "Reliability": async () => {
    const { body } = await api("/portal/api/reliability");
    const dims = Object.entries(body.card.dimensions).map(([n, d]) =>
      kv(n, d.measurement === null ? "n/a" : d.measurement)).join("");
    const rt = body.red_team;
    return panel("Reliability card (no single trust score)", dims) +
      panel("Red team", kv("detected", `${rt.detected}/${rt.n}`) + kv("missed", (rt.missed || []).join(",") || "none"));
  },
  "Red Team": async () => {
    const { body } = await api("/portal/api/reliability");
    const rt = body.red_team;
    return panel("Adversarial test matrix",
      Object.entries(rt.by_category).map(([c, s]) =>
        kv(c, `${s.detected}/${s.total} <span class="pill ${s.detected === s.total ? 'ok' : 'bad'}">${s.detected === s.total ? 'all' : 'GAP'}</span>`)).join(""));
  },
  "Runtime": async () => {
    const { body } = await api("/portal/api/runtime");
    return panel("Persistent runtime",
      kv("tasks", body.n_tasks) +
      Object.entries(body.by_status || {}).map(([k, v]) => kv(k, v)).join(""));
  },
  "Self-Evaluation": async () => {
    const { body } = await api("/portal/api/evaluation");
    const bm = Object.entries(body.benchmarks).map(([b, v]) =>
      kv(b, `<span class="pill ${v.passed ? 'ok' : 'bad'}">${v.passed ? 'pass' : 'FAIL'}</span> ${JSON.stringify(v.metrics)}`)).join("");
    const caps = body.capabilities.map((c) =>
      kv(c.name, `<span class="pill ${c.status === 'DEGRADED' ? 'bad' : c.status === 'EXPERIMENTAL' ? 'warn' : 'ok'}">${c.status}</span>`)).join("");
    return panel("Verdict: " + esc(body.verdict),
      kv("version", body.version) + kv("prompts", `${body.prompts.passed}/${body.prompts.n}`) +
      kv("regression", body.regression.has_regression ? "REGRESSED" : "none")) +
      panel("Benchmark status", bm) + panel("Capability registry", caps) +
      `<p class="loading">${esc(body.note)}</p>`;
  },
  "Review": async () => {
    const { body } = await api("/portal/api/review");
    return panel("Human Scientific Review Gauntlet",
      kv("cases passed", `${body.passed}/${body.n}`) + kv("all passed", body.all_passed) +
      Object.entries(body.cases).map(([k, c]) =>
        kv(k, `<span class="pill ${c.passed ? 'ok' : 'bad'}">${c.passed ? 'pass' : 'FAIL'}</span>`)).join(""));
  },
  "Collaboration": async () => {
    const { body } = await api("/portal/api/collaboration");
    const qs = body.review_questions.map((q) => `<li>${esc(q)}</li>`).join("");
    return panel("External Review Preparation (NOT external review)",
      kv("gauntlet", `${body.gauntlet.passed}/${body.gauntlet.n} ` +
        `<span class="pill ${body.gauntlet.all_passed ? 'ok' : 'bad'}">${body.gauntlet.all_passed ? 'ok' : 'FAIL'}</span>`) +
      kv("AI authorship", body.ai_authorship_allowed ? "ALLOWED(!)" : "never")) +
      panel("Review questions", `<ul>${qs}</ul>`) +
      `<p class="loading">${esc(body.note)}</p>`;
  },
  "World Model": async () => {
    return panel("World Model Explorer",
      "<p class='loading'>Enter a project id:</p><input id='wm-pid' placeholder='project id'>" +
      "<button class='act' onclick='window.__wm()'>Query</button><div id='wm-out'></div>");
  },
  "Decision Center": async () => {
    const { body } = await api("/portal/api/decision");
    const rows = ["context", "uncertainty", "cost", "risk", "recommendation", "why_not_execute"]
      .map((k) => kv(k, body[k])).join("");
    const ev = "<p><b>Evidence:</b> " + body.evidence.map(esc).join("; ") + "</p>";
    const ce = "<p><b>Counter-evidence:</b> " + body.counter_evidence.map(esc).join("; ") + "</p>";
    const btns = body.actions.map((a) =>
      `<button class="act ${a === 'REJECT' ? 'danger' : ''}" onclick="window.__decide('${a}')">${a}</button>`).join("");
    return panel("Decision: " + esc(body.question), ev + ce + rows +
      "<p><input id='dec-reason' placeholder='reason (required to APPROVE)'></p>" + btns +
      "<div id='dec-out'></div>");
  },
  "Projects": async () => panel("Projects", "<p class='loading'>Use <code>acero project init</code>; project views read via the API.</p>"),
  "Publication Candidates": async () => {
    const { body } = await api("/publication/candidate");
    return panel("Publication candidate",
      kv("readiness", body.readiness) + kv("auto-publish", body.can_publish_automatically ? "ON(!)" : "OFF") +
      kv("blockers", (body.blockers || []).join("; ") || "none"));
  },
  "Settings": async () => panel("Settings",
    "<p>Local-first. No secrets are shown here. Secret mode via <code>acero secrets status</code>.</p>" +
    kv("auto-publication", "forbidden by policy") + kv("reviewer", "must be a human (not ACERO)")),
};

window.__wm = async () => {
  const pid = $("#wm-pid").value.trim();
  if (!pid) return;
  const { ok, body } = await api("/portal/api/world/" + encodeURIComponent(pid));
  $("#wm-out").innerHTML = ok ? Object.entries(body).map(([k, v]) => kv(k, JSON.stringify(v))).join("")
    : `<p class="err">${esc(body.detail || "error")}</p>`;
};
window.__decide = async (decision) => {
  const reason = $("#dec-reason").value;
  const { ok, status, body } = await api("/portal/api/decision",
    { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, reason }) });
  $("#dec-out").innerHTML = ok
    ? `<p class="pill ok">recorded ${esc(body.recorded)}</p> <span class="loading">${esc(body.note)}</span>`
    : `<p class="err">blocked (${status}): ${esc(body.detail)}</p>`;
};

let current = "Overview";
async function render(name) {
  current = name;
  document.querySelectorAll("#nav button").forEach((b) =>
    b.classList.toggle("active", b.textContent === name));
  $("#view").innerHTML = "<p class='loading'>Loading…</p>";
  try {
    $("#view").innerHTML = await VIEWS[name]();
  } catch (e) {
    $("#view").innerHTML = `<p class="err">failed to load ${esc(name)}: ${esc(e.message)}</p>`;
  }
}
async function boot() {
  const { body } = await api("/portal/api/overview");
  const sections = (body.sections || Object.keys(VIEWS));
  $("#nav").innerHTML = sections.map((s) =>
    `<button ${VIEWS[s] ? "" : "disabled"}>${esc(s)}</button>`).join("");
  document.querySelectorAll("#nav button").forEach((b) =>
    b.addEventListener("click", () => VIEWS[b.textContent] && render(b.textContent)));
  render("Overview");
}
boot();
