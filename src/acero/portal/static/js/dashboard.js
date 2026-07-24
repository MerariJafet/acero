"use strict";
import { get, post } from "./api.js";
import { esc, kv, pill } from "./components.js";

// CIO-style dashboards: home (all investigations), project-by-phases, phase detail,
// educational plan (floating panel), courses list, and the LMS course viewer.
// `cb` = callbacks from app.js: { openProject, openPhase, openCourse, openCourses,
//        openHome, setContext, refreshProjects }

/* ------------------------------------------------------------------ home -- */
export async function renderHome(view, cb) {
  view.innerHTML = "<p class='loading'>Cargando investigaciones…</p>";
  const [{ body: projs }, { body: courses }] = await Promise.all([
    get("/portal/api/projects"), get("/portal/api/courses")]);
  const list = Array.isArray(projs) ? projs : [];
  const nPapers = list.reduce((a, p) => a + (p.events ? 0 : 0), 0); // events≠papers; fetch below
  const totals = {
    projects: list.length,
    hyps: list.reduce((a, p) => a + (p.hypotheses || 0), 0),
    exps: list.reduce((a, p) => a + (p.experiments || 0), 0),
    nodes: list.reduce((a, p) => a + (p.world_nodes || 0), 0),
    courses: Array.isArray(courses) ? courses.length : 0,
  };
  const cards = list.map((p) => {
    const empty = (p.status || "").startsWith("empty");
    return `<div class="proj-card" data-pid="${esc(p.id)}" role="button" tabindex="0"
      aria-label="Abrir investigación ${esc(p.title)}">
      <h3>${esc(p.title)}</h3>
      <div>${pill(p.domain)} ${pill(empty ? "vacío" : "en progreso", empty ? "warn" : "ok")}</div>
      <div class="tag">Hipótesis ${p.hypotheses} · Experimentos ${p.experiments} ·
        Conocimiento ${p.world_nodes} · Eventos ${p.events}</div>
      <div class="tag">Última actividad: ${esc(p.last_activity || "—")}</div>
      <div class="proj-open">Entrar →</div></div>`;
  }).join("");
  view.innerHTML =
    `<div class="proj-head"><h1>Panel general de investigación</h1>
       <p class="muted">Todas tus investigaciones. Usa el chat para preguntar de forma general,
       o entra a una investigación para su flujo completo.</p></div>
     <div class="stat-strip">
       <div class="stat"><b>${totals.projects}</b><span>investigaciones</span></div>
       <div class="stat"><b>${totals.hyps}</b><span>hipótesis</span></div>
       <div class="stat"><b>${totals.exps}</b><span>experimentos</span></div>
       <div class="stat"><b>${totals.nodes}</b><span>nodos de conocimiento</span></div>
       <div class="stat"><b>${totals.courses}</b><span>cursos</span></div>
     </div>
     <div class="proj-grid">${cards ||
       "<p class='muted'>No hay investigaciones aún — crea una con «＋ Nuevo proyecto».</p>"}</div>`;
  view.querySelectorAll(".proj-card").forEach((c) => {
    const open = () => cb.openProject(c.dataset.pid);
    c.addEventListener("click", open);
    c.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
    });
  });
}

/* --------------------------------------------------------- project phases -- */
function ring(pct, color = "var(--accent)") {
  const p = Math.max(0, Math.min(100, pct || 0));
  return `<div class="ring" style="background:conic-gradient(${color} ${p * 3.6}deg, #222b36 0)">
            <span>${p}%</span></div>`;
}

function barRows(bars) {
  if (!bars || !bars.length) return "<p class='muted tag'>sin datos aún</p>";
  return bars.map((b) =>
    `<div class="bar-row"><span class="bar-label">${esc(b.label)}</span>
       <span class="bar-track"><span class="bar-fill" style="width:${b.pct}%"></span></span>
       <span class="bar-right">${esc(b.right || b.value)}</span></div>`).join("");
}

