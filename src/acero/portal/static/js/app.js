"use strict";
import { get, post, setCsrf } from "./api.js";
import { esc } from "./components.js";
import { VIEWS } from "./views.js";

const $ = (s) => document.querySelector(s);
let current = "Overview";

async function renderView(name) {
  if (!VIEWS[name]) return;
  current = name;
  document.querySelectorAll("#nav button").forEach((b) =>
    b.setAttribute("aria-current", b.dataset.view === name ? "page" : "false"));
  document.querySelectorAll("#nav button").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === name));
  const view = $("#view");
  view.setAttribute("aria-busy", "true");
  view.innerHTML = "<p class='loading'>Loading…</p>";
  try {
    const v = VIEWS[name];
    view.innerHTML = await v.render();
    if (v.mount) v.mount(view);
  } catch (e) {
    view.innerHTML = `<p class="err">failed to load ${esc(name)}: ${esc(e.message)}</p>`;
  }
  view.setAttribute("aria-busy", "false");
}

async function buildNav() {
  const { body } = await get("/portal/api/overview");
  $("#version").textContent = "v" + (body.version || "?");
  $("#whoami").textContent = body.user ? `signed in as ${body.user}` : "";
  // Project-centric nav: Proyectos is THE primary entry; everything else is
  // secondary system tooling (still available, visually de-emphasized).
  const sections = (body.sections || Object.keys(VIEWS)).filter((s) => s !== "Projects");
  $("#nav").innerHTML =
    `<button class="primary-nav" data-view="Projects">📁 Proyectos</button>` +
    `<div class="nav-label">Sistema</div>` +
    sections.map((s) =>
      `<button class="sys" data-view="${esc(s)}" ${VIEWS[s] ? "" : "disabled"}>${esc(s)}</button>`).join("");
  document.querySelectorAll("#nav button").forEach((b) =>
    b.addEventListener("click", () => VIEWS[b.dataset.view] && renderView(b.dataset.view)));
}

function showApp() { $("#login").hidden = true; $("#app").hidden = false; }
function showLogin() { $("#app").hidden = true; $("#login").hidden = false; }

async function enterApp() {
  showApp();
  await buildNav();
  await renderView("Projects");   // the project IS the center of the app
}

async function doLogin(ev) {
  ev.preventDefault();
  const username = $("#u").value, password = $("#p").value;
  const { ok, status, body } = await post("/portal/api/login", { username, password });
  const err = $("#login-error");
  if (!ok) {
    err.textContent = status === 429 ? "Too many attempts. Try again later."
      : "Invalid credentials.";
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
  // in-app navigation events (e.g. "← Proyectos" from a project workspace)
  window.addEventListener("acero:navigate", (e) => renderView(e.detail));
  // resume an existing session if the cookie is still valid
  const { ok, body } = await get("/portal/api/session");
  if (ok && body.csrf) { setCsrf(body.csrf); await enterApp(); }
  else showLogin();
}

boot();
