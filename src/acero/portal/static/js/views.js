"use strict";
import { get, post } from "./api.js";
import { esc, kv, panel, pill, table, resultCard } from "./components.js";
import { workspaceView } from "./workspace.js";

// Each view: { render: async () => htmlString, mount?: (rootEl) => void }.
// No inline event handlers (CSP forbids them); mount() wires listeners.

export const VIEWS = {
  "Overview": {
    render: async () => {
      const { body } = await get("/portal/api/overview");
      const q = Object.entries(body.runtime_queue || {}).map(([k, v]) => `${k}:${v}`).join(" ") || "empty";
      return panel("System overview",
        kv("env", body.env) + kv("user", body.user) + kv("LLM provider", body.llm_provider) +
        kv("sandbox", body.sandbox) + kv("gate rules", body.gate_rules) +
        kv("runtime queue", q) + kv("readiness ceiling", body.readiness_ceiling) +
        kv("auto-publication", body.auto_publication ? "ON (!)" : "OFF"));
    },
  },

  "Research Workspace": workspaceView,

  "Research Programs": {
    render: async () => {
      const { body } = await get("/portal/api/programs");
      if (!body.length) return panel("Research Programs",
        "<p class='loading'>none yet — create one in the Research Workspace.</p>");
      return panel("Research Programs", table("Programs", ["Mission", "Status", "Domains"],
        body.map((p) => [p.mission, p.status, (p.domains || []).join(",")])));
    },
  },

  "Reliability": {
    render: async () => {
      const { body } = await get("/portal/api/reliability");
      const dims = Object.entries(body.card.dimensions).map(([n, d]) =>
        kv(n, d.measurement === null ? "n/a" : d.measurement)).join("");
      const rt = body.red_team;
      return panel("Reliability card (no single trust score)", dims) +
        panel("Red team", kv("detected", `${rt.detected}/${rt.n}`) +
          kv("missed", (rt.missed || []).join(",") || "none"));
    },
  },

  "Red Team": {
    render: async () => {
      const { body } = await get("/portal/api/reliability");
      const rt = body.red_team;
      const rows = Object.entries(rt.by_category).map(([c, s]) =>
        [c, `${s.detected}/${s.total}`, s.detected === s.total ? "all" : "GAP"]);
      return panel("Adversarial test matrix", table("Categories",
        ["Category", "Detected", "Status"], rows));
    },
  },

  "Runtime": {
    render: async () => {
      const { body } = await get("/portal/api/runtime");
      return panel("Persistent runtime", kv("tasks", body.n_tasks) +
        Object.entries(body.by_status || {}).map(([k, v]) => kv(k, v)).join("")) +
        panel("Note", "<p class='muted'>Worker tokens and secrets are never shown here.</p>");
    },
  },

  "Self-Evaluation": {
    render: async () => {
      const { body } = await get("/portal/api/evaluation");
      const bm = table("Benchmarks", ["Benchmark", "Status"],
        Object.entries(body.benchmarks).map(([b, v]) => [b, v.passed ? "pass" : "FAIL"]));
      const caps = table("Capabilities", ["Capability", "Status"],
        body.capabilities.map((c) => [c.name, c.status]));
      return panel("Verdict: " + body.verdict,
        kv("version", body.version) + kv("prompts", `${body.prompts.passed}/${body.prompts.n}`) +
        kv("regression", body.regression.has_regression ? "REGRESSED" : "none")) +
        panel("Benchmark status", bm) + panel("Capability registry", caps) +
        `<p class="loading">${esc(body.note)}</p>`;
    },
  },

  "Review": {
    render: async () => {
      const { body } = await get("/portal/api/review");
      return panel("Human Scientific Review Gauntlet",
        kv("cases passed", `${body.passed}/${body.n}`) + kv("all passed", body.all_passed));
    },
  },

  "Collaboration": {
    render: async () => {
      const { body } = await get("/portal/api/collaboration");
      const qs = body.review_questions.map((q) => `<li>${esc(q)}</li>`).join("");
      return panel("External Review Preparation (NOT external review)",
        kv("gauntlet", `${body.gauntlet.passed}/${body.gauntlet.n}`) +
        kv("AI authorship", body.ai_authorship_allowed ? "ALLOWED(!)" : "never")) +
        panel("Review questions", `<ul>${qs}</ul>`) +
        `<p class="loading">${esc(body.note)}</p>`;
    },
  },

  "World Model": {
    render: async () =>
      panel("World Model Explorer",
        "<div class='field'><label for='wm-pid'>Project id</label>" +
        "<input id='wm-pid' placeholder='project id'></div>" +
        "<div class='field'><label for='wm-q'>Search label</label>" +
        "<input id='wm-q' placeholder='optional search'></div>" +
        "<button class='act' id='wm-go'>Query</button>" +
        "<div id='wm-out' aria-live='polite'></div>"),
    mount: (root) => {
      let offset = 0;
      const run = async () => {
        const pid = root.querySelector("#wm-pid").value.trim();
        const q = root.querySelector("#wm-q").value.trim();
        if (!pid) return;
        const url = `/portal/api/world/${encodeURIComponent(pid)}/nodes?offset=${offset}&limit=50` +
          (q ? `&search=${encodeURIComponent(q)}` : "");
        const { ok, body } = await get(url);
        const out = root.querySelector("#wm-out");
        if (!ok) { out.innerHTML = `<p class="err">error loading nodes</p>`; return; }
        const rows = (body.items || []).map((n) => [n.label, n.type, n.confidence]);
        out.innerHTML =
          `<p class="muted">total ${esc(body.total)} · showing ${esc(body.returned)} from ${esc(body.offset)}</p>` +
          table("World Model nodes (paginated)", ["Label", "Type", "Confidence"], rows) +
          `<div class="pager">
             <button class="act ghost" id="wm-prev" ${body.offset === 0 ? "disabled" : ""}>Prev</button>
             <button class="act ghost" id="wm-next" ${body.has_more ? "" : "disabled"}>Next</button>
           </div>`;
        const prev = out.querySelector("#wm-prev"), next = out.querySelector("#wm-next");
        if (prev) prev.addEventListener("click", () => { offset = Math.max(0, offset - 50); run(); });
        if (next) next.addEventListener("click", () => { offset += 50; run(); });
      };
      root.querySelector("#wm-go").addEventListener("click", () => { offset = 0; run(); });
    },
  },

  "Decision Center": {
    render: async () => {
      const { body } = await get("/portal/api/decision");
      const rows = ["context", "uncertainty", "cost", "risk", "recommendation", "why_not_execute"]
        .map((k) => kv(k, body[k])).join("");
      const ev = "<p><b>Evidence:</b> " + body.evidence.map(esc).join("; ") + "</p>";
      const ce = "<p><b>Counter-evidence:</b> " + body.counter_evidence.map(esc).join("; ") + "</p>";
      const btns = body.actions.map((a) =>
        `<button class="act ${a === "REJECT" ? "danger" : "ghost"}" data-decision="${esc(a)}">${esc(a)}</button>`).join(" ");
      return panel("Decision: " + body.question, ev + ce + rows +
        "<div class='field'><label for='dec-reason'>Reason (required to APPROVE)</label>" +
        "<input id='dec-reason'></div>" + btns + "<div id='dec-out' aria-live='polite'></div>");
    },
    mount: (root) => {
      root.querySelectorAll("[data-decision]").forEach((b) =>
        b.addEventListener("click", async () => {
          const decision = b.getAttribute("data-decision");
          const reason = root.querySelector("#dec-reason").value;
          const { ok, status, body } = await post("/portal/api/decision", { decision, reason });
          root.querySelector("#dec-out").innerHTML = ok
            ? `<p>${pill("recorded " + body.recorded, "ok")} <span class="muted">${esc(body.note)}</span></p>`
            : `<p class="err">blocked (${esc(status)}): ${esc(body.detail)}</p>`;
        }));
    },
  },

  "Publication Candidates": {
    render: async () => {
      const { body } = await get("/portal/api/results/cards");
      return panel("Scientific result cards",
        (body || []).map(resultCard).join("")) +
        panel("Publication policy", kv("auto-publish", "forbidden by policy") +
          kv("ceiling", "human scientific review"));
    },
  },

  "Learning Center": {
    render: async () => {
      const { body } = await get("/portal/api/learning");
      return panel("Learning Center",
        "<p>Curricula the human must demonstrate before a dossier is approved:</p>" +
        "<ul>" + (body.curricula || []).map((c) => `<li>${esc(c)}</li>`).join("") + "</ul>" +
        `<p class="loading">${esc(body.note)}</p>`);
    },
  },

  "Projects": {
    render: async () => {
      const { body } = await get("/portal/api/projects");
      if (!Array.isArray(body) || !body.length)
        return panel("Projects", "<p class='loading'>No projects yet — create one in the Research Workspace.</p>");
      const rows = body.map((p) => [
        p.title, p.domain, p.status,
        `H:${p.hypotheses} E:${p.experiments} N:${p.world_nodes} ev:${p.events}`,
        p.last_activity || "—", p.id,
      ]);
      const table = `<table><caption>All research projects (${body.length}) — click a row for detail</caption>` +
        `<thead><tr><th>Title</th><th>Domain</th><th>Status</th><th>Progress</th><th>Last activity</th><th>ID</th></tr></thead><tbody>` +
        body.map((p) =>
          `<tr class="proj-row" data-pid="${esc(p.id)}" style="cursor:pointer">` +
          `<td>${esc(p.title)}</td><td>${esc(p.domain)}</td>` +
          `<td>${pill(p.status, p.status.startsWith("empty") ? "warn" : "ok")}</td>` +
          `<td class="tag">H:${p.hypotheses} · E:${p.experiments} · WM:${p.world_nodes} · ev:${p.events}</td>` +
          `<td class="tag">${esc(p.last_activity || "—")}</td>` +
          `<td class="tag">${esc(p.id)}</td></tr>`).join("") +
        `</tbody></table>`;
      return panel("Projects", table + "<div id='proj-detail' aria-live='polite'></div>");
    },
    mount: (root) => {
      root.querySelectorAll(".proj-row").forEach((tr) =>
        tr.addEventListener("click", async () => {
          const pid = tr.getAttribute("data-pid");
          const out = root.querySelector("#proj-detail");
          out.innerHTML = "<p class='loading'>Loading…</p>";
          const { ok, body } = await get("/portal/api/projects/" + encodeURIComponent(pid));
          if (!ok) { out.innerHTML = `<p class="err">error loading project</p>`; return; }
          const hist = (body.history || []).map((h) =>
            `<div class="kv"><span>${esc(h.at)} · ${esc(h.action)} · ${esc(h.actor)}</span>` +
            `<b>${esc(h.summary || "")}</b></div>`).join("") || "<p class='muted'>no events</p>";
          const copilot = panel("🧠 Copiloto científico (Codex — ayuda de razonamiento, NO evidencia)",
            "<p class='muted'>Pregúntale a ACERO sobre este proyecto, como hablarías con un asistente científico.</p>" +
            "<textarea id='cop-msg' rows='3' style='width:100%' placeholder='p.ej.: propón hipótesis competidoras y qué datos públicos usar'></textarea>" +
            "<button class='act' id='cop-send'>Preguntar al copiloto</button>" +
            "<div id='cop-out' aria-live='polite'></div>");
          const lit = panel("🔎 Buscar literatura científica REAL (Knowledge Mesh · Crossref)",
            "<input id='lit-q' placeholder='p.ej.: cold dark matter dwarf galaxies'>" +
            "<button class='act' id='lit-go'>Buscar</button>" +
            "<div id='lit-out' aria-live='polite'></div>");
          const runner = panel("⚙️ Ejecutar ciclo de investigación real (gate-guardado)",
            "<input id='rc-q' placeholder='pregunta científica acotada'>" +
            "<button class='act' id='rc-go'>Lanzar ciclo</button>" +
            "<p class='muted' style='margin-top:.8rem'>O una verificación con DATOS PÚBLICOS REALES (Ley de Kepler, catálogo NASA):</p>" +
            "<button class='act' id='rd-go'>Verificar con datos reales</button>" +
            "<div id='rc-out' aria-live='polite'></div>");
          out.innerHTML = panel("Detail: " + body.title,
            kv("id", body.id) + kv("domain", body.domain) + kv("state", body.state) +
            kv("created", body.created_at) +
            kv("hypotheses", (body.hypotheses || []).length) +
            kv("experiments", (body.experiments || []).length) +
            kv("negative results", (body.negatives || []).length) +
            kv("world model nodes", (body.world || {}).n_nodes || 0)) +
            copilot + lit + runner + panel("History (provenance)", hist);

          const litgo = out.querySelector("#lit-go");
          litgo.addEventListener("click", async () => {
            const q = out.querySelector("#lit-q").value.trim();
            if (!q) return;
            const lo = out.querySelector("#lit-out");
            lo.innerHTML = "<p class='loading'>Buscando en fuentes reales…</p>";
            litgo.disabled = true;
            const { ok, body: b } = await get(`/portal/api/mesh/search?q=${encodeURIComponent(q)}&rows=6`);
            litgo.disabled = false;
            if (!ok) { lo.innerHTML = `<p class="err">error: ${esc((b && b.detail) || "search")}</p>`; return; }
            const rows = (b.results || []).map((it) => {
              const flag = it.integrity_status === "normal" ? "" : ` ${pill(it.integrity_status, "bad")}`;
              const lic = it.license ? ` · lic` : "";
              return `<div class="card"><a href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.title || it.doi)}</a>${flag}` +
                `<div class="tag">${esc(it.type)} · ${esc((it.authors || []).slice(0,3).join(", "))} · ${esc(it.doi)}${lic}</div></div>`;
            }).join("");
            lo.innerHTML = `<p class="muted">fuentes: ${esc((b.sources_consulted || []).join(", "))} · ${esc(b.n_results)} resultados</p>` +
              rows + `<p class="tag">${esc(b.disclaimer || "")}</p>`;
          });

          const csend = out.querySelector("#cop-send");
          csend.addEventListener("click", async () => {
            const msg = out.querySelector("#cop-msg").value.trim();
            if (!msg) return;
            const co = out.querySelector("#cop-out");
            co.innerHTML = "<p class='loading'>Pensando (Codex puede tardar hasta ~3 min)…</p>";
            csend.disabled = true;
            const { ok, body: b } = await post(`/portal/api/projects/${encodeURIComponent(pid)}/copilot`, { message: msg });
            csend.disabled = false;
            if (!ok) { co.innerHTML = `<p class="err">error: ${esc((b && b.detail) || "copilot")}</p>`; return; }
            const reply = (b.reply || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
            co.innerHTML = `<div class="card"><div style="white-space:pre-wrap">${reply}</div>` +
              `<div class="tag">${esc(b.disclaimer || "")} ${b.usage && b.usage.total_tokens ? "· tokens: " + esc(b.usage.total_tokens) : ""}</div></div>`;
          });

          const rgo = out.querySelector("#rc-go");
          rgo.addEventListener("click", async () => {
            const q = out.querySelector("#rc-q").value.trim();
            if (!q) return;
            const ro = out.querySelector("#rc-out");
            ro.innerHTML = "<p class='loading'>Ejecutando ciclo real…</p>";
            rgo.disabled = true;
            const { ok, body: b } = await post(`/portal/api/projects/${encodeURIComponent(pid)}/run-cycle`, { question: q });
            rgo.disabled = false;
            if (!ok) { ro.innerHTML = `<p class="err">error: ${esc((b && b.detail) || "run")}</p>`; return; }
            const steps = (b.steps || []).map((s) =>
              `<div class="kv"><span>${esc(s.step)}</span><b>${esc(JSON.stringify(Object.fromEntries(Object.entries(s).filter(([k]) => k !== "step"))))}</b></div>`).join("");
            ro.innerHTML = `<div class="card">${steps}<div class="tag">${esc(b.note || "")}</div></div>` +
              `<p class="muted">Recarga el detalle para ver el avance actualizado.</p>`;
          });

          const rdgo = out.querySelector("#rd-go");
          rdgo.addEventListener("click", async () => {
            const ro = out.querySelector("#rc-out");
            ro.innerHTML = "<p class='loading'>Descargando/analizando datos reales…</p>";
            rdgo.disabled = true;
            const { ok, body: b } = await post(`/portal/api/projects/${encodeURIComponent(pid)}/verify-real-data`, {});
            rdgo.disabled = false;
            if (!ok || !b.ok) { ro.innerHTML = `<p class="err">error: ${esc((b && b.detail) || (b && b.error) || "verify")}</p>`; return; }
            const rs = b.result || {};
            ro.innerHTML = `<div class="card">` +
              kv("dataset", rs.source) + kv("planetas (n)", rs.n_planets) +
              kv("exponente log(a)", (rs.fitted || {}).alpha_log_a + " (teoría 1.5)") +
              kv("exponente log(M)", (rs.fitted || {}).beta_log_M + " (teoría -0.5)") +
              kv("R²", (rs.fitted || {}).r_squared) +
              kv("Tierra: periodo predicho (1 AU)", (rs.earth_context || {}).predicted_period_yr_at_1AU_1Msun + " años (real 1.0)") +
              kv("consistente con Kepler", rs.consistent_with_kepler ? "sí" : "no") +
              `<div class="tag">${esc(rs.claim || "")}</div></div>` +
              `<p class="muted">Experimento REAL registrado (${esc(b.experiment_id || "")}). Recarga para ver el avance.</p>`;
          });
        }));
    },
  },

  "Settings": {
    render: async () => panel("Settings",
      "<p>Local-first. No secrets are shown here.</p>" +
      kv("auto-publication", "forbidden by policy") + kv("reviewer", "must be a human (not ACERO)")),
  },
};