export async function renderProjectDash(view, pid, cb) {
  view.innerHTML = "<p class='loading'>Cargando investigación…</p>";
  const [{ ok, body: ph }, { body: st }] = await Promise.all([
    get(`/portal/api/projects/${encodeURIComponent(pid)}/phases`),
    get(`/portal/api/projects/${encodeURIComponent(pid)}/status`)]);
  if (!ok) { view.innerHTML = "<p class='err'>No se pudo cargar la investigación.</p>"; return; }
  const k = ph.kpis || {};
  const today = (ph.created_at || "").slice(0, 10);

  // --- full-width horizontal phase sections (read top → bottom) ------------
  const phaseRows = ph.phases.map((f) => {
    const items = (f.items || []).slice(0, 4).map((i) =>
      `<div class="kv"><span>${esc((i.title || "").slice(0, 70))}</span>` +
      `<b class="tag">${esc(i.meta || "")}${i.flag ? " · " + esc(i.flag) : ""}</b></div>`).join("");
    return `<section class="phase-row" data-phase="${esc(f.key)}" aria-label="${esc(f.title)}">
      <button class="phase-head" aria-expanded="true" data-toggle="${esc(f.key)}">
        <span class="phase-state ${esc(f.state)}" aria-hidden="true"></span>
        <span class="ph-title">${esc(f.icon)} ${esc(f.title)}</span>
        <span class="ph-note">${esc(f.note)}</span>
        <span class="ph-count">${f.count}</span>
        <span class="chev">▾</span>
      </button>
      <div class="phase-body" data-body="${esc(f.key)}">
        <div class="phase-cols">
          <div class="phase-viz">${barRows(f.bars)}</div>
          <div class="phase-items">${items || "<p class='muted tag'>sin items</p>"}
            <button class="phase-open" data-open="${esc(f.key)}">Ver dashboard completo →</button>
          </div>
        </div>
        <div class="phase-comment">
          <input placeholder="Pregunta SOLO sobre ${esc(f.title.toLowerCase())}…"
                 aria-label="Pregunta sobre ${esc(f.title)}" data-q="${esc(f.key)}">
          <button class="act" data-ask="${esc(f.key)}">Preguntar</button>
        </div>
        <div class="phase-answer" data-answer="${esc(f.key)}" aria-live="polite"></div>
      </div>
    </section>`;
  }).join("");

  // --- acciones recomendadas (from real next steps) -------------------------
  const steps = ((st || {}).next_steps || []).slice(0, 3);
  const prio = ["high", "high", "medium"];
  const actions = steps.map((s, i) =>
    `<div class="action-card">
       <div><span class="prio ${prio[i] || "medium"}">prioridad ${prio[i] === "high" ? "HIGH" : "MEDIUM"}</span></div>
       <p>${esc(s.text)}</p>
       <button class="act ghost" data-goto-tabx="${esc(s.tab || "")}" data-pidx="${esc(pid)}">Ir →</button>
     </div>`).join("");

  view.innerHTML =
    `<p class="eyebrow">Pulso de la investigación</p>
     <div class="pulse-head">
       <h1>${esc(ph.title)}</h1>
       <span class="tag">${pill(ph.domain)} ${pill(ph.state, "ok")} · creado ${esc(today)}</span>
     </div>

     <div class="kpi-strip">
       <div class="kpi">${ring(ph.progress_pct, "#4aa3ff")}
         <div><b>${ph.n_phases_done}/${ph.n_phases}</b><span>fases con trabajo</span>
         <span class="tag">flujo completo de investigación</span></div></div>
       <div class="kpi">${ring(k.real_pct, "#2ea043")}
         <div><b>${k.experiments || 0}</b><span>experimentos</span>
         <span class="tag">${k.real_experiments || 0} con datos reales</span></div></div>
       <div class="kpi"><div class="kpi-big">${k.papers || 0}</div>
         <div><b>papers reales</b><span>con DOI + chequeo de retracción</span></div></div>
       <div class="kpi">${ring(k.approved_pct, "#d29922")}
         <div><b>${k.hypotheses || 0}</b><span>hipótesis</span>
         <span class="tag">${k.approved || 0} aprobadas</span></div></div>
       <div class="kpi"><div class="kpi-big">${k.dossiers || 0}</div>
         <div><b>dossiers</b><span>esperan revisión humana</span></div></div>
     </div>

     <div class="narrative-row">
       <p class="narrative">${esc(ph.narrative || "")}</p>
       <div class="narrative-actions">
         <button class="act" id="deep-run">🌌 Investigación a fondo</button>
         <button class="act ghost" id="dash-refresh">↻ Actualizar</button>
       </div>
     </div>

     ${phaseRows}

     <section class="panel actions-panel" aria-label="Acciones recomendadas">
       <p class="eyebrow">★ Acciones recomendadas</p>
       <div class="actions-grid">${actions || "<p class='muted'>sin recomendaciones</p>"}</div>
     </section>
     <p class="tag">${esc(ph.honesty)}</p>`;

  // acciones "Ir →": navegan a la parte correspondiente
  view.querySelectorAll("[data-goto-tabx]").forEach((b) =>
    b.addEventListener("click", () => {
      const t = b.dataset.gotoTabx;
      if (t === "lit") cb.openPhase(pid, "literatura");
      else if (t === "learn") cb.openPhase(pid, "conclusiones");
      else if (t === "chat") document.querySelector("#question").focus();
      else cb.openPhase(pid, "experimentos");
    }));

  // minimize/expand
  view.querySelectorAll("[data-toggle]").forEach((b) =>
    b.addEventListener("click", () => {
      const body = view.querySelector(`[data-body="${b.dataset.toggle}"]`);
      const open = body.style.display !== "none";
      body.style.display = open ? "none" : "";
      b.setAttribute("aria-expanded", String(!open));
      b.querySelector(".chev").textContent = open ? "▸" : "▾";
    }));
  // open phase detail
  view.querySelectorAll("[data-open]").forEach((b) =>
    b.addEventListener("click", () => cb.openPhase(pid, b.dataset.open)));
  // per-section comment bars (scoped copilot questions)
  view.querySelectorAll("[data-ask]").forEach((b) =>
    b.addEventListener("click", async () => {
      const key = b.dataset.ask;
      const input = view.querySelector(`[data-q="${key}"]`);
      const out = view.querySelector(`[data-answer="${key}"]`);
      const q = input.value.trim();
      if (!q) return;
      out.innerHTML = "<span class='loading'>Pensando…</span>";
      b.disabled = true;
      const { ok: aok, body: ans } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/copilot`,
        { message: q, location: { scope: "phase", phase: key } });
      b.disabled = false;
      out.innerHTML = aok && ans.reply
        ? `<div class="card">${esc(ans.reply)}<div class="tag">${esc(ans.disclaimer || "")}</div></div>`
        : `<span class="err">error: ${esc((ans && (ans.detail || ans.error)) || "copiloto")}</span>`;
      input.value = "";
    }));
  view.querySelector("#dash-refresh").addEventListener("click", () => cb.openProject(pid));
  view.querySelector("#deep-run").addEventListener("click", async () => {
    const btn = view.querySelector("#deep-run");
    btn.disabled = true; btn.textContent = "Investigando (1–3 min)…";
    const { ok: dok, body: b } = await post(
      `/portal/api/projects/${encodeURIComponent(pid)}/deep-investigation`, {});
    btn.disabled = false; btn.textContent = "🌌 Investigación a fondo";
    if (dok && b.ok) cb.openProject(pid);
    else alert("Error en la investigación a fondo: " + ((b && (b.detail || b.error)) || ""));
  });
}

const KIND_STYLE = {
  established: ["Ya probado", "warn"], theorized: ["Ya teorizado", "warn"],
  novel: ["Nuevo", "ok"], open_question: ["Pregunta abierta", "bad"],
};

/* ------------------------------------------------------------ phase detail -- */
export async function renderPhaseDetail(view, pid, phaseKey, cb) {
  view.innerHTML = "<p class='loading'>Cargando fase…</p>";
  const { ok, body: ph } = await get(`/portal/api/projects/${encodeURIComponent(pid)}/phases`);
  if (!ok) { view.innerHTML = "<p class='err'>error</p>"; return; }
  const f = ph.phases.find((x) => x.key === phaseKey);
  if (!f) { view.innerHTML = "<p class='err'>fase desconocida</p>"; return; }
  const m = f.methodology || {};

  // literature + experiments are hypothesis-centric dashboards
  if (phaseKey === "literatura" || phaseKey === "experimentos") {
    return renderHypFlow(view, pid, phaseKey, ph, cb);
  }

  // rich, interactive hypothesis cards
  let items;
  if (phaseKey === "hipotesis") {
    items = (f.items || []).map((i, ix) => {
      const [klabel, kcolor] = KIND_STYLE[i.kind] || ["", "warn"];
      const reasoning = (i.trigger_question || i.argument || i.doubt) ? `
        <div class="hyp-reason" data-reason="${ix}" hidden>
          ${i.trigger_question ? `<div class="hyp-field"><b>❓ Pregunta detonante</b><p>${esc(i.trigger_question)}</p></div>` : ""}
          ${i.argument ? `<div class="hyp-field"><b>➕ Argumento a favor</b><p>${esc(i.argument)}</p></div>` : ""}
          ${i.doubt ? `<div class="hyp-field"><b>➖ La duda / qué la falsaría</b><p>${esc(i.doubt)}</p></div>` : ""}
          ${i.competes_with ? `<div class="hyp-field"><b>⚔️ Compite con</b><p>${esc(i.competes_with)}</p></div>` : ""}
          ${i.test_idea ? `<div class="hyp-field"><b>🔬 Cómo probarla</b><p>${esc(i.test_idea)}</p></div>` : ""}
          <div class="hyp-ask">
            <input placeholder="Cuestiona o pregunta sobre ${esc(i.tag)}…" data-hq="${ix}">
            <button class="act" data-hask="${ix}">Preguntar al copiloto</button>
          </div>
          <div class="hyp-answer" data-hans="${ix}" aria-live="polite"></div>
        </div>` : "";
      const approved = i.meta === "APPROVED";
      const actions = `<div class="hyp-actions">
          ${approved
            ? `<span class="pill ok">✓ Aprobada</span>
               <button class="act ghost" data-hstatus="${esc(i.id)}" data-to="PROPOSED">Desaprobar</button>`
            : `<button class="act" data-happrove="${esc(i.id)}" data-tag="${esc(i.tag)}">✓ Aprobar</button>
               <button class="act ghost" data-hstatus="${esc(i.id)}" data-to="REJECTED">Rechazar</button>`}
        </div>`;
      const anom = i.origin === "anomaly" ? `<span class="pill bad">🔥 nacida de anomalía</span>` : "";
      const anomProv = i.anomaly_provenance
        ? `<p class="tag">🔥 Origen: discrepancia medida en «${esc(i.anomaly_provenance.exp_title || "")}» — ${esc((i.anomaly_provenance.anomaly || "").slice(0, 140))}</p>` : "";
      // novelty filter: steer toward discovery (green = frontier, red = settled)
      const N_COLOR = { asentada: "bad", en_debate: "warn", abierta: "ok", inexplorada: "ok", sin_evaluar: "warn" };
      const N_ICON = { asentada: "🔴 asentada", en_debate: "🟠 en debate", abierta: "🟢 abierta", inexplorada: "🔵 inexplorada", sin_evaluar: "⚪ sin evaluar" };
      const nv = i.novelty;
      const novBadge = nv && nv.status
        ? pill(N_ICON[nv.status] || nv.status, N_COLOR[nv.status] || "warn")
        : `<button class="act ghost small" data-novelty="${esc(i.id)}">🎯 evaluar novedad</button>`;
      const DA = { cross_data: "🔗 cruce de datos", anomaly: "🔥 anomalía/residuo", open_untested: "🧭 abierta sin analizar", untested_prediction: "🎲 predicción sin probar" };
      const daBadge = i.discovery_angle && DA[i.discovery_angle] ? `<span class="src">${esc(DA[i.discovery_angle])}</span>` : "";
      const novDetail = nv && nv.status && nv.status !== "sin_evaluar" ? `
        <details class="nov-detail"><summary class="tag">🎯 novedad: ${esc(nv.status)} — ¿vale la pena?</summary>
          <div class="hyp-field"><b>Ya se sabe:</b><p>${esc(nv.known || "")}</p></div>
          <div class="hyp-field"><b>El hueco (lo que NO se ha hecho):</b><p>${esc(nv.gap || "")}</p></div>
          <div class="hyp-field"><b>🚀 Camino a un descubrimiento:</b><p>${esc(nv.discovery_path || "")}</p></div>
        </details>` : "";
      return `<div class="card hyp-card${nv && nv.status === "asentada" ? " settled" : ""}">
        <div class="hyp-head">
          <b>${esc(i.tag)}: ${esc(i.title)}</b>
          ${verChip(`H v${i.version || 1}`, true, "versión actual de la hipótesis")}
          ${novBadge} ${daBadge}
          ${klabel ? " " + pill(klabel, kcolor) : ""} ${anom}
          ${pill(i.meta || "", approved ? "ok" : "warn")}
          ${i.flag ? " " + pill(i.flag, "bad") : ""}
          ${reasoning ? `<button class="hyp-toggle" data-htoggle="${ix}">ver razonamiento ▾</button>` : ""}
        </div>${novDetail}${anomProv}${actions}
        <div class="hyp-links">
          <button class="act ghost" data-htrace="${esc(i.id)}">🧭 Detalle</button>
          <a href="#" data-golit>→ ir a Literatura</a> ·
          <a href="#" data-goexp>→ ir a Experimentos</a>
          <button class="act ghost danger" data-hdel="${esc(i.id)}" data-tag="${esc(i.tag)}">🗑 Borrar</button>
        </div>
        ${reasoning}${i.critique ? criticFoot(i.critique, i.id, i.version || 1) : criticEmpty(i.id, "hipotesis")}</div>`;
    }).join("");
  } else {
    items = (f.items || []).map((i) => {
      const link = i.url ? `<a href="${esc(i.url)}" target="_blank" rel="noopener">${esc(i.title)}</a>`
                         : esc(i.title);
      return `<div class="card">${link}
        ${i.flag ? " " + pill(i.flag, "bad") : ""}
        <div class="tag">${esc(i.meta || "")}</div></div>`;
    }).join("");
  }

  // KPI mini-strip contextual a la fase
  const k = ph.kpis || {};
  const kpiByPhase = {
    hipotesis: [["hipótesis", f.count], ["aprobadas", k.approved]],
    literatura: [["papers reales", f.count], ["con retracción", 0]],
    teorias: [["nodos", f.count]],
    experimentos: [["experimentos", f.count], ["con datos reales", k.real_experiments]],
    resultados: [["resultados", f.count], ["negativos", k.negatives]],
    conclusiones: [["dossiers", f.count]],
  }[phaseKey] || [["items", f.count]];
  const kstrip = kpiByPhase.map(([lb, v]) =>
    `<div class="kpi"><div class="kpi-big">${v ?? 0}</div><div><b>${esc(lb)}</b></div></div>`).join("");

  view.innerHTML =
    `<button class="act ghost" id="ph-back">← ${esc(ph.title)}</button>
     <p class="eyebrow">Dashboard de fase</p>
     <div class="pulse-head"><h1>${esc(f.icon)} ${esc(f.title)}</h1>
       <span class="tag">${pill(f.state === "done" ? "con trabajo" : "pendiente", f.state === "done" ? "ok" : "warn")}
         · ${f.count} items · ${esc(f.note)}</span></div>

     <section class="panel method-panel">
       <p class="eyebrow">ℹ️ Cómo entender esta fase</p>
       <div class="method-grid">
         <div><b>¿Qué es?</b><p>${esc(m.que_es || "")}</p></div>
         <div><b>¿De dónde sale?</b><p>${esc(m.de_donde || "")}</p></div>
         <div><b>¿Qué significa su calificación?</b><p>${esc(m.calificacion || "")}</p></div>
       </div>
     </section>

     <div class="kpi-strip">${kstrip}</div>
     ${phaseKey === "hipotesis" ? `
       <div class="hyp-gen">
         <input id="hyp-focus" placeholder="(opcional) enfoca: p.ej. movimiento del Sol, sesgos de selección…">
         <button class="act" id="hyp-gen-btn">🧠 Generar hipótesis (crítica y creativa)</button>
         <button class="act ghost" id="hyp-gen-one">＋ Generar nueva hipótesis</button>
         <button class="act ghost" id="anom-harvest">🔥 Anomalías → hipótesis</button>
         <button class="act ghost" id="nov-all">🎯 Evaluar novedad de todas</button>
         <span id="hyp-gen-out" class="tag" aria-live="polite"></span>
       </div>
       <p class="tag">El copiloto CUESTIONA (no repite): propone hipótesis ya probadas, teorizadas, nuevas y preguntas abiertas, cada una con su pregunta detonante, argumento, duda y cómo probarla.</p>` : ""}
     <h3 style="margin:.4rem 0 .6rem">Detalle (${(f.items || []).length})</h3>
     ${items || "<p class='muted'>Sin items en esta fase todavía.</p>"}
     <p class="tag" style="margin-top:.6rem">${esc(ph.honesty)}</p>`;
  view.querySelector("#ph-back").addEventListener("click", () => cb.openProject(pid));

  // hypothesis interactions
  view.querySelectorAll("[data-htoggle]").forEach((b) =>
    b.addEventListener("click", () => {
      const r = view.querySelector(`[data-reason="${b.dataset.htoggle}"]`);
      const open = !r.hidden;
      r.hidden = open;
      b.textContent = open ? "ver razonamiento ▾" : "ocultar razonamiento ▴";
    }));
  view.querySelectorAll("[data-hask]").forEach((b) =>
    b.addEventListener("click", async () => {
      const ix = b.dataset.hask;
      const input = view.querySelector(`[data-hq="${ix}"]`);
      const out = view.querySelector(`[data-hans="${ix}"]`);
      const q = input.value.trim();
      if (!q) return;
      out.innerHTML = "<span class='loading'>Pensando…</span>";
      b.disabled = true;
      const { ok: aok, body: ans } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/copilot`,
        { message: q, location: { scope: "phase", phase: "hipotesis" } });
      b.disabled = false;
      out.innerHTML = aok && ans.reply
        ? `<div class="card">${esc(ans.reply)}<div class="tag">${esc(ans.disclaimer || "")}</div></div>`
        : `<span class="err">error</span>`;
      input.value = "";
    }));
  const genHyp = async (n, btn) => {
    const focus = view.querySelector("#hyp-focus").value.trim();
    const out = view.querySelector("#hyp-gen-out");
    btn.disabled = true;
    out.textContent = "Generando (Codex cuestiona… hasta ~3 min)…";
    const { ok: gok, body: g } = await post(
      `/portal/api/projects/${encodeURIComponent(pid)}/hypotheses/generate`,
      { n, use_ai: true, focus });
    btn.disabled = false;
    if (!gok || !g.ok) { out.textContent = "Error: " + ((g && (g.detail || g.error)) || "gen"); return; }
    out.textContent = `${g.created.length} hipótesis nuevas (${g.provider}).`;
    cb.openPhase(pid, "hipotesis");
  };
  const genBtn = view.querySelector("#hyp-gen-btn");
  if (genBtn) genBtn.addEventListener("click", () => genHyp(6, genBtn));
  const genOne = view.querySelector("#hyp-gen-one");
  if (genOne) genOne.addEventListener("click", () => genHyp(1, genOne));
  // detalle / borrar / hipervínculos / Aristóteles (hipotesis phase)
  wireAristoteles(view, pid, cb, () => cb.openPhase(pid, "hipotesis"));
  view.querySelectorAll("[data-htrace]").forEach((b) =>
    b.addEventListener("click", () => renderTrace(view, pid, b.dataset.htrace, cb)));
  view.querySelectorAll("[data-novelty]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      b.textContent = "🎯 evaluando novedad (Codex)…";
      const { ok, body } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/hypothesis/${b.dataset.novelty}/novelty`, {});
      if (ok && body.ok) cb.openPhase(pid, "hipotesis");
      else { b.disabled = false; b.textContent = "🎯 evaluar novedad"; }
    }));
  view.querySelectorAll("[data-golit]").forEach((a) =>
    a.addEventListener("click", (ev) => { ev.preventDefault(); cb.openPhase(pid, "literatura"); }));
  view.querySelectorAll("[data-goexp]").forEach((a) =>
    a.addEventListener("click", (ev) => { ev.preventDefault(); cb.openPhase(pid, "experimentos"); }));
  view.querySelectorAll("[data-hdel]").forEach((b) =>
    b.addEventListener("click", async () => {
      if (!confirm(`¿BORRAR ${b.dataset.tag} y todo lo que depende de ella (literatura, experimentos no guardados, críticas)? El vault conservará la memoria de lo que se hizo.`)) return;
      const { ok, body } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/hypothesis/${b.dataset.hdel}/delete`, {});
      if (ok && body.ok) {
        alert(`Borrada. Archivo en vault: ${body.vault_note || "—"}. Experimentos guardados que sobreviven: ${(body.kept_orphans || []).length}`);
        cb.openPhase(pid, "hipotesis");
      } else alert("Error: " + ((body && body.error) || ""));
    }));

  const novAll = view.querySelector("#nov-all");
  if (novAll) novAll.addEventListener("click", async () => {
    const out = view.querySelector("#hyp-gen-out");
    novAll.disabled = true;
    out.textContent = "🎯 El sistema evalúa la novedad de cada hipótesis (Codex)…";
    const { ok, body } = await post(
      `/portal/api/projects/${encodeURIComponent(pid)}/novelty/assess-all`, {});
    novAll.disabled = false;
    if (ok && body.ok) { out.textContent = `🎯 ${body.assessed.length} evaluadas — verde=frontera, rojo=ya se sabe`; cb.openPhase(pid, "hipotesis"); }
    else out.textContent = "Error al evaluar novedad.";
  });
  const anomBtn = view.querySelector("#anom-harvest");
  if (anomBtn) anomBtn.addEventListener("click", async () => {
    const out = view.querySelector("#hyp-gen-out");
    anomBtn.disabled = true;
    out.textContent = "🔥 Buscando discrepancias medidas en los experimentos…";
    const { ok, body } = await post(
      `/portal/api/projects/${encodeURIComponent(pid)}/anomalies/harvest`, {});
    anomBtn.disabled = false;
    if (ok && body.ok) {
      out.textContent = body.created.length
        ? `🔥 ${body.created.length} hipótesis nacidas de anomalías — apruébalas si valen.`
        : (body.note || "sin anomalías nuevas");
      if (body.created.length) cb.openPhase(pid, "hipotesis");
    } else out.textContent = "Error en la cosecha.";
  });

  // approve / reject / unapprove
  view.querySelectorAll("[data-happrove]").forEach((b) =>
    b.addEventListener("click", async () => {
      const reason = prompt(`Razón para aprobar ${b.dataset.tag} (los siguientes pasos correrán sobre esta hipótesis):`);
      if (!reason) return;
      const { ok, body } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/hypothesis/${b.dataset.happrove}/status`,
        { status: "APPROVED", reason });
      if (ok && body.ok) cb.openPhase(pid, "hipotesis");
      else alert("Error: " + ((body && (body.detail || body.error)) || ""));
    }));
  view.querySelectorAll("[data-hstatus]").forEach((b) =>
    b.addEventListener("click", async () => {
      const to = b.dataset.to;
      if (to === "REJECTED" && !confirm("¿Rechazar esta hipótesis?")) return;
      const { ok, body } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/hypothesis/${b.dataset.hstatus}/status`,
        { status: to, reason: to === "PROPOSED" ? "desaprobada" : "rechazada por el humano" });
      if (ok) cb.openPhase(pid, "hipotesis");
    }));
}

