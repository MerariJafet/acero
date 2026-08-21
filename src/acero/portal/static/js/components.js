"use strict";
// Pure render helpers. All user/text values pass through esc() — no innerHTML of
// untrusted data without escaping, no eval, no dynamic script.
export const esc = (s) =>
  String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

export const kv = (k, v) => `<div class="kv"><span>${esc(k)}</span><b>${esc(v)}</b></div>`;
export const panel = (title, inner) => `<section class="panel"><h2>${esc(title)}</h2>${inner}</section>`;
export const pill = (text, cls = "") => `<span class="pill ${cls}">${esc(text)}</span>`;

// "¿Qué hace esto?" -- un (?) que, al pulsarlo, muestra una explicación corta cerca
// del control. El manejador global vive una sola vez en app.js (boot()).
export const helpIcon = (text) =>
  `<button type="button" class="help-ic" data-help="${esc(text)}" aria-label="Qué hace esto">?</button>`;

// tiempo relativo corto para "última decisión hace 4m" -- nunca timestamps crudos
// en un panel que se supone que se lee de un vistazo.
export function relTime(iso) {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const sec = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (sec < 60) return "hace instantes";
  const min = Math.round(sec / 60);
  if (min < 60) return `hace ${min}m`;
  const h = Math.round(min / 60);
  if (h < 24) return `hace ${h}h`;
  return `hace ${Math.round(h / 24)}d`;
}

export function table(caption, columns, rows) {
  const head = columns.map((c) => `<th scope="col">${esc(c)}</th>`).join("");
  const body = rows.map((row) =>
    `<tr>${row.map((cell) => `<td>${esc(cell)}</td>`).join("")}</tr>`).join("");
  return `<table><caption>${esc(caption)}</caption><thead><tr>${head}</tr></thead>` +
    `<tbody>${body}</tbody></table>`;
}

export function resultCard(c) {
  const list = (label, arr) =>
    `<div class="tag">${esc(label)}: ${(arr || []).map(esc).join("; ") || "—"}</div>`;
  return `<article class="card">
    <h3>${esc(c.title)}</h3>
    <div>${pill(c.epistemic_level, "warn")} ${pill(c.gate, "ok")} <span class="tag">${esc(c.domain)} · ${esc(c.date)}</span></div>
    ${list("Evidence", c.evidence)}
    ${list("Counter-evidence", c.counter_evidence)}
    <div class="tag">Calibration: ${esc(c.calibration)}</div>
    <div class="tag">Reproducibility: ${esc(c.reproducibility)}</div>
    ${list("Allowed claims", c.allowed_claims)}
    ${list("PROHIBITED claims", c.prohibited_claims)}
    ${list("Limitations", c.limitations)}
  </article>`;
}
