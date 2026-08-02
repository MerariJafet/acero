"use strict";
import { get, post, setCsrf } from "./api.js";
import { esc } from "./components.js";
import { VIEWS } from "./views.js";
import {
  eduPlanFlow, renderCourse, renderCourses, renderHome,
  renderPhaseDetail, renderProjectDash,
} from "./dashboard.js";
import { renderLearning } from "./learning.js";
import { renderEconomics } from "./economics.js";

const $ = (s) => document.querySelector(s);

// ---- app state -------------------------------------------------------------
const state = {
  project: null,          // current project id (null = home/global)
  context: { scope: "global", label: "Chat general — todas las investigaciones" },
};

const SUGGESTIONS = {
  global: ["¿Qué investigaciones tenemos y cómo van?",
           "Resume los hallazgos más importantes hasta hoy",
           "¿Qué investigación necesita mi decisión?"],
  project: ["¿En qué fase vamos y qué sigue?",
            "Propón el siguiente experimento",
            "¿Qué contraevidencia deberíamos buscar?"],
  course: ["Explícame esta lección con una analogía",
           "¿Por qué importa este tema para la investigación?",
           "Hazme una pregunta para comprobar que entendí"],
};

// ---- callbacks passed to dashboards ---------------------------------------
const cb = {
  openHome: () => { state.project = null; syncSelect(); setContext({ scope: "global" }); renderHome($("#view"), cb); },
  openProject: (pid) => {
    state.project = pid; syncSelect();
    setContext({ scope: "project", project_id: pid });
    renderProjectDash($("#view"), pid, cb);
  },
  openPhase: (pid, key) => {
    state.project = pid;
    setContext({ scope: "phase", project_id: pid, phase: key,
                 label: `Fase: ${key} — pregunta scoped en la tarjeta` });
    renderPhaseDetail($("#view"), pid, key, cb);
  },
  openCourses: () => { setContext({ scope: "global", label: "Cursos — chat general" }); renderCourses($("#view"), cb); },
  openCourse: (id) => renderCourse($("#view"), id, cb),
  openLearning: () => {
    state.project = null; syncSelect();
    setContext({ scope: "global", label: "Modo Aprender — tutor socrático" });
    renderLearning($("#view"), cb);
  },
  openEconomics: () => {
    state.project = null; syncSelect();
    setContext({ scope: "global", label: "Modo Económico — asesor sobre NEXUS" });
    renderEconomics($("#view"), cb);
  },
  openModeSelect: () => { state.project = null; syncSelect();
    setContext({ scope: "global" }); renderModeSelect($("#view"), cb); },
  setContext,
  refreshProjects: loadProjects,
};

// Landing: choose Learning vs Research (the two entry modes).
function renderModeSelect(view, cb) {
  view.innerHTML =
    `<div class="mode-select">
       <h1>¿Qué quieres hacer hoy?</h1>
       <div class="mode-grid">
         <button class="mode-card" id="mode-learn">
           <div class="mode-ic">🎓</div><h2>Modo Aprender</h2>
           <p>Un tutor te lleva de un tema general a la frontera del conocimiento.
           Cuando roces una pregunta abierta, la conviertes en investigación.</p>
           <span class="mode-go">Empezar a aprender →</span></button>
         <button class="mode-card" id="mode-research">
           <div class="mode-ic">🔬</div><h2>Modo Investigación</h2>
           <p>El flujo completo de ACERO: hipótesis, literatura, experimentos
           agénticos, revisión y el loop autónomo del Investigador Principal.</p>
           <span class="mode-go">Ir a mis investigaciones →</span></button>
         <button class="mode-card" id="mode-econ">
           <div class="mode-ic">💰</div><h2>Modo Económico</h2>
           <p>Diálogos e ideas para generar recursos y una economía sana, sobre tus
           datos reales de NEXUS. El asesor cuestiona cada idea hasta que funcione.</p>
           <span class="mode-go">Ir a mi economía →</span></button>
       </div>
     </div>`;
  view.querySelector("#mode-learn").addEventListener("click", () => cb.openLearning());
  view.querySelector("#mode-research").addEventListener("click", () => cb.openHome());
  view.querySelector("#mode-econ").addEventListener("click", () => cb.openEconomics());
}

// ---- chat context ----------------------------------------------------------
function setContext(ctx) {
  state.context = { ...ctx };
  const label = ctx.label
    || (ctx.scope === "global" ? "Chat general — todas las investigaciones"
        : ctx.scope === "project" ? "Chat de la investigación activa"
        : ctx.scope === "course" ? "Chat del curso"
        : "Chat");
  $("#chat-context").textContent = "📍 " + label;
  const sugg = SUGGESTIONS[ctx.scope === "phase" ? "project" : ctx.scope] || SUGGESTIONS.global;
  $("#suggestions").innerHTML = sugg.map((s) =>
    `<li><button type="button" class="suggestion-btn">${esc(s)}</button></li>`).join("");
  document.querySelectorAll(".suggestion-btn").forEach((b) =>
    b.addEventListener("click", () => { $("#question").value = b.textContent; $("#question").focus(); }));
  $("#edu-plan-btn").hidden = !(ctx.scope === "project" || ctx.scope === "phase");
  loadThread();
}