/* ---------- hypothesis-centric literature + experiments dashboards -------- */
/* Versioned label chips: green = al día con la versión actual, ámbar = desactualizado. */
function verChip(text, isCurrent, title) {
  return `<span class="pill vtag ${isCurrent ? "ok" : "warn"}" title="${esc(title || (isCurrent ? "al día con la versión actual" : "hecho sobre una versión anterior — actualiza"))}">${esc(text)}</span>`;
}

/* Footer with the resident critic's ("El Revisor") latest take on a card. */
function criticFoot(c, targetId, curVer) {
  if (!c) return "";
  const COLOR = { solido: "ok", prometedor: "warn", debil: "warn",
                  defectuoso: "bad", sin_revision: "warn" };
  const list = (arr, label) => (arr && arr.length)
    ? `<div class="hyp-field"><b>${label}</b><ul>${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>` : "";
  // objections carry their resolution status (C3 closed loop)
  const sts = c.objections_status || [];
  const objList = (c.objections || []).length ? `
    <div class="hyp-field"><b>⚠️ Objeciones</b><ul>${(c.objections || []).map((x, i) =>
      `<li>${sts[i] === "resolved" ? "✅" : "⏳"} ${esc(x)}</li>`).join("")}</ul></div>` : "";
  const convertBtn = targetId && (c.suggestions || []).length
    ? `<button class="act ghost" data-c2e="${esc(targetId)}">🧪 Convertir sugerencias en experimentos</button>` : "";
  const details = (c.objections || []).length || (c.alternatives || []).length ||
                  (c.suggestions || []).length || c.hard_question ? `
    <details><summary class="tag">ver crítica completa</summary>
      ${objList}
      ${list(c.alternatives, "🔀 Explicaciones alternativas no descartadas")}
      ${list(c.suggestions, "🛠 Sugerencias ejecutables")}
      ${c.hard_question ? `<div class="hyp-field"><b>🎯 La pregunta incómoda</b><p>${esc(c.hard_question)}</p></div>` : ""}
      ${convertBtn}
    </details>` : "";
  const resolved = sts.filter((s) => s === "resolved").length;
  const objChip = (c.objections || []).length
    ? `<span class="tag">${resolved}/${c.objections.length} objeciones resueltas</span>` : "";
  const tools = targetId ? `<div class="critic-tools">
      <button class="act ghost" data-consult="${esc(targetId)}" data-ctask="${esc(c.task || "hipotesis")}">🧐 Consultar a Aristóteles</button>
      ${c.id ? `<button class="act ghost" data-consider="${esc(c.id)}">🔄 Considerar crítica</button>` : ""}
      <button class="act ghost" data-crithist="${esc(targetId)}">🗂 Historial</button>
    </div><div class="crit-hist" data-histout="${esc(targetId)}"></div>` : "";
  return `<div class="critic-note">
    <div class="critic-head">🧐 <b>Aristóteles</b>
      ${c.label ? verChip(c.label, !curVer || (c.hyp_version || 1) >= curVer) : ""}
      ${pill(c.verdict || "", COLOR[c.verdict] || "warn")}
      <span class="tag">${esc(c.task || "")}</span> ${objChip}</div>
    <p>${esc(c.summary || "")}</p>${details}${tools}
  </div>`;
}

/* Aristóteles card when there is NO critique yet — still consultable. */
function criticEmpty(targetId, task) {
  return `<div class="critic-note"><div class="critic-head">🧐 <b>Aristóteles</b>
      <span class="tag">aún sin crítica</span></div>
    <div class="critic-tools">
      <button class="act ghost" data-consult="${esc(targetId)}" data-ctask="${esc(task)}">🧐 Consultar a Aristóteles</button>
    </div><div class="crit-hist" data-histout="${esc(targetId)}"></div></div>`;
}

