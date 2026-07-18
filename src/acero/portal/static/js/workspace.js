"use strict";
import { post } from "./api.js";
import { esc, panel, pill } from "./components.js";

// The Research Workspace guided flow. Every action calls a protected /workspace
// endpoint (which routes through gate-guarded services). State is kept locally to
// chain steps; no UI code writes to persistence directly.
const state = {};

function stepBox(id, title, inner) {
  return `<div class="step" id="${id}"><h3>${esc(title)}</h3>${inner}</div>`;
}

export const workspaceView = {
  render: async () => panel("Research Workspace",
    "<div class='wsflow'>" +
    stepBox("s-program", "1. Program",
      "<input id='ws-mission' placeholder='mission'>" +
      "<button class='act' id='ws-mk-program'>Create program</button>" +
      "<div id='ws-program-out' class='tag'></div>") +
    stepBox("s-project", "2. Project",
      "<input id='ws-title' placeholder='project title'>" +
      "<button class='act' id='ws-mk-project'>Create project</button>" +
      "<div id='ws-project-out' class='tag'></div>") +
    stepBox("s-question", "3. Question",
      "<input id='ws-question' placeholder='research question'>" +
      "<button class='act' id='ws-mk-question'>Add question</button>" +
      "<div id='ws-question-out' class='tag'></div>") +
    stepBox("s-hyp", "4. Hypotheses → approve",
      "<button class='act' id='ws-gen-hyp'>Generate hypotheses</button>" +
      "<div id='ws-hyp-out'></div>") +
    stepBox("s-exp", "5. Experiment + gate",
      "<button class='act' id='ws-run-exp' disabled>Run experiment</button>" +
      "<button class='act ghost' id='ws-gate-bad'>Gate an INVALID artifact</button>" +
      "<div id='ws-exp-out'></div>") +
    stepBox("s-wm", "6. World Model + dossier",
      "<button class='act' id='ws-wm'>Update World Model</button>" +
      "<button class='act' id='ws-dossier'>Generate dossier</button>" +
      "<div id='ws-final-out'></div>") +
    "</div>"),

  mount: (root) => {
    const out = (id, html) => { root.querySelector(id).innerHTML = html; };

    root.querySelector("#ws-mk-program").addEventListener("click", async () => {
      const mission = root.querySelector("#ws-mission").value.trim();
      const { ok, body } = await post("/portal/api/workspace/program", { mission });
      if (!ok) return out("#ws-program-out", `<span class="err">${esc(body.detail)}</span>`);
      state.program = body.id;
      out("#ws-program-out", `${pill("program " + body.id, "ok")}`);
    });

    root.querySelector("#ws-mk-project").addEventListener("click", async () => {
      const title = root.querySelector("#ws-title").value.trim();
      const { ok, body } = await post("/portal/api/workspace/project",
        { title, program_id: state.program || null });
      if (!ok) return out("#ws-project-out", `<span class="err">${esc(body.detail)}</span>`);
      state.project = body.id;
      out("#ws-project-out", `${pill("project " + body.id, "ok")}`);
    });

    root.querySelector("#ws-mk-question").addEventListener("click", async () => {
      const text = root.querySelector("#ws-question").value.trim();
      if (!state.program) return out("#ws-question-out", `<span class="err">create a program first</span>`);
      const { ok, body } = await post("/portal/api/workspace/question",
        { program_id: state.program, text });
      if (!ok) return out("#ws-question-out", `<span class="err">${esc(body.detail)}</span>`);
      state.question = text;
      out("#ws-question-out", `${pill("question added", "ok")}`);
    });

    root.querySelector("#ws-gen-hyp").addEventListener("click", async () => {
      if (!state.project) return out("#ws-hyp-out", `<span class="err">create a project first</span>`);
      const { ok, body } = await post("/portal/api/workspace/hypotheses",
        { project_id: state.project, question: state.question || "default question" });
      if (!ok) return out("#ws-hyp-out", `<span class="err">${esc(body.detail)}</span>`);
      out("#ws-hyp-out", body.map((h) =>
        `<div class="kv"><span>${esc(h.tag)}: ${esc(h.description)}</span>` +
        `<button class="act ghost" data-approve="${esc(h.id)}">Approve</button></div>`).join(""));
      root.querySelectorAll("[data-approve]").forEach((btn) =>
        btn.addEventListener("click", async () => {
          const hid = btn.getAttribute("data-approve");
          const { ok: aok, body: ab } = await post("/portal/api/workspace/approve",
            { hypothesis_id: hid, reason: "reviewed synthetic hypothesis for testing" });
          if (!aok) return;
          state.hypothesis = hid;
          btn.textContent = "APPROVED"; btn.disabled = true;
          root.querySelector("#ws-run-exp").disabled = false;
        }));
    });

    root.querySelector("#ws-run-exp").addEventListener("click", async () => {
      const { ok, body } = await post("/portal/api/workspace/experiment",
        { project_id: state.project, hypothesis_id: state.hypothesis });
      if (!ok) return out("#ws-exp-out", `<span class="err">${esc(body.detail)}</span>`);
      const gate = await post("/portal/api/workspace/gate", { artifact: body });
      const g = gate.body.outcome;
      out("#ws-exp-out",
        `<div class="tag">experiment ${esc(body.id)} · R²=${esc(body.r2)}</div>` +
        `<div>gate: ${pill(g, g === "BLOCKED" ? "bad" : "ok")}</div>`);
    });

    root.querySelector("#ws-gate-bad").addEventListener("click", async () => {
      // An invalid artifact must be BLOCKED by the gate — the UI shows the block.
      const bad = { dimensions_valid: false, train_test_disjoint: false,
        reproduced: false, codex_treated_as_evidence: true };
      const { body } = await post("/portal/api/workspace/gate", { artifact: bad });
      const blocked = body.outcome === "BLOCKED";
      out("#ws-exp-out",
        `<div id="gate-block">gate on invalid artifact: ${pill(body.outcome, blocked ? "bad" : "ok")} ` +
        `${blocked ? "(correctly blocked)" : "(NOT blocked — bug!)"}</div>`);
    });

    root.querySelector("#ws-wm").addEventListener("click", async () => {
      if (!state.project) return out("#ws-final-out", `<span class="err">create a project first</span>`);
      const { ok, body } = await post("/portal/api/workspace/world-update",
        { project_id: state.project, label: "synthetic claim under review" });
      if (!ok) return out("#ws-final-out", `<span class="err">${esc(body.detail)}</span>`);
      out("#ws-final-out", `${pill("world node " + body.node_id, "ok")}`);
    });

    root.querySelector("#ws-dossier").addEventListener("click", async () => {
      if (!state.project) return out("#ws-final-out", `<span class="err">create a project first</span>`);
      const { ok, body } = await post("/portal/api/workspace/dossier",
        { project_id: state.project, claim: "synthetic structure recovered (not a discovery)" });
      if (!ok) return out("#ws-final-out", `<span class="err">${esc(body.detail)}</span>`);
      out("#ws-final-out",
        `<div id="dossier-done">${pill("dossier " + body.id, "ok")} ` +
        `readiness=${esc(body.readiness)} · auto-publish=${body.can_publish_automatically ? "ON(!)" : "OFF"}</div>`);
    });
  },
};
