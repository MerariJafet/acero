"use strict";
import { get, post } from "./api.js";
import { esc, kv, pill, table } from "./components.js";

// The project IS the thread. Clicking a project opens this full workspace:
// the copilot chat is the central conversation, and every tool (research actions,
// literature, knowledge, learning, history) lives INSIDE the project context.

export async function renderProjectWorkspace(view, pid) {
  view.innerHTML = "<p class='loading'>Cargando proyecto…</p>";
  const { ok, body: p } = await get("/portal/api/projects/" + encodeURIComponent(pid));
  if (!ok) { view.innerHTML = "<p class='err'>No se pudo cargar el proyecto.</p>"; return; }

  view.innerHTML =
    `<button class="act ghost" id="pw-back">← Proyectos</button>` +
    `<section class="panel pw-head">
       <h2>${esc(p.title)}</h2>
       <div>${pill(p.domain)} ${pill(p.state, "ok")} <span class="tag">${esc(p.id)}</span></div>
       <div class="tag" id="pw-stats">Hipótesis ${p.hypotheses.length} · Experimentos ${p.experiments.length} · Conocimiento ${(p.world || {}).n_nodes || 0} nodos · Eventos ${p.history.length}</div>
     </section>` +
    `<div class="tabs" role="tablist" aria-label="Herramientas del proyecto">
       <button data-tab="status" class="active">📍 Estado</button>
       <button data-tab="chat">💬 Copiloto</button>
       <button data-tab="research">🔬 Investigar</button>
       <button data-tab="lit">🔎 Literatura</button>
       <button data-tab="world">🧠 Conocimiento</button>
       <button data-tab="learn">📚 Aprender</button>
       <button data-tab="loop">🔁 Loop autónomo</button>
       <button data-tab="history">📜 Historial</button>
     </div>
     <div id="pw-tab"></div>`;

  view.querySelector("#pw-back").addEventListener("click", () =>
    window.dispatchEvent(new CustomEvent("acero:navigate", { detail: "Projects" })));

  const tabs = view.querySelectorAll(".tabs button");
  const show = (name) => {
    tabs.forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
    TABS[name](view.querySelector("#pw-tab"), pid, p);
  };
  tabs.forEach((b) => b.addEventListener("click", () => show(b.dataset.tab)));
  show("status");
}

const CHIPS = [
  "Propón hipótesis competidoras para este proyecto",
  "¿Qué datos públicos debería usar y con qué licencia?",
  "Diseña las pruebas nulas y los falsos positivos",
  "¿Cuándo debería abstenerse ACERO aquí?",
];

