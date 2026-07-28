"use strict";
// 🎓 Modo Learning — tutor socrático de 3 paneles: izquierda = árbol anidado de tu
// recorrido, centro = chat con el tutor, derecha = lienzo (fórmulas, diagrama,
// términos, conexiones). Cuando el tutor detecta que rozas una pregunta abierta,
// muestra una alerta y el botón para convertirla en una investigación real.
import { get, post } from "./api.js";
import { esc } from "./components.js";

const S = { sid: null, cur: null, data: null };

export async function renderLearning(view, cb) {
  if (!S.sid) { view.innerHTML = starter(); wireStarter(view, cb); return; }
  await refresh();
  paint(view, cb);
}

// --- topic starter ------------------------------------------------------------
const SEEDS = ["Mecánica cuántica", "Epigenética", "Agujeros negros",
  "Teoría de números", "Inmunología", "Consciencia"];

function starter() {
  return `<div class="learn-start">
    <h1>🎓 Modo Aprender</h1>
    <p class="muted">Elige un tema y baja de lo general a la <b>frontera del conocimiento</b>.
    El tutor te guía, ramificas en cada concepto, y cuando roces una pregunta sin
    respuesta podrás convertirla en una investigación.</p>
    <form id="learn-form" class="learn-startform">
      <input id="learn-topic" placeholder="Ej: Mecánica cuántica, CRISPR, agujeros negros…"
        autocomplete="off" aria-label="Tema a aprender">
      <button class="act" type="submit">Comenzar ▸</button>
    </form>
    <div class="learn-suggest">${SEEDS.map((t) =>
      `<button class="act ghost" data-topic="${esc(t)}">${esc(t)}</button>`).join("")}</div>
  </div>`;
}

function wireStarter(view, cb) {
  const go = async (topic) => {
    if (!topic) return;
    view.innerHTML = "<p class='loading'>El tutor está preparando tu lección…</p>";
    const { ok, body } = await post("/portal/api/learning/start", { topic });
    if (!ok) { view.innerHTML = "<p class='err'>No se pudo iniciar la lección.</p>"; return; }
    S.sid = body.session_id; S.cur = body.node_id; S.data = null;
    await renderLearning(view, cb);
  };
  view.querySelector("#learn-form").addEventListener("submit", (e) => {
    e.preventDefault(); go(view.querySelector("#learn-topic").value.trim());
  });
  view.querySelectorAll("[data-topic]").forEach((b) =>
    b.addEventListener("click", () => go(b.dataset.topic)));
}

async function refresh() {
  const { ok, body } = await get(`/portal/api/learning/${encodeURIComponent(S.sid)}`);
  if (ok) S.data = body;
}

// --- 3-pane render ------------------------------------------------------------
function paint(view, cb) {
  const tree = S.data.tree;
  const msgs = S.data.messages.filter((m) => m.node_id === S.cur);
  const lastTurn = [...msgs].reverse().find((m) => m.role === "assistant" && m.turn)?.turn || {};
  view.innerHTML =
    `<div class="learn-shell">
       <aside class="learn-pane learn-left">
         <div class="learn-paneh">🧭 Tu recorrido</div>
         ${treeHTML(tree, S.cur)}
         <button class="act ghost learn-reset" id="learn-reset">＋ Nuevo tema</button>
       </aside>
       <main class="learn-pane learn-center">
         ${frontierBanner(lastTurn.frontier)}
         <div class="learn-msgs" id="learn-msgs">${msgs.map(msgHTML).join("") ||
           "<p class='muted'>…</p>"}</div>
         ${subtopicsHTML(lastTurn.subtopics)}
         <form id="learn-ask" class="learn-askform">
           <input id="learn-q" placeholder="Pregunta algo o profundiza…" autocomplete="off">
           <button class="act" type="submit">Enviar</button>
         </form>
       </main>
       <aside class="learn-pane learn-right">
         <div class="learn-paneh">🎨 Lienzo</div>
         <div id="learn-canvas">${canvasHTML(lastTurn)}</div>
       </aside>
     </div>`;
  renderMath(view); renderDiagrams(view);

  view.querySelectorAll("[data-node]").forEach((b) =>
    b.addEventListener("click", () => { S.cur = b.dataset.node; paint(view, cb); }));

  view.querySelectorAll("[data-drill]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true; b.textContent = "⏳ " + b.textContent;
      const { ok, body } = await post(`/portal/api/learning/${S.sid}/drill`,
        { parent_id: S.cur, subtopic: b.dataset.drill });
      if (ok) { S.cur = body.node_id; await refresh(); paint(view, cb); }
    }));

  view.querySelector("#learn-ask").addEventListener("submit", async (e) => {
    e.preventDefault();
    const inp = view.querySelector("#learn-q");
    const q = inp.value.trim(); if (!q) return;
    inp.disabled = true;
    const holder = view.querySelector("#learn-msgs");
    holder.insertAdjacentHTML("beforeend", msgHTML({ role: "user", text: q })
      + "<div class='learn-msg tutor pending'>el tutor piensa…</div>");
    holder.scrollTop = holder.scrollHeight;
    const { ok } = await post(`/portal/api/learning/${S.sid}/ask`,
      { node_id: S.cur, message: q });
    if (ok) { await refresh(); paint(view, cb); }
    else inp.disabled = false;
  });

  view.querySelector("#learn-reset").addEventListener("click", () => {
    S.sid = null; S.cur = null; S.data = null; renderLearning(view, cb);
  });

  const promo = view.querySelector("#learn-promote");
  if (promo) promo.addEventListener("click", async () => {
    const q = promo.dataset.q;
    if (!confirm(`¿Convertir esto en una investigación de ACERO?\n\n"${q}"`)) return;
    promo.disabled = true; promo.textContent = "⏳ creando proyecto…";
    const { ok, body } = await post(`/portal/api/learning/${S.sid}/promote`, { question: q });
    if (ok && body.project) cb.openProject(body.project.id);
    else { promo.disabled = false; promo.textContent = "🚀 Crear investigación"; }
  });
}