async function loadThread() {
  const box = $("#messages");
  box.innerHTML = "";
  if (state.context.scope === "global") {
    box.innerHTML = "<div class='msg assistant'>Hola — pregunta lo que quieras sobre TODAS tus investigaciones, o entra a una para trabajarla a fondo.</div>";
    return;
  }
  const pid = state.context.project_id || state.project;
  if (!pid) return;
  const { ok, body } = await get(`/portal/api/projects/${encodeURIComponent(pid)}/chat`);
  if (ok && Array.isArray(body) && body.length) {
    box.innerHTML = body.map((m) =>
      `<div class="msg ${m.role === "user" ? "user" : "assistant"}">${esc(m.text)}</div>`).join("");
  } else {
    box.innerHTML = "<div class='msg assistant'>Este es el hilo de la investigación. Todo lo que hablemos aquí queda guardado con el proyecto.</div>";
  }
  box.scrollTop = box.scrollHeight;
}

async function sendChat(text) {
  const box = $("#messages");
  box.insertAdjacentHTML("beforeend", `<div class="msg user">${esc(text)}</div>` +
    `<div class="msg assistant loading" id="chat-wait">Pensando… (Codex puede tardar 1–3 min)</div>`);
  box.scrollTop = box.scrollHeight;
  const loc = { scope: state.context.scope, phase: state.context.phase,
                course_id: state.context.course_id };
  let res;
  if (state.context.scope === "global") {
    res = await post("/portal/api/copilot/global", { message: text, location: loc });
  } else {
    const pid = state.context.project_id || state.project;
    res = await post(`/portal/api/projects/${encodeURIComponent(pid)}/copilot`,
                     { message: text, location: loc });
  }
  const wait = $("#chat-wait");
  if (!wait) return;
  wait.removeAttribute("id");
  if (res.ok && res.body && res.body.reply) {
    wait.classList.remove("loading");
    wait.textContent = res.body.reply;
  } else {
    wait.classList.add("err");
    wait.textContent = "Error: " + ((res.body && (res.body.detail || res.body.error)) || "copiloto");
  }
  box.scrollTop = box.scrollHeight;
}

// ---- topbar ----------------------------------------------------------------
async function loadProjects() {
  const { body } = await get("/portal/api/projects");
  const list = Array.isArray(body) ? body : [];
  const sel = $("#proj-select");
  sel.innerHTML = `<option value="">— Vista general —</option>` +
    list.map((p) => `<option value="${esc(p.id)}">${esc(p.title.slice(0, 48))}</option>`).join("");
  sel.value = state.project || "";
  return list;
}

function syncSelect() { const sel = $("#proj-select"); if (sel) sel.value = state.project || ""; }

function newProjectFlow() {
  const panel = $("#float-panel");
  $("#float-title").textContent = "＋ Nueva investigación";
  $("#float-body").innerHTML =
    `<div class="field"><label for="np-title">Nombre corto de la investigación</label>
       <input id="np-title" placeholder="p.ej.: Valle de radios de exoplanetas"></div>
     <div class="field"><label for="np-topic">Tema o pregunta de investigación
         <small>(el prompt libre — esto guía las hipótesis que se generen)</small></label>
       <textarea id="np-topic" rows="3"
         placeholder="p.ej.: ¿La posición del valle de radios depende de la metalicidad estelar de forma que distinga fotoevaporación de pérdida impulsada por el núcleo?"></textarea></div>
     <div class="field"><label for="np-domain">Dominio</label>
       <select id="np-domain">
         <option value="astronomy">astronomy</option><option value="physics">physics</option>
         <option value="chemistry">chemistry</option><option value="genetics">genetics</option>
         <option value="general">general</option>
       </select></div>
     <button class="act" id="np-create">Crear investigación</button>
     <span id="np-out" class="tag" aria-live="polite"></span>`;
  panel.hidden = false;
  $("#np-create").addEventListener("click", async () => {
    const topic = $("#np-topic").value.trim();
    let title = $("#np-title").value.trim();
    if (!title) title = topic.slice(0, 60);   // derive a short name from the topic
    if (!title) { $("#np-out").textContent = "Escribe un tema o un nombre."; return; }
    $("#np-out").textContent = "Creando…";
    const { ok, body } = await post("/portal/api/workspace/project",
      { title, domain: $("#np-domain").value, topic });
    if (!ok) { $("#np-out").textContent = "Error: " + esc(body.detail || ""); return; }
    panel.hidden = true;
    await loadProjects();
    cb.openProject(body.id);
  });
}