const TABS = {
  // --- 📍 Estado: what's done, where we are, what's next, decisions -------
  status: async (el, pid) => {
    el.innerHTML = "<p class='loading'>Calculando estado real…</p>";
    const { ok, body: st } = await get(`/portal/api/projects/${encodeURIComponent(pid)}/status`);
    if (!ok) { el.innerHTML = "<p class='err'>error cargando estado</p>"; return; }

    const stepper = st.stages.map((s) =>
      `<div class="stage ${s.done ? "done" : (s.stage === st.current_stage ? "now" : "todo")}">
         <span class="stage-dot">${s.done ? "✓" : (s.stage === st.current_stage ? "●" : "○")}</span>
         <span class="stage-name">${esc(s.stage)}</span>
         <span class="tag">${esc(s.detail || "")}</span>
       </div>`).join("");

    const doneList = st.done_items.length
      ? st.done_items.map((d) =>
          `<div class="card"><b>[${esc(d.kind)}]</b> ${esc(d.title)}` +
          `${d.status ? " " + pill(d.status, d.kind.includes("REAL") ? "ok" : "warn") : ""}` +
          `${d.note ? `<div class="tag">${esc(d.note)}</div>` : ""}</div>`).join("")
      : "<p class='muted'>Aún no se ha hecho trabajo en este proyecto.</p>";

    const decisions = st.decisions.map((d) =>
      `<div class="kv"><span>${esc(d.at)} · ${esc(d.actor)}</span><b>${esc(d.decision)}</b></div>`).join("");

    const nexts = st.next_steps.map((n, i) =>
      `<div class="kv"><span>${i + 1}. ${esc(n.text)}</span>` +
      `<button class="chip" data-goto="${esc(n.tab)}">ir →</button></div>`).join("");

    el.innerHTML =
      `<div class="panel"><h3>🧭 Dónde estamos</h3>` +
      `<p><b>Etapa actual: ${esc(st.current_stage)}</b></p><div class="stepper">${stepper}</div></div>` +
      `<div class="panel"><h3>✅ Lo que ya se hizo (${st.n_done})</h3>${doneList}</div>` +
      `<div class="panel"><h3>🗳️ Decisiones tomadas</h3>${decisions}</div>` +
      `<div class="panel"><h3>➡️ Qué sigue (recomendado)</h3>${nexts}</div>` +
      `<p class="tag">${esc(st.honesty)}</p>`;

    el.querySelectorAll("[data-goto]").forEach((b) =>
      b.addEventListener("click", () => {
        const t = el.parentElement.querySelector(`.tabs button[data-tab="${b.dataset.goto}"]`);
        if (t) t.click();
      }));
  },

  // --- 💬 Copiloto: the persistent conversation thread --------------------
  chat: async (el, pid) => {
    el.innerHTML = `<div class="panel">
        <div class="chat-thread" id="ch-thread" aria-live="polite"></div>
        <div id="ch-chips"></div>
        <div class="chat-input">
          <textarea id="ch-msg" rows="2" placeholder="Pregunta o pide algo sobre este proyecto…"></textarea>
          <button class="act" id="ch-send">Enviar</button>
        </div>
        <p class="tag">El copiloto es ayuda de razonamiento (Codex) — NO evidencia científica. El hilo se guarda con el proyecto.</p>
      </div>`;
    const thread = el.querySelector("#ch-thread");
    const paint = (msgs) => {
      thread.innerHTML = msgs.length
        ? msgs.map((m) => `<div class="msg ${m.role === "user" ? "user" : "assistant"}">${esc(m.text)}</div>`).join("")
        : "<p class='muted'>Sin mensajes aún. Empieza con una de las sugerencias o escribe la tuya.</p>";
      thread.scrollTop = thread.scrollHeight;
    };
    const { body: msgs } = await get(`/portal/api/projects/${encodeURIComponent(pid)}/chat`);
    paint(Array.isArray(msgs) ? msgs : []);
    const chipBox = el.querySelector("#ch-chips");
    if (!Array.isArray(msgs) || !msgs.length) {
      chipBox.innerHTML = CHIPS.map((c) => `<button class="chip">${esc(c)}</button>`).join(" ");
      chipBox.querySelectorAll(".chip").forEach((b) =>
        b.addEventListener("click", () => { el.querySelector("#ch-msg").value = b.textContent; }));
    }
    const send = async () => {
      const box = el.querySelector("#ch-msg");
      const text = box.value.trim();
      if (!text) return;
      box.value = "";
      chipBox.innerHTML = "";
      thread.insertAdjacentHTML("beforeend", `<div class="msg user">${esc(text)}</div>` +
        `<div class="msg assistant loading" id="ch-wait">Pensando… (Codex puede tardar 1–3 min)</div>`);
      thread.scrollTop = thread.scrollHeight;
      const btn = el.querySelector("#ch-send");
      btn.disabled = true;
      const { ok, body } = await post(`/portal/api/projects/${encodeURIComponent(pid)}/copilot`, { message: text });
      btn.disabled = false;
      const wait = el.querySelector("#ch-wait");
      if (!ok || !body.ok === true && !body.reply) {
        wait.textContent = "Error: " + ((body && (body.detail || body.error)) || "copiloto");
        wait.classList.add("err");
        return;
      }
      wait.classList.remove("loading");
      wait.removeAttribute("id");
      wait.textContent = body.reply || "(sin respuesta)";
      thread.scrollTop = thread.scrollHeight;
    };
    el.querySelector("#ch-send").addEventListener("click", send);
    el.querySelector("#ch-msg").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send();
    });
  },

  // --- 🔬 Investigar: real gate-guarded actions ---------------------------
  research: async (el, pid, p) => {
    el.innerHTML = `<div class="panel">
        <h3>Acciones reales (gate-guardadas)</h3>
        <div class="field"><label for="rc-q">Pregunta científica acotada</label>
          <input id="rc-q" value="${esc((p.title || "").slice(0, 80))}"></div>
        <button class="act" id="rc-go">⚙️ Lanzar ciclo de investigación</button>
        <button class="act" id="rd-go">🔭 Verificar con datos reales (NASA)</button>
        <button class="act" id="deep-go">🌌 Investigación A FONDO (datos + papers + síntesis)</button>
        <div id="rc-out" aria-live="polite"></div>
      </div>`;
    el.querySelector("#deep-go").addEventListener("click", async () => {
      const ro = el.querySelector("#rc-out");
      ro.innerHTML = "<p class='loading'>Investigando a fondo: datos reales + literatura (Crossref) + síntesis (Codex)… puede tardar 1–3 min.</p>";
      const btn = el.querySelector("#deep-go");
      btn.disabled = true;
      const { ok, body: b } = await post(`/portal/api/projects/${encodeURIComponent(pid)}/deep-investigation`, {});
      btn.disabled = false;
      if (!ok || !b.ok) { ro.innerHTML = `<p class="err">error: ${esc((b && (b.detail || b.error)) || "deep")}</p>`; return; }
      const angles = (b.findings || []).map((f) => {
        const papers = (f.papers || []).map((p) =>
          `<li><a href="${esc(p.url)}" target="_blank" rel="noopener">${esc((p.title || p.doi).slice(0, 80))}</a>` +
          `${p.integrity === "retracted" ? " " + pill("RETRACTADO", "bad") : ""} <span class="tag">${esc(p.doi)}</span></li>`).join("");
        const dr = f.data_result ? `<div class="tag">DATOS: ${esc((f.data_result.claim || "").slice(0, 200))}</div>` : "";
        return `<div class="card"><b>${esc(f.question)}</b>${dr}` +
          `<div class="tag">${esc(f.n_papers)} papers reales:</div><ul>${papers}</ul></div>`;
      }).join("");
      const syn = (b.synthesis || {}).text || "";
      ro.innerHTML = `<div class="card"><h4>Síntesis honesta (Codex — ayuda, NO evidencia)</h4>` +
        `<div style="white-space:pre-wrap">${esc(syn)}</div></div>` + angles +
        `<p class="tag">${esc(b.honesty || "")} · Dossier: ${esc(b.dossier_id || "")}</p>` +
        `<p class="muted">Recarga 📍 Estado para ver el avance actualizado.</p>`;
    });
    el.querySelector("#rc-go").addEventListener("click", async () => {
      const q = el.querySelector("#rc-q").value.trim();
      if (!q) return;
      const ro = el.querySelector("#rc-out");
      ro.innerHTML = "<p class='loading'>Ejecutando ciclo real…</p>";
      const { ok, body: b } = await post(`/portal/api/projects/${encodeURIComponent(pid)}/run-cycle`, { question: q });
      if (!ok) { ro.innerHTML = `<p class="err">error: ${esc((b && b.detail) || "run")}</p>`; return; }
      ro.innerHTML = `<div class="card">` + (b.steps || []).map((s) =>
        kv(s.step, JSON.stringify(Object.fromEntries(Object.entries(s).filter(([k]) => k !== "step"))))).join("") +
        `<div class="tag">${esc(b.note || "")}</div></div>`;
    });
    el.querySelector("#rd-go").addEventListener("click", async () => {
      const ro = el.querySelector("#rc-out");
      ro.innerHTML = "<p class='loading'>Analizando datos reales…</p>";
      const { ok, body: b } = await post(`/portal/api/projects/${encodeURIComponent(pid)}/verify-real-data`, {});
      if (!ok || !b.ok) { ro.innerHTML = `<p class="err">error: ${esc((b && (b.detail || b.error)) || "verify")}</p>`; return; }
      const rs = b.result || {};
      ro.innerHTML = `<div class="card">` +
        kv("dataset", rs.source) + kv("planetas (n)", rs.n_planets) +
        kv("R²", (rs.fitted || {}).r_squared) +
        kv("Tierra (1 AU): periodo predicho", (rs.earth_context || {}).predicted_period_yr_at_1AU_1Msun + " años (real 1.0)") +
        kv("consistente con Kepler", rs.consistent_with_kepler ? "sí" : "no") +
        `<div class="tag">${esc(rs.claim || "")}</div></div>`;
    });
  },

  // --- 🔎 Literatura: real Knowledge Mesh search --------------------------
  lit: async (el, pid, p) => {
    el.innerHTML = `<div class="panel">
        <h3>Literatura científica real (Knowledge Mesh · Crossref)</h3>
        <div class="field"><input id="lit-q" placeholder="p.ej.: ${esc(p.domain)} …"></div>
        <button class="act" id="lit-go">Buscar</button>
        <div id="lit-out" aria-live="polite"></div>
      </div>`;
    el.querySelector("#lit-go").addEventListener("click", async () => {
      const q = el.querySelector("#lit-q").value.trim();
      if (!q) return;
      const lo = el.querySelector("#lit-out");
      lo.innerHTML = "<p class='loading'>Buscando en fuentes reales…</p>";
      const { ok, body: b } = await get(`/portal/api/mesh/search?q=${encodeURIComponent(q)}&rows=6`);
      if (!ok) { lo.innerHTML = `<p class="err">error: ${esc((b && b.detail) || "search")}</p>`; return; }
      lo.innerHTML = `<p class="muted">${esc(b.n_results)} resultados · fuentes: ${esc((b.sources_consulted || []).join(", "))}</p>` +
        (b.results || []).map((it) => {
          const flag = it.integrity_status === "normal" ? "" : " " + pill(it.integrity_status, "bad");
          return `<div class="card"><a href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.title || it.doi)}</a>${flag}` +
            `<div class="tag">${esc(it.type)} · ${esc((it.authors || []).slice(0, 3).join(", "))} · ${esc(it.doi)}</div></div>`;
        }).join("") + `<p class="tag">${esc(b.disclaimer || "")}</p>`;
    });
  },

  // --- 🧠 Conocimiento: this project's World Model ------------------------
  world: async (el, pid) => {
    const { ok, body } = await get(`/portal/api/world/${encodeURIComponent(pid)}/nodes?limit=50`);
    if (!ok) { el.innerHTML = "<p class='err'>error cargando conocimiento</p>"; return; }
    const rows = (body.items || []).map((n) => [n.label, n.type, n.confidence]);
    el.innerHTML = `<div class="panel"><h3>Conocimiento del proyecto (World Model)</h3>` +
      (rows.length ? table(`${body.total} nodos de conocimiento`, ["Claim / concepto", "Tipo", "Confianza"], rows)
        : "<p class='muted'>Aún no hay nodos. Lanza un ciclo o una verificación con datos reales en 🔬 Investigar.</p>") +
      `</div>`;
  },

  // --- 📚 Aprender: learning scoped to this project -----------------------
  learn: async (el, pid) => {
    const { ok, body } = await get(`/portal/api/projects/${encodeURIComponent(pid)}/learning`);
    if (!ok) { el.innerHTML = "<p class='err'>error cargando aprendizaje</p>"; return; }
    el.innerHTML = `<div class="panel"><h3>Aprendizaje para este proyecto (${esc(body.domain)})</h3>` +
      `<p class="muted">${esc(body.note || "")}</p>` +
      (body.concepts || []).map((c) =>
        `<div class="card"><b>${esc(c.concept)}</b> ${c.blocking ? pill("BLOQUEANTE", "bad") : pill(c.criticality, "warn")}` +
        `<div class="tag">${esc(c.reason)}</div><div class="tag">currículo: ${esc(c.curriculum)}</div></div>`).join("") +
      `</div>`;
  },

  // --- 🔁 Loop autónomo: el Investigador Principal ------------------------
  loop: async (el, pid) => {
    const base = `/portal/api/projects/${encodeURIComponent(pid)}/loop`;
    let timer = null;
    async function draw() {
      const { ok, body } = await get(base);
      if (!ok) { el.innerHTML = "<p class='err'>no se pudo cargar el loop</p>"; return; }
      const st = body.state || {}, fb = (body.feedback || []).slice().reverse();
      const running = !st.paused && st.status === "running";
      const rows = fb.length ? fb.map((r) => {
        const d = r.decision || {}, a = r.applied || {};
        const blocks = (a.blocks || []).length
          ? `<div class="tag bad">EVA bloqueó: ${esc((a.blocks || []).join("; ").slice(0, 160))}</div>` : "";
        return `<div class="card">
          <b>tick ${esc(r.tick)}</b> · ${esc(d.action || "?")}
          ${d.focus ? `— <span class="muted">${esc(String(d.focus).slice(0, 80))}</span>` : ""}
          <div class="tag">generadas ${esc(a.generated || 0)} · aprobadas ${esc(a.approved || 0)} · misiones ${esc(a.started || 0)}${r.dry ? " · seco" : ""}</div>
          ${blocks}</div>`;
      }).join("") : "<p class='muted'>sin ticks aún — pulsa Iniciar</p>";
      el.innerHTML =
        `<section class="panel">
           <h3>🔁 Investigador Principal (loop autónomo)</h3>
           <p class="muted">El agente decide → la máquina corre los experimentos → la retro vuelve al agente → repite. La metodología gobierna cada paso; nada se promueve a descubrimiento sin tu revisión.</p>
           <div class="tag">estado: ${pill(st.paused ? "pausado" : (st.status || "idle"), st.paused ? "warn" : "ok")} · ticks ${esc(st.ticks || 0)} · seco×${esc(st.dry_streak || 0)}</div>
           <div class="chat-actions" style="margin-top:.6rem">
             <button id="lp-start" class="act" ${running ? "disabled" : ""}>▶ ${st.ticks ? "Reanudar" : "Iniciar"}</button>
             <button id="lp-pause" class="act ghost" ${running ? "" : "disabled"}>⏸ Pausar</button>
             <button id="lp-tick" class="act ghost">⏭ Avanzar un tick</button>
           </div>
         </section>
         <section class="panel"><h4>Últimas decisiones</h4>${rows}</section>`;
      el.querySelector("#lp-start").addEventListener("click", async () => {
        await post(base + "/start"); setTimeout(draw, 600);
      });
      el.querySelector("#lp-pause").addEventListener("click", async () => {
        await post(base + "/pause"); setTimeout(draw, 300);
      });
      el.querySelector("#lp-tick").addEventListener("click", async (e) => {
        e.target.disabled = true; e.target.textContent = "⏳ tick…";
        await post(base + "/tick"); draw();
      });
    }
    await draw();
    // refresco en vivo mientras el tab esté abierto
    timer = setInterval(() => {
      if (el.isConnected) draw(); else clearInterval(timer);
    }, 5000);
  },

  // --- 📜 Historial: provenance ------------------------------------------
  history: async (el, pid) => {
    const { ok, body: p } = await get("/portal/api/projects/" + encodeURIComponent(pid));
    if (!ok) { el.innerHTML = "<p class='err'>error</p>"; return; }
    el.innerHTML = `<div class="panel"><h3>Historial (provenance)</h3>` +
      ((p.history || []).map((h) =>
        `<div class="kv"><span>${esc(h.at)} · ${esc(h.action)} · ${esc(h.actor)}</span><b>${esc(h.summary || "")}</b></div>`).join("")
        || "<p class='muted'>sin eventos</p>") + `</div>`;
  },
};