function wireAristoteles(view, pid, cb, refresh) {
  view.querySelectorAll("[data-consult]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      b.textContent = "🧐 Aristóteles está pensando (1-3 min)…";
      const { ok, body } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/critic/consult`,
        { target_id: b.dataset.consult, task: b.dataset.ctask || "hipotesis" });
      if (ok && body.ok) refresh();
      else { b.disabled = false; b.textContent = "Error al consultar"; }
    }));
  view.querySelectorAll("[data-consider]").forEach((b) =>
    b.addEventListener("click", async () => {
      if (!confirm("Considerar esta crítica replantea TODO el flujo desde un nivel anterior (nueva versión de la hipótesis, literatura STALE, experimentos supeditados). ¿Continuar?")) return;
      b.disabled = true;
      const { ok, body } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/critique/${b.dataset.consider}/consider`, {});
      if (ok && body.ok) { alert(body.note || "Flujo replanteado."); refresh(); }
      else { b.disabled = false; alert("Error: " + ((body && body.error) || "")); }
    }));
  view.querySelectorAll("[data-crithist]").forEach((b) =>
    b.addEventListener("click", async () => {
      const out = view.querySelector(`[data-histout="${b.dataset.crithist}"]`);
      if (!out) return;
      out.innerHTML = "<span class='loading'>cargando historial…</span>";
      const { ok, body } = await get(
        `/portal/api/projects/${encodeURIComponent(pid)}/critic/history/${b.dataset.crithist}`);
      out.innerHTML = ok && body.history.length
        ? body.history.map((c) => `<div class="cite"><b>${esc(c.verdict || "")}</b>
            <span class="tag">${esc((c.created_at || "").slice(0, 16))} · ${esc(c.task || "")}</span>
            <p class="cite-abs">${esc((c.summary || "").slice(0, 220))}</p></div>`).join("")
        : "<p class='muted tag'>sin críticas previas</p>";
    }));
}