function buildSysMenu(sections) {
  $("#nav").innerHTML = sections.map((s) =>
    `<button data-view="${esc(s)}" ${VIEWS[s] ? "" : "disabled"}>${esc(s)}</button>`).join("");
  document.querySelectorAll("#nav button").forEach((b) =>
    b.addEventListener("click", async () => {
      $("#sys-menu").removeAttribute("open");
      const name = b.dataset.view;
      if (!VIEWS[name]) return;
      document.querySelectorAll("#nav button").forEach((x) =>
        x.classList.toggle("active", x === b));
      const view = $("#view");
      view.innerHTML = "<p class='loading'>Cargando…</p>";
      try {
        view.innerHTML = await VIEWS[name].render();
        if (VIEWS[name].mount) VIEWS[name].mount(view);
      } catch (e) {
        view.innerHTML = `<p class="err">error cargando ${esc(name)}: ${esc(e.message)}</p>`;
      }
    }));
}

// ---- auth + boot -----------------------------------------------------------
function showApp() { $("#login").hidden = true; $("#app").hidden = false; }
function showLogin() { $("#app").hidden = true; $("#login").hidden = false; }

async function enterApp() {
  showApp();
  const { body } = await get("/portal/api/overview");
  $("#version").textContent = "v" + (body.version || "?");
  $("#whoami").textContent = body.user ? `sesión: ${body.user}` : "";
  buildSysMenu(body.sections || Object.keys(VIEWS));
  await loadProjects();
  // arranque: pantalla de selección de modo (Aprender / Investigación)
  cb.openModeSelect();
}

async function doLogin(ev) {
  ev.preventDefault();
  const { ok, status, body } = await post("/portal/api/login",
    { username: $("#u").value, password: $("#p").value });
  const err = $("#login-error");
  if (!ok) {
    err.textContent = status === 429 ? "Demasiados intentos. Espera un momento."
      : "Credenciales incorrectas.";
    return;
  }
  err.textContent = "";
  setCsrf(body.csrf);
  await enterApp();
}

async function doLogout() {
  await post("/portal/api/logout", {});
  setCsrf(null);
  showLogin();
}

async function boot() {
  $("#login-form").addEventListener("submit", doLogin);
  $("#logout").addEventListener("click", doLogout);
  $("#home-btn").addEventListener("click", () => cb.openModeSelect());
  $("#new-project").addEventListener("click", newProjectFlow);
  $("#learn-btn").addEventListener("click", () => cb.openLearning());
  $("#econ-btn").addEventListener("click", () => cb.openEconomics());
  $("#courses-btn").addEventListener("click", () => cb.openCourses());
  $("#processes-btn").addEventListener("click", async () => {
    const panel = $("#float-panel");
    $("#float-title").textContent = "⚙️ Procesos activos";
    const body = $("#float-body");
    panel.hidden = false;
    async function paint() {
      const { ok, body: pr } = await get("/portal/api/processes");
      if (!ok) { body.innerHTML = "<p class='err'>error</p>"; return false; }
      const ms = (pr.missions || []).map((m) => {
        const pct = m.status === "DONE" ? 100 : (m.progress_pct || 0);
        return `<div class="mission-line">🚀 <b>${esc(m.hyp_tag)}</b> v${m.hyp_version}
          <span class="tag">${esc(m.project)}</span> ${esc(m.status)} <b>${pct}%</b>
          <div class="mbar"><div class="mbar-fill run" style="width:${pct}%"></div></div>
          ${m.current ? `<div class="mbar-label">${esc(m.current)}</div>` : ""}
          ${(m.steps || []).map((s2) => `<span class="mstep ${s2.status.toLowerCase()}">${esc(s2.name.replace("experiments_", "exp:"))}: ${esc(s2.status)}</span>`).join(" → ")}
        </div>`; }).join("");
      const rs = (pr.runs || []).map((r) => `
        <div class="mission-line">⚙️ ${esc(r.kind)} ${r.done}/${r.total}
          ${(r.items || []).map((i) => `<span class="mstep ${i.status.toLowerCase()}">${esc(i.label.slice(0, 40))}: ${esc(i.status)}</span>`).join(" · ")}
        </div>`).join("");
      body.innerHTML = (ms + rs) || "<p class='muted'>Sin procesos activos ahora mismo.</p>";
      return (pr.missions || []).length + (pr.runs || []).length > 0;
    }
    const live = await paint();
    if (live) {
      const t = setInterval(async () => {
        if (panel.hidden) { clearInterval(t); return; }
        if (!(await paint())) clearInterval(t);
      }, 4000);
    }
  });
  $("#float-close").addEventListener("click", () => { $("#float-panel").hidden = true; });
  $("#edu-plan-btn").addEventListener("click", () => {
    const pid = state.context.project_id || state.project;
    if (pid) eduPlanFlow(pid, cb);
  });
  $("#proj-select").addEventListener("change", (e) => {
    const v = e.target.value;
    if (v) cb.openProject(v); else cb.openHome();
  });
  $("#ask-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = $("#question").value.trim();
    if (!q) return;
    $("#question").value = "";
    sendChat(q);
  });
  window.addEventListener("acero:navigate", (e) => {
    // legacy hook used by old views ("← Proyectos")
    if (e.detail === "Projects") cb.openHome();
  });
  // resume session if the cookie is still valid
  const { ok, body } = await get("/portal/api/session");
  if (ok && body.csrf) { setCsrf(body.csrf); await enterApp(); }
  else showLogin();
}

boot();