// --- pieces -------------------------------------------------------------------
function treeHTML(tree, cur) {
  const nodes = tree.nodes;
  const kids = (pid) => tree.order.filter((id) => nodes[id].parent === pid);
  const li = (id) => {
    const n = nodes[id];
    const c = kids(id);
    return `<li><button class="learn-node ${id === cur ? "active" : ""}"
      data-node="${esc(id)}">${esc(n.title)}</button>${
      c.length ? `<ul>${c.map(li).join("")}</ul>` : ""}</li>`;
  };
  return tree.root ? `<ul class="learn-tree">${li(tree.root)}</ul>` : "";
}

function msgHTML(m) {
  const who = m.role === "user" ? "you" : "tutor";
  return `<div class="learn-msg ${who}">${md(m.text || "")}</div>`;
}

function subtopicsHTML(subs) {
  if (!subs || !subs.length) return "";
  return `<div class="learn-subs"><span class="tag">Profundiza en:</span>${
    subs.map((s) => `<button class="act ghost learn-sub" data-drill="${esc(s.title)}"
      title="${esc(s.hook || "")}">${esc(s.title)} ↴</button>`).join("")}</div>`;
}

function frontierBanner(fr) {
  if (!fr || !fr.near) return "";
  const q = esc(fr.open_question || "");
  return `<div class="learn-frontier">
    <div><b>🛰️ Estás rozando la frontera del conocimiento.</b>
    <div class="tag">${esc(fr.why || "")}</div>
    <div class="learn-openq">${q}</div></div>
    <button class="act learn-promo" id="learn-promote" data-q="${q}">🚀 Crear investigación</button>
  </div>`;
}

function canvasHTML(t) {
  const parts = [];
  if (t.formulas && t.formulas.length) {
    parts.push(`<div class="canvas-card"><h4>Fórmulas</h4>${t.formulas.map((f) =>
      `<div class="formula" data-latex="${esc(f.latex)}"></div>
       <div class="tag">${esc(f.caption || "")}</div>`).join("")}</div>`);
  }
  if (t.diagram_mermaid) {
    parts.push(`<div class="canvas-card"><h4>Diagrama</h4>
      <div class="mermaid">${esc(t.diagram_mermaid)}</div></div>`);
  }
  if (t.key_terms && t.key_terms.length) {
    parts.push(`<div class="canvas-card"><h4>Términos clave</h4>${t.key_terms.map((k) =>
      `<div class="term"><b>${esc(k.term)}</b>: ${esc(k.definition)}</div>`).join("")}</div>`);
  }
  if (t.connections && t.connections.length) {
    parts.push(`<div class="canvas-card"><h4>Conexiones</h4><ul>${
      t.connections.map((c) => `<li>${esc(c)}</li>`).join("")}</ul></div>`);
  }
  return parts.join("") || "<p class='muted'>El lienzo se llena a medida que avanzas.</p>";
}

// minimal, safe markdown: escape first, then a few inline styles + line breaks
function md(s) {
  let t = esc(s);
  t = t.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
       .replace(/`([^`]+)`/g, "<code>$1</code>")
       .replace(/\n{2,}/g, "</p><p>").replace(/\n/g, "<br>");
  return `<p>${t}</p>`;
}

// KaTeX / Mermaid render with graceful fallback (libs loaded from CDN in index.html)
function renderMath(view) {
  view.querySelectorAll(".formula[data-latex]").forEach((el) => {
    const tex = el.getAttribute("data-latex");
    if (window.katex) {
      try { window.katex.render(tex, el, { throwOnError: false, displayMode: true }); return; }
      catch (_e) { /* fall through */ }
    }
    el.innerHTML = `<code>${esc(tex)}</code>`;
  });
}

function renderDiagrams(view) {
  const els = view.querySelectorAll(".mermaid");
  if (!els.length) return;
  if (window.mermaid && window.mermaid.run) {
    try { window.mermaid.run({ nodes: els }); return; } catch (_e) { /* fallback */ }
  }
  els.forEach((el) => { el.innerHTML = `<pre>${el.textContent}</pre>`; });
}
