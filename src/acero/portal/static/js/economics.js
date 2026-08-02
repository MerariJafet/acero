"use strict";
// 💰 Modo Económico — asesor sobre datos REALES de NEXUS. 3 paneles: izquierda =
// snapshot financiero (ingresos/gastos/cuentas), centro = diálogo con el asesor
// (ideas de crecimiento + cuestionar cada idea hasta que funcione), derecha =
// lienzo de estrategia (salud, gráfico SVG, plan de gasto). Nunca inventa cifras;
// no ejecuta transacciones; planea, tú decides.
import { get, post } from "./api.js";
import { esc } from "./components.js";

const S = { sid: null, data: null };

export async function renderEconomics(view, cb) {
  if (!S.sid) { await renderStart(view, cb); return; }
  await refresh();
  paint(view, cb);
}

async function refresh() {
  const { ok, body } = await get(`/portal/api/economics/${encodeURIComponent(S.sid)}`);
  if (ok) S.data = body;
}

// --- start: goal + resume + snapshot preview ---------------------------------
async function renderStart(view, cb) {
  view.innerHTML = "<p class='loading'>Cargando tu economía…</p>";
  const { body } = await get("/portal/api/economics");
  const sessions = (body && body.sessions) || [];
  const snap = (body && body.snapshot) || { available: false };
  const resume = sessions.length ? `
    <section class="learn-resume"><h3>▸ Continúa una conversación</h3>
      <div class="learn-sesslist">${sessions.map((s) => `
        <button class="learn-sesscard" data-resume="${esc(s.session_id)}">
          <b>${esc(s.goal || "(sin meta)")}</b>
          <span class="tag">${esc((s.created_at || "").slice(0, 10))}</span></button>`).join("")}</div>
    </section>` : "";
  view.innerHTML = `<div class="learn-start">
    <h1>💰 Modo Económico</h1>
    <p class="muted">Diálogos e ideas para <b>generar recursos y sostener una economía sana</b>,
    apoyado en tus datos reales de <b>NEXUS</b>. El asesor cuestiona cada idea hasta que
    funcione. No es asesoría de inversión; planea, tú decides.</p>
    <div class="econ-snapprev">${snapshotHTML(snap)}</div>
    <form id="econ-form" class="learn-startform">
      <input id="econ-goal" placeholder="Tu meta: ej. crecer 20% en 6 meses, ahorrar para X…"
        autocomplete="off" aria-label="Meta económica">
      <button class="act" type="submit">Empezar ▸</button>
    </form>
    ${resume}</div>`;
  view.querySelector("#econ-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const goal = view.querySelector("#econ-goal").value.trim();
    view.innerHTML = "<p class='loading'>El asesor analiza tu economía…</p>";
    const { ok, body: b } = await post("/portal/api/economics/start", { goal });
    if (!ok) { view.innerHTML = "<p class='err'>No se pudo iniciar.</p>"; return; }
    S.sid = b.session_id; S.data = null; renderEconomics(view, cb);
  });
  view.querySelectorAll("[data-resume]").forEach((b) =>
    b.addEventListener("click", () => { S.sid = b.dataset.resume; S.data = null; renderEconomics(view, cb); }));
}

// --- 3-pane -------------------------------------------------------------------
function paint(view, cb) {
  const d = S.data || {};
  const snap = (d.session && d.session.snapshot) || { available: false };
  const msgs = d.messages || [];
  const last = [...msgs].reverse().find((m) => m.turn)?.turn || {};
  view.innerHTML = `<div class="learn-shell">
    <aside class="learn-pane learn-left">
      <div class="learn-paneh">💵 NEXUS — tu dinero</div>${snapshotHTML(snap)}
      <button class="act ghost learn-reset" id="econ-reset">＋ Nueva conversación</button>
    </aside>
    <main class="learn-pane learn-center">
      ${adviceHTML(last)}
      <div class="learn-msgs" id="econ-msgs">${msgs.map(msgHTML).join("")}</div>
      <form id="econ-ask" class="learn-askform">
        <input id="econ-q" placeholder="Pregunta, propón una idea, o pide estrategia…" autocomplete="off">
        <button class="act" type="submit">Enviar</button>
      </form>
    </main>
    <aside class="learn-pane learn-right">
      <div class="learn-paneh">📈 Estrategia</div>${canvasHTML(last)}
    </aside></div>`;

  view.querySelector("#econ-reset").addEventListener("click", () => {
    S.sid = null; S.data = null; renderEconomics(view, cb);
  });
  view.querySelector("#econ-ask").addEventListener("submit", async (e) => {
    e.preventDefault();
    const inp = view.querySelector("#econ-q");
    const q = inp.value.trim(); if (!q) return;
    inp.disabled = true;
    await post(`/portal/api/economics/${S.sid}/ask`, { message: q });
    await refresh(); paint(view, cb);
  });
  // cuestionar / promover cada idea
  view.querySelectorAll("[data-critique]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true; b.textContent = "⏳ cuestionando…";
      const { ok, body } = await post(`/portal/api/economics/${S.sid}/critique`, { idea: b.dataset.critique });
      const v = ok && body.verdict ? body.verdict : { verdict: "?", why: "error" };
      const box = b.closest(".econ-idea").querySelector(".econ-verdict");
      const cls = { viable: "ok", needs_work: "warn", reject: "bad" }[v.verdict] || "";
      box.innerHTML = `<span class="pill ${cls}">${esc(v.verdict)}</span> ${esc(v.why || "")}`
        + (v.fixes && v.fixes.length ? `<ul>${v.fixes.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>` : "");
      b.disabled = false; b.textContent = "🔎 Cuestionar";
    }));
  view.querySelectorAll("[data-promote]").forEach((b) =>
    b.addEventListener("click", async () => {
      await post(`/portal/api/economics/${S.sid}/promote`, { idea: b.dataset.promote });
      b.textContent = "✓ en proyectos"; b.disabled = true;
    }));
}