function wireCriticConvert(view, pid, cb, phaseKey) {
  view.querySelectorAll("[data-c2e]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      b.textContent = "Convirtiendo…";
      const { ok, body } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/hypothesis/${b.dataset.c2e}/critic/to-experiments`, {});
      if (ok && body.ok) cb.openPhase(pid, "experimentos");
      else { b.disabled = false; b.textContent = "Error: " + esc((body && body.error) || "conversión"); }
    }));
}

/* Small SVG bar chart for an experiment's numeric metrics. */
function metricsChart(metrics) {
  const entries = Object.entries(metrics || {})
    .filter(([, v]) => typeof v === "number" && isFinite(v));
  if (!entries.length) return "";
  const max = Math.max(...entries.map(([, v]) => Math.abs(v))) || 1;
  const rowH = 30, w = 620, labelW = 200, barW = w - labelW - 90;
  const rows = entries.map(([k, v], i) => {
    const len = Math.max(2, Math.round(barW * Math.abs(v) / max));
    const y = i * rowH + 6;
    const val = Math.abs(v) < 1e-3 || Math.abs(v) > 1e4 ? v.toExponential(2) : Number(v.toPrecision(4));
    return `<text x="0" y="${y + 15}" class="mc-lbl">${esc(k.slice(0, 28))}</text>
      <rect x="${labelW}" y="${y + 3}" width="${len}" height="18" rx="4" class="mc-bar ${v < 0 ? "neg" : ""}"></rect>
      <text x="${labelW + len + 6}" y="${y + 16}" class="mc-val">${esc(String(val))}</text>`;
  }).join("");
  return `<svg viewBox="0 0 ${w} ${entries.length * rowH + 12}" class="metrics-chart" role="img" aria-label="métricas">${rows}</svg>`;
}

/* Full experiment dashboard: method, data, metrics, nulls, code, figures. */
async function renderExperiment(view, pid, expId, cb, backPhase) {
  view.innerHTML = "<p class='loading'>Cargando análisis del experimento…</p>";
  const { ok, body } = await get(
    `/portal/api/projects/${encodeURIComponent(pid)}/experiment/${encodeURIComponent(expId)}/detail`);
  if (!ok || !body.ok) { view.innerHTML = "<p class='err'>No se pudo cargar el experimento.</p>"; return; }
  const e = body.experiment;
  const V_COLOR = { supports: "ok", refutes: "bad", inconclusive: "warn" };
  const mIcon = { download_data: "⬇️ datos descargados", math_analysis: "∑ análisis matemático", theoretical: "📐 teórico", simulation: "🎲 simulación" };
  const nt = e.null_test || {};
  const fac = e.factory || {};
  const cc = fac.cross_check;
  const provRows = (e.provenance || []).map((p2) => `
    <tr><td><a href="${esc(p2.url)}" target="_blank" rel="noopener">${esc(p2.filename)}</a></td>
      <td>${Math.round((p2.bytes || 0) / 1024)} KB</td>
      <td><code>${esc((p2.sha256 || "").slice(0, 16))}…</code></td>
      <td>${p2.pruned ? "podado (re-descargable)" : (p2.cached ? "caché" : "descargado")}</td></tr>`).join("");
  const figs = (e.figures || []).map((f) =>
    `<figure class="exp-fig"><img src="/portal/api/projects/${encodeURIComponent(pid)}/experiment/${encodeURIComponent(expId)}/figure/${encodeURIComponent(f)}" alt="${esc(f)}" loading="lazy"><figcaption>${esc(f)}</figcaption></figure>`).join("");
  const kpi = (big, label, cls) => `<div class="kpi exp-kpi"><div class="exp-kpi-big ${cls || ""}">${esc(big)}</div><div class="exp-kpi-lbl">${esc(label)}</div></div>`;

  view.innerHTML = `
    <button class="act ghost" id="exp-back">← volver a Experimentos</button>
    <p class="eyebrow">Análisis del experimento · ${esc(e.hyp_tag)} v${e.hyp_version}</p>
    <div class="pulse-head"><h1>🔬 ${esc(e.title)}</h1>
      ${e.verdict ? pill(e.verdict, V_COLOR[e.verdict] || "warn") : pill(e.status, "warn")}</div>
    <p class="muted">Hipótesis: ${esc(e.hyp_title)}</p>

    <div class="kpi-strip">
      ${kpi(e.verdict || e.status, "veredicto", V_COLOR[e.verdict] || "")}
      ${kpi(mIcon[e.method_type] || e.method_type || "—", "método")}
      ${kpi((e.provenance || []).length, "datasets reales")}
      ${kpi(nt.passed === true ? "✓" : nt.passed === false ? "✗" : "—", "control nulo")}
      ${fac.attempts ? kpi(fac.attempts, "intentos de código") : ""}
      ${fac.duration_sec ? kpi(fac.duration_sec + "s", "cómputo") : ""}
    </div>

    ${e.verdict_reason ? `<div class="card"><b>⚖️ Conclusión del análisis</b><p>${esc(e.verdict_reason)}</p>
      <p class="tag">Código escrito por IA y ejecutado en sandbox — revisa el código antes de confiar en el resultado. Nada es un descubrimiento.</p></div>` : ""}

    <div class="card"><b>🧪 Qué se hizo</b>
      <div class="tag"><b>Qué mide:</b> ${esc(e.what)}</div>
      <div class="tag"><b>Cómo (método):</b> ${esc(e.how)}</div>
      <div class="tag"><b>Datos:</b> ${esc(e.data_source)}</div>
      <div class="tag"><b>Controles:</b> ${esc(e.controls)}</div>
      <div class="tag"><b>Discriminador:</b> ${esc(e.discriminator)}</div>
    </div>

    ${Object.keys(e.metrics || {}).length ? `<div class="card"><b>📊 Métricas calculadas</b>${metricsChart(e.metrics)}</div>` : ""}

    ${nt.description ? `<div class="card"><b>🎲 Control nulo (¿es señal o azar?)</b>
      <p>${esc(nt.description)}</p>
      <div class="tag">estadístico: ${esc(String(nt.statistic ?? "—"))} · umbral: ${esc(String(nt.threshold ?? "—"))} · <b>${nt.passed === true ? "SUPERADO" : nt.passed === false ? "NO superado" : "sin nulo"}</b></div></div>` : ""}

    ${cc ? `<div class="card"><b>🔁 Verificación cruzada (2ª implementación independiente)</b>
      <p class="tag">${cc.agreed ? "✅ coincidió" : "⚠️ NO coincidió"} — ${esc(cc.detail || cc.reason || "")}</p></div>` : ""}

    ${(e.anomalies || []).length ? `<div class="card"><b>🔥 Anomalías detectadas</b><ul>${e.anomalies.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>` : ""}

    ${figs ? `<div class="card"><b>📈 Figuras</b><div class="exp-figs">${figs}</div></div>` : ""}

    ${provRows ? `<div class="card"><b>📦 Procedencia de los datos (verificable)</b>
      <table class="prov-table"><thead><tr><th>archivo</th><th>tamaño</th><th>sha256</th><th>estado</th></tr></thead><tbody>${provRows}</tbody></table></div>` : ""}

    ${e.plan ? `<div class="card"><b>📋 Plan de ejecución (pendiente de datos reales)</b><div class="lms-body">${esc(e.plan)}</div></div>` : ""}

    ${e.code ? `<div class="card"><details><summary><b>📄 Código del análisis (generado por IA — revísalo)</b></summary><pre class="code-block">${esc(e.code)}</pre></details>
      ${e.code_v2 ? `<details><summary><b>📄 Segunda implementación (verificación cruzada)</b></summary><pre class="code-block">${esc(e.code_v2)}</pre></details>` : ""}</div>` : ""}

    ${e.stdout ? `<div class="card"><details><summary><b>🖥 Salida de la ejecución (stdout)</b></summary><pre class="code-block">${esc(e.stdout)}</pre></details></div>` : ""}
  `;
  view.querySelector("#exp-back").addEventListener("click", () => cb.openPhase(pid, backPhase || "experimentos"));
}

/* Detalle: the full story of one hypothesis as a top-down connected flow. */
async function renderTrace(view, pid, hypId, cb) {
  view.innerHTML = "<p class='loading'>Reconstruyendo la historia…</p>";
  const { ok, body: t } = await get(
    `/portal/api/projects/${encodeURIComponent(pid)}/hypothesis/${encodeURIComponent(hypId)}/trace`);
  if (!ok || !t.ok) { view.innerHTML = "<p class='err'>No se pudo cargar el detalle.</p>"; return; }
  const nodes = (t.nodes || []).map((n) => `
    <div class="trace-node t-${esc(n.type)}">
      <div class="trace-dot">${esc(n.icon)}</div>
      <div class="trace-card" ${n.link ? `data-tlink="${esc(n.link)}" role="button" tabindex="0"` : ""}
        ${n.type === "experiment" && n.ref ? `data-texp="${esc(n.ref)}"` : ""}>
        <div class="trace-head"><b>${esc(n.title)}</b>
          <span class="tag">${esc((n.ts || "").slice(0, 16).replace("T", " "))}</span></div>
        <p class="tag">${esc(n.summary || "")}</p>
        ${n.type === "experiment" && n.ref ? `<span class="trace-go">ver análisis →</span>`
          : n.link ? `<span class="trace-go">abrir ficha →</span>` : ""}
      </div>
    </div>`).join("");
  view.innerHTML = `
    <button class="act ghost" id="trace-back">← volver</button>
    <p class="eyebrow">Detalle · mapa del flujo</p>
    <div class="pulse-head"><h1>🧭 ${esc(t.tag)} (v${t.version}): historia completa</h1></div>
    <p class="muted">${esc(t.title)}</p>
    <div class="trace-flow">${nodes || "<p class='muted'>sin eventos aún</p>"}</div>`;
  view.querySelector("#trace-back").addEventListener("click", () => cb.openPhase(pid, "hipotesis"));
  view.querySelectorAll("[data-texp]").forEach((c) =>
    c.addEventListener("click", () => renderExperiment(view, pid, c.dataset.texp, cb, "hipotesis")));
  view.querySelectorAll("[data-tlink]:not([data-texp])").forEach((c) => {
    const go = () => cb.openPhase(pid, c.dataset.tlink);
    c.addEventListener("click", go);
    c.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
  });
}

/* Progress bar for a hypothesis' running/last mission (0-100%). */
function missionBar(m, hypId) {
  if (!m) return "";
  const running = m.status === "RUNNING" || m.status === "PENDING";
  const pct = m.status === "DONE" ? 100 : (m.progress_pct || 0);
  const cls = m.status === "FAILED" ? "bad" : (m.status === "DONE" ? "ok" : "run");
  const label = m.status === "DONE" ? "✅ misión completa"
    : m.status === "FAILED" ? "❌ misión falló"
    : (m.current || "misión en curso…");
  return `<div class="mbar-wrap" data-mbar="${esc(hypId)}" data-mid="${esc(m.id)}" data-mrun="${running ? 1 : 0}">
      <div class="mbar"><div class="mbar-fill ${cls}" style="width:${pct}%"></div>
        <span class="mbar-pct">${pct}%</span></div>
      <div class="mbar-label">🚀 ${esc(label)}</div>
    </div>`;
}

/* Live-poll each running mission bar on this view and refresh when it ends. */
function wireMissionBars(view, pid, cb) {
  const bars = [...view.querySelectorAll('[data-mbar][data-mrun="1"]')];
  if (!bars.length) return;
  const t = setInterval(async () => {
    if (!document.body.contains(view)) { clearInterval(t); return; }
    const { ok, body } = await get(`/portal/api/projects/${encodeURIComponent(pid)}/missions`);
    if (!ok) return;
    const byHyp = {};
    (body.missions || []).forEach((mn) => { if (!(mn.hyp_id in byHyp)) byHyp[mn.hyp_id] = mn; });
    let anyRunning = false;
    bars.forEach((wrap) => {
      const mn = byHyp[wrap.dataset.mbar];
      if (!mn) return;
      const cur = (mn.steps || []).find((s2) => s2.status === "RUNNING");
      const pct = mn.status === "DONE" ? 100 : (mn.progress_pct || 0);
      const fill = wrap.querySelector(".mbar-fill");
      fill.style.width = pct + "%";
      wrap.querySelector(".mbar-pct").textContent = pct + "%";
      wrap.querySelector(".mbar-label").textContent = "🚀 " + (mn.status === "DONE" ? "✅ misión completa"
        : (cur && cur.sub) || "misión en curso…");
      if (mn.status === "RUNNING" || mn.status === "PENDING") anyRunning = true;
      else { fill.classList.remove("run"); fill.classList.add(mn.status === "FAILED" ? "bad" : "ok"); }
    });
    if (!anyRunning) { clearInterval(t); cb.openPhase(pid, "literatura"); }
  }, 3500);
}

/* Poll a parallel run (one subagent per item) and paint live progress. */
function pollRun(runId, out, onDone) {
  const icon = { PENDING: "⏳", RUNNING: "🤖", DONE: "✅", ERROR: "❌" };
  const timer = setInterval(async () => {
    const { ok, body: r } = await get(`/portal/api/runs/${encodeURIComponent(runId)}`);
    if (!ok || !r) {
      clearInterval(timer);
      out.textContent = "Se perdió el run (¿portal reiniciado?).";
      return;
    }
    out.innerHTML = `${r.done}/${r.total} subagentes — ` + (r.items || [])
      .map((i) => `${icon[i.status] || "⏳"} ${esc((i.label || "").split(":")[0])}` +
                  (i.status === "ERROR" ? ` <span class="err">(${esc(i.summary)})</span>` : ""))
      .join(" · ");
    if (r.status === "DONE") { clearInterval(timer); onDone(r); }
  }, 2500);
}

async function renderHypFlow(view, pid, phaseKey, ph, cb) {
  const { ok, body: fl } = await get(`/portal/api/projects/${encodeURIComponent(pid)}/hyp-flow`);
  const approved = (ok && fl.approved) || [];
  const back = `<button class="act ghost" id="ph-back">← ${esc(ph.title)}</button>`;
  if (!approved.length) {
    view.innerHTML = back +
      `<p class="eyebrow">Dashboard de fase</p>
       <div class="pulse-head"><h1>${esc(phaseKey === "literatura" ? "📚 Investigación de literatura" : "⚗️ Experimentos")}</h1></div>
       <p class="muted">Aún no hay hipótesis <b>aprobadas</b>. Ve a la fase <b>Hipótesis</b>,
       aprueba una (con su razón) y aquí aparecerá su propia investigación.</p>`;
    view.querySelector("#ph-back").addEventListener("click", () => cb.openProject(pid));
    return;
  }

  if (phaseKey === "literatura") {
    const cards = approved.map((h) => {
      const done = h.lit_status === "DONE";
      const c = h.confrontation || {};
      const relTag = (x) => x.relevance ? `<span class="tag">rel ${Math.round(x.relevance)}</span>` : "";
      const cites = (c.citations || []).map((x) => {
        const href = x.url || (x.doi ? `https://doi.org/${esc(x.doi)}` : "#");
        const retr = x.integrity === "retracted" ? ` <span class="pill bad">RETRACTADO</span>` : "";
        const ft = x.has_fulltext ? ` <span class="pill ok">📖 texto completo leído</span>` : "";
        return `<li class="cite">
          <a href="${esc(href)}" target="_blank" rel="noopener">${esc((x.title || x.doi).slice(0, 90))}</a>
          <span class="src">${esc(x.source || "")}</span> ${relTag(x)}${retr}${ft}
          ${x.abstract ? `<p class="cite-abs">${esc(x.abstract)}…</p>` : ""}</li>`;
      }).join("");
      const qUsed = c.query_used ? `<p class="tag">🔤 Búsqueda ejecutada (inglés): <code>${esc(c.query_used)}</code></p>` : "";
      const hv = h.version || 1;
      const iv = (c.hyp_version || (done ? 1 : 0));
      const ver = verChip(`H v${hv}`, true, "versión actual de la hipótesis");
      const invChip = iv ? verChip(`Inv v${iv}`, iv >= hv,
        iv >= hv ? "investigación de la versión actual" : `investigaste la v${iv} pero la hipótesis ya va en v${hv} — re-investiga`) : "";
      const stale = h.lit_status === "STALE"
        ? `<p class="tag warn-txt">⚠️ Tomaste una versión mejorada — vuelve a <b>Investigar</b> para confrontar la v${h.version} con nueva literatura.</p>` : "";
      // improved-hypothesis block gets a "Tomar hipótesis" button that versions the original
      const improved = (c.improved_hypothesis || "").trim();
      const canAdopt = improved && improved !== (h.title || "").trim();
      const improvedBlock = improved ? `
          <div class="hyp-field improved">
            <b>✨ Hipótesis mejorada por la evidencia</b><p>${esc(improved)}</p>
            ${canAdopt ? `<button class="act small" data-adopt="${esc(h.id)}">⤴ Tomar hipótesis → v${(h.version || 1) + 1}</button>` : `<span class="tag">ya es la versión actual</span>`}
          </div>` : "";
      // computer-doable experiment ideas surfaced while reading the literature
      const ideas = (c.experiment_ideas || []);
      const mIcon = { download_data: "⬇️ bajar datos", math_analysis: "∑ análisis", theoretical: "📐 teórico", simulation: "🎲 simulación" };
      const ideasBlock = ideas.length ? `
          <div class="hyp-field"><b>🧪 Cómo comprobarlo (ejecutable en la compu)</b>
            <ul class="ideas">${ideas.map((i) => `<li>
              <b>${esc(i.title || "")}</b>
              <span class="src">${esc(mIcon[i.method_type] || i.method_type || "")}</span>
              ${i.feasible_local ? `<span class="pill ok">local</span>` : `<span class="pill warn">requiere infra</span>`}
              <p class="cite-abs">${esc(i.approach || "")}</p>
              <p class="tag">📦 Datos: ${esc(i.data_source || "")}</p></li>`).join("")}</ul>
            <p class="tag">Estas ideas alimentan la fase de <b>Experimentos</b>.</p>
          </div>` : "";
      const confrontHtml = done && c.provider === "codex" ? `
        <div class="confront">
          ${qUsed}
          <div class="hyp-field"><b>⚖️ Postura de la evidencia</b> ${pill(c.stance || "", c.stance === "supports" ? "ok" : c.stance === "challenges" ? "bad" : "warn")}</div>
          <div class="hyp-field"><b>➕ A favor</b><p>${esc(c.argument_for || "")}</p></div>
          <div class="hyp-field"><b>➖ En contra</b><p>${esc(c.argument_against || "")}</p></div>
          ${improvedBlock}
          ${ideasBlock}
          <div class="hyp-field"><b>📎 Literatura leída (${(c.citations || []).length})</b><ul class="cites">${cites}</ul></div>
        </div>` : (done ? `<div class="confront">${qUsed}<p class="tag">Se indexaron ${h.lit_count} papers (confrontación IA no disponible).</p><ul class="cites">${cites}</ul></div>` : "");
      const newEv = (h.new_evidence_count || 0) > 0
        ? `<span class="pill warn">📡 ${h.new_evidence_count} papers nuevos</span>` : "";
      return `<div class="card hyp-card">
        <div class="hyp-head"><b>${esc(h.tag)}: ${esc(h.title)}</b> ${ver} ${invChip} ${newEv}
          ${pill(done ? `${h.lit_count} papers ✓` : (h.lit_status === "STALE" ? "re-investigar" : "sin investigar"), done ? "ok" : "warn")}</div>
        <p class="tag">Literatura real multi-fuente (OpenAlex + arXiv + Crossref) sobre: ${esc(h.trigger_question || h.title)}</p>
        ${stale}
        <button class="act" data-invest="${esc(h.id)}">${done ? "↻ Re-investigar" : "🔎 Investigar"}</button>
        <button class="act mission-btn" data-mission="${esc(h.id)}">🚀 Lanzar Misión</button>
        ${missionBar(h.mission, h.id)}
        ${done ? `<button class="act ghost" data-deepen="${esc(h.id)}">📖 Leer a fondo (descargar PDFs + leer texto completo + indexar)</button>` : ""}
        <button class="act ghost" data-htrace="${esc(h.id)}">🧭 Detalle</button>
        <div class="confront-out" data-invout="${esc(h.id)}">${confrontHtml}</div>
        ${h.critique ? criticFoot(h.critique, h.id, h.version || 1) : criticEmpty(h.id, "literatura")}
      </div>`;
    }).join("");
    view.innerHTML = back +
      `<p class="eyebrow">Dashboard de fase · por hipótesis</p>
       <div class="pulse-head"><h1>📚 Investigación de literatura</h1>
         <span class="tag">${approved.length} hipótesis aprobadas</span>
         <span class="tag" id="rigor-chip"></span></div>
       <div class="run-all"><button class="act" id="lit-run-all">▶▶ Correr TODAS las investigaciones</button>
         <button class="act" id="msn-all">🚀 Misiones para TODAS</button>
         <button class="act ghost" id="watch-scan">📡 Buscar novedades</button>
         <button class="act ghost" id="obs-sync">🧠 Sync Obsidian</button>
         <span id="lit-run-out" class="tag" aria-live="polite"></span></div>
       <div class="vault-search">
         <input id="vault-q" placeholder="🔍 Busca por SIGNIFICADO en toda la literatura del proyecto (embeddings)…" aria-label="Buscar en el vault">
         <button class="act ghost" id="vault-go">Buscar</button>
         <div id="vault-out" aria-live="polite"></div>
       </div>
       <div id="missions-strip" aria-live="polite"></div>
       ${cards}
       <p class="tag">Cada tarjeta confronta su hipótesis con citas reales y propone una versión mejorada. La síntesis IA es ayuda, no evidencia.</p>`;
    view.querySelectorAll("[data-invest]").forEach((b) =>
      b.addEventListener("click", async () => {
        const out = view.querySelector(`[data-invout="${b.dataset.invest}"]`);
        out.innerHTML = `<div class="mbar-wrap"><div class="mbar"><div class="mbar-fill run" style="width:20%"></div><span class="mbar-pct"></span></div><div class="mbar-label">🔎 buscando literatura real (multi-fuente) + confrontando con Codex…</div></div>`;
        b.disabled = true;
        const { ok: iok, body } = await post(
          `/portal/api/projects/${encodeURIComponent(pid)}/hypothesis/${b.dataset.invest}/investigate`, {});
        if (iok && body.run) {
          const fill = out.querySelector(".mbar-fill");
          let w = 20;
          const grow = setInterval(() => { w = Math.min(90, w + 6); fill.style.width = w + "%"; }, 2500);
          pollRun(body.run.id, out.querySelector(".mbar-label"), () => {
            clearInterval(grow); b.disabled = false; cb.openPhase(pid, "literatura");
          });
        } else { b.disabled = false; out.innerHTML = "<span class='err'>error al investigar</span>"; }
      }));
    view.querySelectorAll("[data-deepen]").forEach((b) =>
      b.addEventListener("click", async () => {
        const out = view.querySelector("#lit-run-out");
        b.disabled = true;
        b.textContent = "📖 Descargando PDFs, leyendo texto completo e indexando…";
        const { ok: dok, body: d } = await post(
          `/portal/api/projects/${encodeURIComponent(pid)}/hypothesis/${b.dataset.deepen}/literature/deepen`, {});
        b.disabled = false;
        b.textContent = "📖 Leer a fondo (descargar PDFs + leer texto completo + indexar)";
        if (dok && d.ok) {
          out.textContent = `📖 ${d.fulltext_read}/${d.fulltext_attempted} papers LEÍDOS a texto completo · +${d.level2_added} referencias nivel-2 · ${(d.pdfs_saved || []).length} PDFs al vault · índice: ${esc(d.embeddings_backend || "")}`;
          cb.openPhase(pid, "literatura");
        } else out.textContent = "Error: " + esc((d && d.error) || "profundizar");
      }));
    view.querySelectorAll("[data-adopt]").forEach((b) =>
      b.addEventListener("click", async () => {
        b.disabled = true;
        b.textContent = "Tomando…";
        const { ok: aok, body: a } = await post(
          `/portal/api/projects/${encodeURIComponent(pid)}/hypothesis/${b.dataset.adopt}/adopt-improved`, {});
        b.disabled = false;
        if (aok && a.ok) cb.openPhase(pid, "literatura");
        else b.textContent = "Error: " + ((a && a.error) || "no se pudo tomar");
      }));
    view.querySelector("#lit-run-all").addEventListener("click", async () => {
      const out = view.querySelector("#lit-run-out");
      const btn = view.querySelector("#lit-run-all");
      btn.disabled = true;
      out.textContent = "Lanzando subagentes en paralelo…";
      const { ok: aok, body: a } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/investigate-all`, {});
      if (!aok || !a.ok || !a.run) {
        btn.disabled = false;
        out.textContent = "Error al lanzar los subagentes.";
        return;
      }
      pollRun(a.run.id, out, () => {
        btn.disabled = false;
        cb.openPhase(pid, "literatura");
      });
    });
    // --- missions: autonomous per-hypothesis research cycle -----------------
    const strip = view.querySelector("#missions-strip");
    const S_ICON = { PENDING: "⏳", RUNNING: "🚀", DONE: "✅", FAILED: "❌" };
    async function paintMissions() {
      const { ok: mok, body: mb } = await get(`/portal/api/projects/${encodeURIComponent(pid)}/missions`);
      if (!mok || !strip) return false;
      const ms = (mb.missions || []);
      strip.innerHTML = ms.length ? ms.map((mn) => {
        const steps = (mn.steps || []).map((s2) =>
          `<span class="mstep ${s2.status.toLowerCase()}" title="${esc(s2.error || s2.info || "")}">${S_ICON[s2.status] || "⏳"} ${esc(s2.name.replace("experiments_", "exp:"))}</span>`).join(" → ");
        const retry = mn.status === "FAILED" ? ` <button class="act ghost" data-mretry="${esc(mn.id)}">↻ Reintentar</button>` : "";
        const pct = mn.status === "DONE" ? 100 : (mn.progress_pct || 0);
        const queued = mn.status === "PENDING"
          ? ` <span class="tag warn-txt">⏳ en cola — esperando turno (máx 2 misiones a la vez)</span>` : "";
        return `<div class="mission-line">${S_ICON[mn.status] || "⏳"} <b>${esc(mn.hyp_tag)}</b> <span class="tag">${pct}%</span>${queued} ${steps}${retry}</div>`;
      }).join("") : "";
      strip.querySelectorAll("[data-mretry]").forEach((b) =>
        b.addEventListener("click", async () => {
          b.disabled = true;
          await post(`/portal/api/missions/${b.dataset.mretry}/retry`, {});
        }));
      return ms.some((mn) => mn.status === "RUNNING" || mn.status === "PENDING");
    }
    paintMissions().then((live) => {
      if (!live) return;
      const t = setInterval(async () => {
        if (!document.body.contains(strip)) { clearInterval(t); return; }
        const still = await paintMissions();
        if (!still) { clearInterval(t); cb.openPhase(pid, "literatura"); }
      }, 4000);
    });
    view.querySelectorAll("[data-mission]").forEach((b) =>
      b.addEventListener("click", async () => {
        b.disabled = true;
        b.textContent = "🚀 Misión lanzada…";
        const { ok: sok, body: sb } = await post(
          `/portal/api/projects/${encodeURIComponent(pid)}/hypothesis/${b.dataset.mission}/mission`, {});
        if (!sok || !sb.ok) { b.disabled = false; b.textContent = "Error: " + esc((sb && sb.error) || "misión"); return; }
        paintMissions();
      }));
    view.querySelector("#msn-all").addEventListener("click", async () => {
      const btn = view.querySelector("#msn-all");
      btn.disabled = true;
      await post(`/portal/api/projects/${encodeURIComponent(pid)}/missions/start-all`, {});
      btn.disabled = false;
      paintMissions();
    });

    wireCriticConvert(view, pid, cb, phaseKey);
    wireAristoteles(view, pid, cb, () => cb.openPhase(pid, "literatura"));
    wireMissionBars(view, pid, cb);
    const vaultSearch = async () => {
      const q = view.querySelector("#vault-q").value.trim();
      const vout = view.querySelector("#vault-out");
      if (!q) return;
      vout.innerHTML = "<span class='loading'>buscando por significado…</span>";
      const { ok, body } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/vault/search`, { query: q });
      if (!ok) { vout.textContent = "error"; return; }
      const rows = (body.results || []).map((rr) =>
        `<li class="cite"><a href="${esc(rr.url || (rr.doi ? "https://doi.org/" + rr.doi : "#"))}" target="_blank" rel="noopener">${esc(rr.title.slice(0, 100))}</a>
          <span class="src">${esc(rr.source)}</span> <span class="tag">sim ${rr.score}</span>
          ${rr.has_fulltext ? `<span class="pill ok">texto completo</span>` : ""}</li>`).join("");
      vout.innerHTML = rows
        ? `<p class="tag">motor: ${esc(body.backend)} · ${body.n_indexed} papers indexados</p><ul class="cites">${rows}</ul>`
        : `<p class="tag">sin coincidencias (${esc(body.backend || "")})</p>`;
    };
    view.querySelector("#vault-go").addEventListener("click", vaultSearch);
    view.querySelector("#vault-q").addEventListener("keydown", (e) => { if (e.key === "Enter") vaultSearch(); });
    view.querySelectorAll("[data-htrace]").forEach((b) =>
      b.addEventListener("click", () => renderTrace(view, pid, b.dataset.htrace, cb)));
    get(`/portal/api/projects/${encodeURIComponent(pid)}/rigor`).then(({ ok: rk, body: rg }) => {
      const chip = view.querySelector("#rigor-chip");
      if (chip && rk) {
        chip.textContent = rg.score === null
          ? "rigor: sin objeciones aún"
          : `⚖️ rigor ${rg.score}/10 (${rg.resolved}/${rg.total} objeciones resueltas)`;
      }
    });
    view.querySelector("#watch-scan").addEventListener("click", async () => {
      const out = view.querySelector("#lit-run-out");
      const btn = view.querySelector("#watch-scan");
      btn.disabled = true;
      out.textContent = "📡 Consultando OpenAlex/arXiv por novedades…";
      const { ok: wok, body: w } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/watch/scan`, {});
      btn.disabled = false;
      if (wok && w.ok) {
        out.textContent = w.total_new
          ? `📡 ${w.total_new} papers NUEVOS encontrados — El Revisor los está evaluando`
          : "📡 Sin novedades en las fuentes (hoy)";
        if (w.total_new) setTimeout(() => cb.openPhase(pid, "literatura"), 1500);
      } else out.textContent = "Error en la vigilancia.";
    });
    view.querySelector("#obs-sync").addEventListener("click", async () => {
      const out = view.querySelector("#lit-run-out");
      const btn = view.querySelector("#obs-sync");
      btn.disabled = true;
      out.textContent = "Sincronizando vault Obsidian…";
      const { ok: sok, body: s } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/obsidian/sync`, {});
      btn.disabled = false;
      out.textContent = sok && s.ok
        ? `🧠 ${s.notes_written} notas en ${s.vault}`
        : "Error al sincronizar vault.";
    });
  } else {
    // experimentos por hipótesis
    const cards = approved.map((h) => {
      const litDone = h.lit_status === "DONE";
      const exps = (h.experiments || []).map((e) => {
        const st = e.status || "PROPOSED";
        const stColor = st === "COMPLETE" ? "ok" : st === "PLANNED" ? "warn" : "warn";
        // generated-analysis results: verdict + real metrics + data provenance + code
        const r = e.result || {};
        const V_COLOR = { supports: "ok", refutes: "bad", inconclusive: "warn" };
        const metrics = r.metrics
          ? Object.entries(r.metrics).slice(0, 5).map(([k, v]) =>
              `<span class="metric">${esc(k)}: <b>${esc(typeof v === "number" ? Number(v.toPrecision(4)).toString() : String(v))}</b></span>`).join(" ")
          : "";
        const provs = (e.provenance || []).map((p2) =>
          `<div class="tag">📦 <a href="${esc(p2.url)}" target="_blank" rel="noopener">${esc(p2.filename)}</a> · ${Math.round((p2.bytes || 0) / 1024)} KB · sha256 <code>${esc((p2.sha256 || "").slice(0, 12))}…</code></div>`).join("");
        const genDetail = r.verdict ? `
          <div class="gen-result">
            <div>${pill(r.verdict, V_COLOR[r.verdict] || "warn")} <span class="tag">análisis generado por IA — revisar código</span></div>
            <p class="tag">${esc(r.verdict_reason || "")}</p>
            <div class="metrics">${metrics}</div>
            ${r.null_test && r.null_test.description !== "ausente" ? `<div class="tag">🎲 Nulo: ${esc(r.null_test.description || "")} → ${r.null_test.passed ? "superado" : "NO superado"}</div>` : ""}
            ${provs}
            ${e.code_path ? `<div class="tag">📄 Código: <code>${esc(e.code_path)}</code></div>` : ""}
          </div>` : "";
        const result = e.claim ? `<div class="tag">${esc((e.claim || "").slice(0, 180))}</div>` : "";
        const ferr = e.factory_error ? `<div class="tag warn-txt">⚠️ La fábrica no pudo ejecutarlo (${esc(e.factory_error.stage || "")}): ${esc((e.factory_error.error || "").slice(0, 120))}</div>` : "";
        const plan = e.plan ? `<details><summary class="tag">plan de ejecución</summary><div class="lms-body">${esc(e.plan)}</div></details>` : "";
        const mIcon = { download_data: "⬇️ bajar datos", math_analysis: "∑ análisis", theoretical: "📐 teórico", simulation: "🎲 simulación" };
        const mt = e.method_type ? `<span class="src">${esc(mIcon[e.method_type] || e.method_type)}</span>` : "";
        const ev = e.hyp_version || 1;
        const evChip = verChip(`Exp v${ev}`, ev >= (h.version || 1),
          ev >= (h.version || 1) ? "experimento de la versión actual" : `propuesto para la v${ev}; la hipótesis va en v${h.version} — re-propón o reconsidera`);
        const viaB = String(e.via || "").startsWith("mission") ? `<span class="src">🚀 misión</span>` : (e.from_critique ? `<span class="src">🧐 de crítica</span>` : "");
        const sup = e.superseded_by_critique ? `<span class="pill warn">supeditado a crítica</span>` : "";
        const savedB = e.saved ? `<span class="pill ok">💾 guardado</span>` : `<button class="act ghost" data-esave="${esc(e.id)}">💾 Guardar</button>`;
        return `<div class="exp-line">
          <div class="exp-head"><b>${esc(e.title || "experimento")}</b> ${evChip} ${mt} ${viaB} ${pill(st, stColor)} ${sup} ${savedB}
            ${st === "PROPOSED" ? `<button class="act" data-runexp="${esc(e.id)}">▶ Correr experimento</button> <span class="tag" data-runout="${esc(e.id)}" aria-live="polite"></span>` : ""}</div>
          <div class="tag"><b>Qué:</b> ${esc(e.what || "")}</div>
          <div class="tag"><b>Cómo:</b> ${esc(e.how || "")}</div>
          <div class="tag"><b>Datos:</b> ${esc(e.data_source || "")} · <b>Controles:</b> ${esc(e.controls || "")}</div>
          ${st === "COMPLETE" || st === "PLANNED" ? `<button class="act" data-expdetail="${esc(e.id)}">🔬 Ver análisis completo</button>` : ""}
          ${result}${genDetail}${ferr}${plan}${e.critique ? criticFoot(e.critique, e.id, h.version || 1) : criticEmpty(e.id, "experimento_resultado")}
        </div>`;
      }).join("");
      return `<div class="card hyp-card">
        <div class="hyp-head"><b>${esc(h.tag)}: ${esc(h.title)}</b>
          ${pill(litDone ? `literatura ✓ (${h.lit_count})` : "literatura pendiente", litDone ? "ok" : "warn")}</div>
        ${litDone && (h.confrontation || {}).improved_hypothesis
          ? `<p class="tag">✨ <b>Hipótesis actualizada:</b> ${esc(h.confrontation.improved_hypothesis)}</p>` : ""}
        <button class="act ghost" data-propexp="${esc(h.id)}">🧪 Proponer experimentos (Codex)</button>
        <div class="exp-list">${exps || "<p class='muted tag'>Sin experimentos aún — propónlos.</p>"}</div>
      </div>`;
    }).join("");
    const orphans = ((fl && fl.orphans) || []).map((e) => `
      <div class="exp-line orphan">
        <div class="exp-head"><b>${esc(e.title || "experimento")}</b>
          <span class="pill warn">sin hipótesis</span>
          ${e.orphaned_from ? `<span class="tag">venía de ${esc(e.orphaned_from.tag || "")}</span>` : ""}</div>
        <div class="tag">Ancla este experimento a una hipótesis para que su flujo lo absorba:</div>
        <div>${approved.map((h) => `<button class="act ghost" data-anchor="${esc(e.id)}" data-to="${esc(h.id)}">⚓ ${esc(h.tag)}</button>`).join(" ")}</div>
      </div>`).join("");
    const orphanBlock = orphans ? `<div class="card"><b>💾 Experimentos guardados (huérfanos)</b>${orphans}</div>` : "";
    view.innerHTML = back +
      `<p class="eyebrow">Dashboard de fase · por hipótesis</p>
       <div class="pulse-head"><h1>⚗️ Experimentos</h1>
         <span class="tag">${approved.length} hipótesis aprobadas</span></div>
       <div class="run-all"><button class="act" id="exp-run-all">▶▶ Correr TODOS los experimentos</button>
         <span id="exp-run-out" class="tag" aria-live="polite"></span></div>
       ${cards}
       ${orphanBlock}
       <p class="tag">ACERO ejecuta de verdad los análisis con código (Kepler, Hubble); los demás quedan como PLAN reproducible pendiente de datos (no se inventan resultados).</p>`;
    wireAristoteles(view, pid, cb, () => cb.openPhase(pid, "experimentos"));
    view.querySelectorAll("[data-expdetail]").forEach((b) =>
      b.addEventListener("click", () => renderExperiment(view, pid, b.dataset.expdetail, cb, "experimentos")));
    view.querySelectorAll("[data-esave]").forEach((b) =>
      b.addEventListener("click", async () => {
        b.disabled = true;
        const { ok } = await post(
          `/portal/api/projects/${encodeURIComponent(pid)}/experiment/${b.dataset.esave}/save`, {});
        if (ok) cb.openPhase(pid, "experimentos");
      }));
    view.querySelectorAll("[data-anchor]").forEach((b) =>
      b.addEventListener("click", async () => {
        b.disabled = true;
        const { ok, body } = await post(
          `/portal/api/projects/${encodeURIComponent(pid)}/experiment/${b.dataset.anchor}/anchor`,
          { hyp_id: b.dataset.to });
        if (ok && body.ok) { alert(`Anclado a ${body.anchored_to}. El flujo lo absorbió: ${body.synthesis}`); cb.openPhase(pid, "experimentos"); }
        else { b.disabled = false; alert("Error: " + ((body && body.error) || "")); }
      }));
    view.querySelectorAll("[data-propexp]").forEach((b) =>
      b.addEventListener("click", async () => {
        b.disabled = true; b.textContent = "Proponiendo (Codex)…";
        const { ok: pok } = await post(
          `/portal/api/projects/${encodeURIComponent(pid)}/hypothesis/${b.dataset.propexp}/experiments/propose`, {});
        if (pok) cb.openPhase(pid, "experimentos");
      }));
    view.querySelectorAll("[data-runexp]").forEach((b) =>
    b.addEventListener("click", async () => {
      const out = view.querySelector(`[data-runout="${b.dataset.runexp}"]`);
      b.disabled = true;
      if (out) out.textContent = "lanzando subagente…";
      const { ok, body } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/experiment/${b.dataset.runexp}/run`, {});
      if (ok && body.ok && body.run) {
        pollRun(body.run.id, out || b, () => cb.openPhase(pid, "experimentos"));
      } else { b.disabled = false; if (out) out.textContent = "error al lanzar"; }
    }));
    view.querySelector("#exp-run-all").addEventListener("click", async () => {
      const out = view.querySelector("#exp-run-out");
      const btn = view.querySelector("#exp-run-all");
      btn.disabled = true;
      out.textContent = "Lanzando subagentes en paralelo…";
      const { ok: aok, body: a } = await post(
        `/portal/api/projects/${encodeURIComponent(pid)}/experiments/run-all`, {});
      if (!aok || !a.ok || !a.run) {
        btn.disabled = false;
        out.textContent = "Error al lanzar los subagentes.";
        return;
      }
      pollRun(a.run.id, out, () => {
        btn.disabled = false;
        cb.openPhase(pid, "experimentos");
      });
    });
  }
  view.querySelector("#ph-back").addEventListener("click", () => cb.openProject(pid));
}

/* --------------------------------------------------------- educational plan -- */
export async function eduPlanFlow(pid, cb) {
  const panel = document.querySelector("#float-panel");
  const title = document.querySelector("#float-title");
  const body = document.querySelector("#float-body");
  panel.hidden = false;
  title.textContent = "🎓 Plan educativo";
  body.innerHTML = "<p class='loading'>Generando plan de estudio desde el estado real de la investigación… (Codex, hasta ~2 min)</p>";
  const { ok, body: res } = await post(
    `/portal/api/projects/${encodeURIComponent(pid)}/edu-plan`, { use_ai: true });
  if (!ok || !res.ok) {
    body.innerHTML = `<p class="err">error: ${esc((res && (res.detail || res.error)) || "plan")}</p>`;
    return;
  }
  const plan = res.plan;
  const rows = (plan.topics || []).map((t) => `
    <div class="topic-row">
      <input type="checkbox" id="tp-${esc(t.id)}" data-topic="${esc(t.id)}" checked>
      <div><label for="tp-${esc(t.id)}"><b>${esc(t.title)}</b></label>
        <div class="tag">${esc(t.why || "")}</div>
        <div class="tag">Conceptos: ${esc((t.concepts || []).join(", "))}</div></div>
      <span class="lvl">${pill(t.level || "core", t.level === "bloqueante" ? "bad" : "warn")}</span>
    </div>`).join("");
  body.innerHTML =
    `<p class="muted">${esc(plan.title)} · generado por ${esc(plan.provider)}.
      Apaga los temas que ya dominas — el curso solo incluirá lo encendido.</p>
     ${rows}
     <div style="margin-top:.9rem; display:flex; gap:.6rem">
       <button class="act" id="gen-course">📘 Generar curso</button>
       <span id="gen-out" class="tag" aria-live="polite"></span>
     </div>
     <p class="tag">${esc(res.disclaimer || "")}</p>`;
  body.querySelector("#gen-course").addEventListener("click", async () => {
    const chosen = [...body.querySelectorAll("[data-topic]")]
      .filter((c) => c.checked).map((c) => c.dataset.topic);
    const out = body.querySelector("#gen-out");
    if (!chosen.length) { out.textContent = "Selecciona al menos un tema."; return; }
    const btn = body.querySelector("#gen-course");
    btn.disabled = true;
    out.textContent = "Generando curso didáctico… (hasta ~3 min)";
    const { ok: cok, body: cres } = await post(
      `/portal/api/projects/${encodeURIComponent(pid)}/course`,
      { topic_ids: chosen, use_ai: true });
    btn.disabled = false;
    if (!cok || !cres.ok) {
      out.textContent = "Error: " + ((cres && (cres.detail || cres.error)) || "curso");
      return;
    }
    const c = cres.course;
    out.innerHTML = "";
    btn.hidden = true;
    body.querySelector("#gen-out").insertAdjacentHTML("beforebegin",
      `<span class="pill ok">Curso listo: ${esc(c.title)} (${c.n_lessons} lecciones)</span>
       <button class="act" id="go-course">▶ Ir a curso</button>`);
    body.querySelector("#go-course").addEventListener("click", () => {
      panel.hidden = true;
      cb.openCourse(c.id);
    });
  });
}

/* ----------------------------------------------------------------- courses -- */
export async function renderCourses(view, cb) {
  view.innerHTML = "<p class='loading'>Cargando cursos…</p>";
  const { body: courses } = await get("/portal/api/courses");
  const list = Array.isArray(courses) ? courses : [];
  const cards = list.map((c) => {
    const pct = (c.progress || {}).pct || 0;
    const done = c.status === "COMPLETED";
    return `<div class="card">
      <h3>${esc(c.title)}</h3>
      <div>${pill(done ? "COMPLETADO ✓" : c.status, done ? "ok" : "warn")}
        <span class="tag">investigación: ${esc(c.project_title || c.project_id)} ·
        ${c.n_lessons} lecciones · ${esc(c.provider)}</span></div>
      <div class="progressbar" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0"
           aria-valuemax="100"><div style="width:${pct}%"></div></div>
      <div class="tag">${pct}% completado</div>
      <div style="margin-top:.5rem; display:flex; gap:.5rem; flex-wrap:wrap">
        <button class="act" data-go="${esc(c.id)}">▶ ${done ? "Repasar curso" : "Ir a curso"}</button>
        <button class="act ghost" data-sync="${esc(c.id)}"
          title="Agregar temas nuevos si la investigación creció">↻ Sync con investigación</button>
        <button class="act danger" data-del="${esc(c.id)}"
          title="Borrar este curso">🗑 Borrar</button>
      </div>
      <div class="tag" data-syncout="${esc(c.id)}" aria-live="polite"></div>
    </div>`;
  }).join("");
  view.innerHTML =
    `<div class="proj-head"><h1>🎓 Cursos</h1>
      <p class="muted">Cursos vinculados a tus investigaciones. Si una investigación crece,
      usa «Sync» para agregar los temas nuevos automáticamente.</p></div>
     ${cards || "<p class='muted'>No hay cursos aún — genera uno desde el botón «🎓 Plan educativo» dentro de una investigación.</p>"}`;
  view.querySelectorAll("[data-go]").forEach((b) =>
    b.addEventListener("click", () => cb.openCourse(b.dataset.go)));
  view.querySelectorAll("[data-sync]").forEach((b) =>
    b.addEventListener("click", async () => {
      const out = view.querySelector(`[data-syncout="${b.dataset.sync}"]`);
      out.textContent = "Sincronizando…";
      const { ok, body: s } = await post(`/portal/api/courses/${b.dataset.sync}/sync`, {});
      out.textContent = ok && s.ok ? s.note : "error de sync";
      if (ok && s.ok && s.added) cb.openCourses();
    }));
  view.querySelectorAll("[data-del]").forEach((b) =>
    b.addEventListener("click", async () => {
      if (!confirm("¿Borrar este curso? No se puede deshacer.")) return;
      const { ok, body: d } = await post(`/portal/api/courses/${b.dataset.del}/delete`, {});
      if (ok && d.ok) cb.openCourses();
      else alert("Error al borrar: " + ((d && (d.detail || d.error)) || ""));
    }));
}

/* -------------------------------------------------------------- LMS viewer -- */
export async function renderCourse(view, courseId, cb) {
  view.innerHTML = "<p class='loading'>Cargando curso…</p>";
  const { ok, body: c } = await get(`/portal/api/courses/${encodeURIComponent(courseId)}`);
  if (!ok) { view.innerHTML = "<p class='err'>curso no encontrado</p>"; return; }
  const flat = [];
  (c.modules || []).forEach((m, mi) =>
    (m.lessons || []).forEach((ls, li) =>
      flat.push({ key: `m${mi}l${li}`, module: m.title, ...ls })));
  let idx = 0;
  const completed = new Set(((c.progress || {}).completed) || []);
  // resume at the first incomplete lesson
  const firstIncomplete = flat.findIndex((l) => !completed.has(l.key));
  if (firstIncomplete > 0) idx = firstIncomplete;

  const paint = () => {
    const l = flat[idx];
    const pct = Math.round(100 * completed.size / Math.max(1, flat.length));
    const quiz = (l.quiz_options || []).map((o, i) =>
      `<label><input type="radio" name="quiz" value="${i}"> ${esc(o)}</label>`).join("");
    view.innerHTML =
      `<button class="act ghost" id="lms-back">← Cursos</button>
       <div class="lms">
         <div class="lms-head">
           <h1 style="margin:0">${esc(c.title)}</h1>
           ${pill(pct >= 100 ? "COMPLETADO ✓" : pct + "%", pct >= 100 ? "ok" : "warn")}
         </div>
         <div class="progressbar" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0"
              aria-valuemax="100"><div style="width:${pct}%"></div></div>
         <p class="tag">Lección ${idx + 1} de ${flat.length} · módulo: ${esc(l.module)} ·
           vinculado a: ${esc(c.project_title || "")}</p>
         <div class="lms-lesson">
           <h2>${esc(l.title)}</h2>
           <div class="lms-body">${esc(l.body || "")}</div>
           <div class="lms-quiz">
             <b>🧠 Pregunta:</b> ${esc(l.quiz_question || "")}
             <div>${quiz}</div>
             <button class="act ghost" id="quiz-check" style="margin-top:.4rem">Responder</button>
             <span id="quiz-fb" aria-live="polite"></span>
           </div>
         </div>
         <div class="lms-nav">
           <button class="act ghost" id="lms-prev" ${idx === 0 ? "disabled" : ""}>← Anterior</button>
           <button class="act" id="lms-next">${idx >= flat.length - 1 ? "Terminar curso ✓" : "Siguiente →"}</button>
           <span class="tag">${completed.has(l.key) ? "lección completada ✓" : ""}</span>
         </div>
       </div>`;
    view.querySelector("#lms-back").addEventListener("click", () => cb.openCourses());
    view.querySelector("#quiz-check").addEventListener("click", () => {
      const sel = view.querySelector("input[name=quiz]:checked");
      const fb = view.querySelector("#quiz-fb");
      if (!sel) { fb.textContent = "Elige una opción."; return; }
      const okAns = Number(sel.value) === Number(l.quiz_answer_idx);
      fb.innerHTML = okAns ? "<span class='quiz-ok'>✓ Correcto</span>"
        : `<span class='quiz-bad'>✗ No — revisa la lección</span>`;
    });
    view.querySelector("#lms-prev").addEventListener("click", () => { idx--; paint(); });
    view.querySelector("#lms-next").addEventListener("click", async () => {
      if (!completed.has(l.key)) {
        completed.add(l.key);
        await post(`/portal/api/courses/${encodeURIComponent(courseId)}/progress`,
                   { lesson_key: l.key });
      }
      if (idx < flat.length - 1) { idx++; paint(); }
      else { paint(); }   // last lesson → repaint shows COMPLETADO
    });
  };
  paint();
  cb.setContext({ scope: "course", course_id: courseId, project_id: c.project_id,
                  label: `Curso: ${c.title}` });
}
