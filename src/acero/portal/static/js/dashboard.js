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

/* ------------------------------------------------------------ phase detail -- */
export async function renderPhaseDetail(view, pid, phaseKey, cb) {
  view.innerHTML = "<p class='loading'>Cargando fase…</p>";
  const { ok, body: ph } = await get(`/portal/api/projects/${encodeURIComponent(pid)}/phases`);
  if (!ok) { view.innerHTML = "<p class='err'>error</p>"; return; }
  const f = ph.phases.find((x) => x.key === phaseKey);
  if (!f) { view.innerHTML = "<p class='err'>fase desconocida</p>"; return; }
  const m = f.methodology || {};

  const items = (f.items || []).map((i) => {
    const link = i.url ? `<a href="${esc(i.url)}" target="_blank" rel="noopener">${esc(i.title)}</a>`
                       : esc(i.title);
    return `<div class="card">${link}
      ${i.flag ? " " + pill(i.flag, "bad") : ""}
      <div class="tag">${esc(i.meta || "")}</div></div>`;
  }).join("");

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
     <h3 style="margin:.4rem 0 .6rem">Detalle (${(f.items || []).length})</h3>
     ${items || "<p class='muted'>Sin items en esta fase todavía.</p>"}
     <p class="tag" style="margin-top:.6rem">${esc(ph.honesty)}</p>`;
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
      <div style="margin-top:.5rem; display:flex; gap:.5rem">
        <button class="act" data-go="${esc(c.id)}">▶ ${done ? "Repasar curso" : "Ir a curso"}</button>
        <button class="act ghost" data-sync="${esc(c.id)}"
          title="Agregar temas nuevos si la investigación creció">↻ Sync con investigación</button>
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