// --- pieces -------------------------------------------------------------------
function money(v, cur) { return (v == null) ? "—" : `${cur || ""} ${Number(v).toLocaleString()}`.trim(); }

function snapshotHTML(s) {
  if (!s || !s.available) {
    return `<div class="canvas-card"><p class="tag">Sin datos de NEXUS.</p>
      <p class="tag">${esc((s && s.reason) || "Conecta NEXUS (ACERO_NEXUS_URL/TOKEN) o importa un snapshot.")}</p></div>`;
  }
  const cats = (s.expenses_by_category || []);
  const max = Math.max(1, ...cats.map((c) => Math.abs(c.amount || 0)));
  return `<div class="canvas-card">
    <div class="econ-kpis">
      <div class="econ-kpi"><b>${money(s.income, s.currency)}</b><span>ingresos</span></div>
      <div class="econ-kpi"><b>${money(s.expenses, s.currency)}</b><span>gastos</span></div>
      <div class="econ-kpi"><b class="${(s.net || 0) >= 0 ? "pos" : "neg"}">${money(s.net, s.currency)}</b><span>neto</span></div>
    </div>
    <div class="tag">fuente: ${esc(s.source || "?")}</div></div>
    <div class="canvas-card"><h4>Gasto por categoría</h4>${cats.length ? cats.map((c) => `
      <div class="econ-bar"><span>${esc(c.category)}</span>
        <div class="econ-track"><div class="econ-fill" style="width:${Math.round(100 * Math.abs(c.amount || 0) / max)}%"></div></div>
        <b>${money(c.amount, s.currency)}</b></div>`).join("") : "<p class='tag'>—</p>"}</div>
    ${(s.accounts || []).length ? `<div class="canvas-card"><h4>Cuentas</h4>${
      s.accounts.map((a) => `<div class="term"><b>${esc(a.name)}</b>: ${money(a.balance, s.currency)}</div>`).join("")}</div>` : ""}`;
}

function adviceHTML(t) {
  if (!t || !t.analysis) return "";
  const ideas = (t.growth_ideas || []).map((i) => `
    <div class="econ-idea">
      <b>${esc(i.title)}</b> — <span class="tag">${esc(i.hook || "")}</span>
      <div class="tag">efecto esperado: ${esc(i.expected_effect || "")}</div>
      <div class="chat-actions">
        <button class="act ghost" data-critique="${esc(i.title + ": " + (i.hook || ""))}">🔎 Cuestionar</button>
        <button class="act ghost" data-promote="${esc(i.title)}">🚀 Promover</button></div>
      <div class="econ-verdict"></div>
    </div>`).join("");
  const q = (t.questions || []).length ? `<div class="tag">Preguntas: ${t.questions.map(esc).join(" · ")}</div>` : "";
  return `<div class="econ-advice">${ideas ? `<h4>Ideas de crecimiento</h4>${ideas}` : ""}${q}</div>`;
}

function msgHTML(m) {
  if (m.role === "user") return `<div class="learn-msg you"><p>${esc(m.text || "")}</p></div>`;
  const t = m.turn || {};
  const ins = (t.insights || []).map((x) => `<li>${esc(x)}</li>`).join("");
  return `<div class="learn-msg tutor"><p>${esc(t.analysis || "")}</p>${
    ins ? `<ul>${ins}</ul>` : ""}</div>`;
}

function canvasHTML(t) {
  const parts = [];
  const h = t.health;
  if (h) {
    const pct = Math.round(100 * (h.score || 0));
    parts.push(`<div class="canvas-card"><h4>Salud financiera</h4>
      <div class="econ-track big"><div class="econ-fill" style="width:${pct}%"></div></div>
      <div class="tag">${pct}% — ${esc(h.reason || "")}</div></div>`);
  }
  if (t.canvas_svg && t.canvas_svg.includes("<svg")) {
    const uri = "data:image/svg+xml;utf8," + encodeURIComponent(t.canvas_svg);
    parts.push(`<div class="canvas-card"><h4>Visual</h4><img class="learn-svg" src="${uri}" alt="gráfico"></div>`);
  }
  if ((t.spend_strategy || []).length) {
    parts.push(`<div class="canvas-card"><h4>Estrategia de gasto</h4><ul>${
      t.spend_strategy.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>`);
  }
  if ((t.risks || []).length) {
    parts.push(`<div class="canvas-card"><h4>Riesgos</h4><ul>${
      t.risks.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>`);
  }
  return parts.join("") || "<p class='muted'>La estrategia aparece al conversar.</p>";
}
