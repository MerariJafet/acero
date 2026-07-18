"use strict";
// API client. Holds the CSRF token in memory (never in a readable cookie) and
// attaches it to mutating requests. Talks only to same-origin /portal endpoints.
let _csrf = null;
export function setCsrf(t) { _csrf = t; }
export function getCsrf() { return _csrf; }

async function request(path, { method = "GET", body } = {}) {
  const headers = {};
  const opts = { method, headers, credentials: "same-origin" };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  if (method !== "GET" && _csrf) headers["X-CSRF-Token"] = _csrf;
  const r = await fetch(path, opts);
  let data = {};
  try { data = await r.json(); } catch (_e) { data = {}; }
  return { ok: r.ok, status: r.status, body: data };
}

export const get = (p) => request(p);
export const post = (p, body) => request(p, { method: "POST", body });
