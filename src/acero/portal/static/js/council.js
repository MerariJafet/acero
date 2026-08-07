// El Consejo — the 14 scientist-personas as a live dashboard view.
// Fetches /portal/api/projects/{pid}/council and renders vector portraits, a filling
// "council clock", stage-grouped cards with progress rings, and a click-to-detail drawer.

const STATUS = { good: "#54c08a", warn: "#e0a96d", new: "#5b8def", weak: "#e0736f" };
const STATUS_LBL = { good: "sólido", warn: "mejorable", new: "nuevo", weak: "débil" };
const TASK = { done: ["#54c08a", "hecho"], doing: ["#e0a96d", "en curso"], todo: ["#5f6d88", "pendiente"] };

function injectStyles() {
  if (document.getElementById("council-styles")) return;
  const s = document.createElement("style");
  s.id = "council-styles";
  s.textContent = `
  .cv{--ink:#0d121e;--panel:#151d2e;--panel2:#1b2438;--line:#28324a;--star:#eef2fb;
    --dim:#93a1bd;--faint:#5f6d88;--brass:#e0a96d;--brass2:#c8863c;
    --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
    --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
    background:radial-gradient(1200px 560px at 50% -12%,#1a2740 0,transparent 60%),
      radial-gradient(800px 460px at 88% 12%,rgba(224,169,109,.06),transparent 55%),var(--ink);
    color:var(--star);border-radius:16px;padding:22px clamp(12px,3vw,30px) 40px;position:relative;overflow:hidden}
  .cv *{box-sizing:border-box}
  .cv-stars{position:absolute;inset:0;pointer-events:none;opacity:.5}
  .cv-top{position:relative;z-index:1;display:flex;flex-wrap:wrap;align-items:flex-end;
    justify-content:space-between;gap:14px;margin-bottom:22px}
  .cv-eyebrow{font-family:var(--mono);font-size:10px;letter-spacing:.28em;text-transform:uppercase;color:var(--brass)}
  .cv h2{font-family:var(--serif);font-weight:600;font-size:clamp(26px,4vw,42px);margin:.1em 0 0;letter-spacing:.01em}
  .cv h2 em{font-style:italic;color:var(--brass)}
  .cv-tag{color:var(--dim);font-size:13px;max-width:54ch;line-height:1.5;margin-top:4px}
  .cv-back{background:var(--panel);border:1px solid var(--line);color:var(--dim);border-radius:10px;
    padding:9px 14px;font-size:13px;cursor:pointer}
  .cv-back:hover{color:var(--star);border-color:var(--brass2)}
  .cv-stage{position:relative;z-index:1;display:grid;grid-template-columns:minmax(280px,360px) 1fr;gap:24px;align-items:start}
  @media(max-width:900px){.cv-stage{grid-template-columns:1fr}}
  .cv-clockcard{background:linear-gradient(180deg,var(--panel),#121a29);border:1px solid var(--line);
    border-radius:18px;padding:20px;position:sticky;top:12px}
  .cv-cw{position:relative;width:100%;aspect-ratio:1;max-width:320px;margin:0 auto}
  .cv-cw svg{width:100%;height:100%;transform:rotate(-90deg)}
  .cv-cc{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
  .cv-cpct{font-family:var(--serif);font-size:44px;font-weight:600;line-height:1;font-variant-numeric:tabular-nums}
  .cv-clbl{font-family:var(--mono);font-size:9px;letter-spacing:.22em;text-transform:uppercase;color:var(--faint)}
  .cv-csel{color:var(--brass);font-size:13px;min-height:16px;margin-top:2px}
  .cv-legend{display:flex;flex-wrap:wrap;gap:8px 14px;margin-top:16px;justify-content:center}
  .cv-legend span{display:inline-flex;align-items:center;gap:6px;font-size:11px;color:var(--dim)}
  .cv-dot{width:9px;height:9px;border-radius:50%}
  .cv-council{display:flex;flex-direction:column;gap:20px}
  .cv-band{display:flex;flex-direction:column;gap:11px}
  .cv-bh{display:flex;align-items:baseline;gap:12px}
  .cv-bn{font-family:var(--mono);font-size:10px;letter-spacing:.24em;text-transform:uppercase;color:var(--brass)}
  .cv-bl{flex:1;height:1px;background:linear-gradient(90deg,var(--line),transparent)}
  .cv-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:11px}
  .cv-card{background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:13px;display:flex;
    gap:12px;align-items:center;cursor:pointer;position:relative;overflow:hidden;transition:transform .12s,border-color .12s,box-shadow .12s}
  .cv-card:hover{transform:translateY(-2px);border-color:var(--brass2);box-shadow:0 10px 28px rgba(0,0,0,.35)}
  .cv-card:focus-visible{outline:2px solid var(--brass);outline-offset:2px}
  .cv-card.on{border-color:var(--brass);box-shadow:0 0 0 1px var(--brass) inset}
  .cv-face{width:56px;height:56px;flex:0 0 56px}
  .cv-who{min-width:0;flex:1}
  .cv-nm{font-family:var(--serif);font-size:18px;font-weight:600;line-height:1.05}
  .cv-rl{color:var(--dim);font-size:11px;line-height:1.3;margin-top:2px;display:-webkit-box;
    -webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .cv-ring{position:relative;width:44px;height:44px;flex:0 0 44px}
  .cv-ring svg{width:100%;height:100%;transform:rotate(-90deg)}
  .cv-ring b{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
    font-family:var(--mono);font-size:12px;font-variant-numeric:tabular-nums}
  .cv-pill{position:absolute;top:9px;right:9px;font-family:var(--mono);font-size:8.5px;letter-spacing:.08em;
    text-transform:uppercase;padding:2px 6px;border-radius:20px}
  .cv-scrim{position:fixed;inset:0;background:rgba(6,9,15,.6);backdrop-filter:blur(3px);opacity:0;
    pointer-events:none;transition:opacity .2s;z-index:60}
  .cv-scrim.open{opacity:1;pointer-events:auto}
  .cv-drawer{position:fixed;top:0;right:0;height:100%;width:min(430px,94vw);z-index:61;
    background:linear-gradient(180deg,#1b2438,#121a29);border-left:1px solid #28324a;color:#eef2fb;
    transform:translateX(100%);transition:transform .28s cubic-bezier(.2,.7,.2,1);display:flex;flex-direction:column;overflow:auto;
    font-family:system-ui,sans-serif}
  .cv-drawer.open{transform:none}
  .cv-dh{display:flex;gap:15px;align-items:center;padding:20px 20px 15px;border-bottom:1px solid #28324a}
  .cv-df{width:72px;height:72px;flex:0 0 72px}
  .cv-dn{font-family:var(--serif,serif);font-size:25px;font-weight:600;line-height:1}
  .cv-dr{color:#e0a96d;font-size:12px;font-family:var(--mono,monospace);margin-top:5px}
  .cv-dm{color:#5f6d88;font-family:var(--mono,monospace);font-size:11px;margin-top:3px}
  .cv-db{padding:16px 20px 28px;display:flex;flex-direction:column;gap:16px}
  .cv-dsum{font-size:14px;line-height:1.55;color:#cfd8ea}
  .cv-flow{display:flex;gap:10px}
  .cv-flow div{flex:1;background:#151d2e;border:1px solid #28324a;border-radius:10px;padding:9px}
  .cv-k{font-family:var(--mono,monospace);font-size:8.5px;letter-spacing:.16em;text-transform:uppercase;color:#5f6d88;margin-bottom:3px}
  .cv-v{font-size:13px}
  .cv-st{font-family:var(--mono,monospace);font-size:10px;letter-spacing:.22em;text-transform:uppercase;color:#e0a96d;margin-bottom:4px}
  .cv-task{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #28324a}
  .cv-task:last-child{border-bottom:0}
  .cv-tb{width:8px;height:8px;border-radius:50%;flex:0 0 8px}
  .cv-tt{flex:1;font-size:13px}.cv-ts{font-family:var(--mono,monospace);font-size:10px;color:#93a1bd;text-transform:uppercase}
  .cv-verd{display:flex;align-items:center;gap:8px;font-size:12.5px;padding:5px 0}
  .cv-vchip{font-family:var(--mono,monospace);font-size:9px;text-transform:uppercase;padding:2px 7px;border-radius:20px}
  .cv-close{margin-left:auto;background:#151d2e;border:1px solid #28324a;color:#93a1bd;width:34px;height:34px;border-radius:9px;cursor:pointer}
  .cv-src{font-family:var(--mono,monospace);font-size:9px;color:#5f6d88;margin-top:2px}
  @media(prefers-reduced-motion:reduce){.cv *{transition:none!important}}`;
  document.head.appendChild(s);
}

function face(p, S = 56) {
  const f = p.face || {};
  const sk = { 1: "#e7d3b3", 2: "#dcc0a0", 3: "#ead9c1" }[f.skin || 1];
  const hair = f.hairc || "#cbb89c", brass = "#e0a96d", ink = "#20293c";
  const R = S / 2, cx = R, cy = R, id = p.id;
  let g = `<svg viewBox="0 0 ${S} ${S}" width="${S}" height="${S}">`;
  g += `<defs><clipPath id="cf${id}"><circle cx="${cx}" cy="${cy}" r="${R - 2}"/></clipPath></defs>`;
  g += `<circle cx="${cx}" cy="${cy}" r="${R - 1}" fill="#0f1626"/><g clip-path="url(#cf${id})">`;
  g += `<rect width="${S}" height="${S}" fill="#101a2c"/>`;
  g += `<ellipse cx="${cx}" cy="${S + 6}" rx="${R * 0.9}" ry="${R * 0.7}" fill="${f.robe || "#2a3550"}"/>`;
  g += `<rect x="${cx - 6}" y="${cy + 6}" width="12" height="12" fill="${sk}"/>`;
  g += `<ellipse cx="${cx}" cy="${cy - 1}" rx="${R * 0.52}" ry="${R * 0.62}" fill="${sk}"/>`;
  const H = f.hair;
  if (H === "long") g += `<path d="M${cx - R * 0.6} ${cy + 8} Q${cx - R * 0.65} ${cy - R * 0.7} ${cx} ${cy - R * 0.78} Q${cx + R * 0.65} ${cy - R * 0.7} ${cx + R * 0.6} ${cy + 8} Q${cx + R * 0.3} ${cy - R * 0.2} ${cx} ${cy - R * 0.28} Q${cx - R * 0.3} ${cy - R * 0.2} ${cx - R * 0.6} ${cy + 8}Z" fill="${hair}"/>`;
  else if (H === "wild") g += `<path d="M${cx - R * 0.62} ${cy - 2} Q${cx - R * 0.8} ${cy - R * 0.9} ${cx - R * 0.2} ${cy - R * 0.7} Q${cx} ${cy - R} ${cx + R * 0.2} ${cy - R * 0.7} Q${cx + R * 0.8} ${cy - R * 0.9} ${cx + R * 0.62} ${cy - 2} Q${cx + R * 0.3} ${cy - R * 0.42} ${cx} ${cy - R * 0.48} Q${cx - R * 0.3} ${cy - R * 0.42} ${cx - R * 0.62} ${cy - 2}Z" fill="${hair}"/>`;
  else if (H === "bun") { g += `<circle cx="${cx}" cy="${cy - R * 0.72}" r="${R * 0.2}" fill="${hair}"/><path d="M${cx - R * 0.52} ${cy} Q${cx - R * 0.5} ${cy - R * 0.6} ${cx} ${cy - R * 0.6} Q${cx + R * 0.5} ${cy - R * 0.6} ${cx + R * 0.52} ${cy} Q${cx} ${cy - R * 0.42} ${cx - R * 0.52} ${cy}Z" fill="${hair}"/>`; }
  else if (H === "short") g += `<path d="M${cx - R * 0.53} ${cy - R * 0.1} Q${cx - R * 0.55} ${cy - R * 0.72} ${cx} ${cy - R * 0.72} Q${cx + R * 0.55} ${cy - R * 0.72} ${cx + R * 0.53} ${cy - R * 0.1} Q${cx + R * 0.3} ${cy - R * 0.5} ${cx} ${cy - R * 0.5} Q${cx - R * 0.3} ${cy - R * 0.5} ${cx - R * 0.53} ${cy - R * 0.1}Z" fill="${hair}"/>`;
  else if (H === "recede") g += `<path d="M${cx - R * 0.5} ${cy - R * 0.05} Q${cx - R * 0.5} ${cy - R * 0.55} ${cx - R * 0.15} ${cy - R * 0.5} Q${cx - R * 0.3} ${cy - R * 0.2} ${cx - R * 0.5} ${cy - R * 0.05}Z M${cx + R * 0.5} ${cy - R * 0.05} Q${cx + R * 0.5} ${cy - R * 0.55} ${cx + R * 0.15} ${cy - R * 0.5} Q${cx + R * 0.3} ${cy - R * 0.2} ${cx + R * 0.5} ${cy - R * 0.05}Z" fill="${hair}"/>`;
  if (f.beard === "full") g += `<path d="M${cx - R * 0.4} ${cy} Q${cx - R * 0.44} ${cy + R * 0.55} ${cx} ${cy + R * 0.68} Q${cx + R * 0.44} ${cy + R * 0.55} ${cx + R * 0.4} ${cy} Q${cx} ${cy + R * 0.3} ${cx - R * 0.4} ${cy}Z" fill="${hair}"/>`;
  else if (f.beard === "mous") g += `<path d="M${cx - R * 0.24} ${cy + R * 0.26} Q${cx} ${cy + R * 0.34} ${cx + R * 0.24} ${cy + R * 0.26}" stroke="${hair}" stroke-width="3.2" fill="none" stroke-linecap="round"/>`;
  const ey = cy - R * 0.04;
  g += `<circle cx="${cx - R * 0.2}" cy="${ey}" r="1.7" fill="${ink}"/><circle cx="${cx + R * 0.2}" cy="${ey}" r="1.7" fill="${ink}"/>`;
  g += `<path d="M${cx - R * 0.3} ${ey - R * 0.14} q${R * 0.1} -${R * 0.06} ${R * 0.2} 0 M${cx + R * 0.1} ${ey - R * 0.14} q${R * 0.1} -${R * 0.06} ${R * 0.2} 0" stroke="${ink}" stroke-width="1.1" fill="none" opacity=".7"/>`;
  if (f.nose === "metal") g += `<path d="M${cx - 2} ${ey + 2} L${cx + 2} ${ey + 2} L${cx + 1} ${cy + R * 0.2} L${cx - 1} ${cy + R * 0.2}Z" fill="${brass}"/>`;
  else g += `<path d="M${cx} ${ey + 1} L${cx - 2} ${cy + R * 0.16} Q${cx} ${cy + R * 0.22} ${cx + 2} ${cy + R * 0.16}" stroke="${ink}" stroke-width="1" fill="none" opacity=".55"/>`;
  if (f.beard !== "full") g += `<path d="M${cx - R * 0.14} ${cy + R * 0.34} Q${cx} ${cy + R * 0.4} ${cx + R * 0.14} ${cy + R * 0.34}" stroke="${ink}" stroke-width="1.3" fill="none" stroke-linecap="round" opacity=".7"/>`;
  if (f.glasses) g += `<g stroke="${brass}" stroke-width="1.2" fill="none"><circle cx="${cx - R * 0.2}" cy="${ey}" r="${R * 0.16}"/><circle cx="${cx + R * 0.2}" cy="${ey}" r="${R * 0.16}"/><line x1="${cx - R * 0.04}" y1="${ey}" x2="${cx + R * 0.04}" y2="${ey}"/></g>`;
  if (f.hat === "laurel") g += `<path d="M${cx - R * 0.55} ${cy - R * 0.3} Q${cx - R * 0.75} ${cy - R * 0.7} ${cx - R * 0.35} ${cy - R * 0.75} M${cx + R * 0.55} ${cy - R * 0.3} Q${cx + R * 0.75} ${cy - R * 0.7} ${cx + R * 0.35} ${cy - R * 0.75}" stroke="${brass}" stroke-width="2.4" fill="none" stroke-linecap="round"/>`;
  if (f.hat === "ruff") g += `<path d="M${cx - R * 0.5} ${cy + R * 0.5} q${R * 0.12} ${R * 0.14} ${R * 0.25} 0 q${R * 0.12} ${R * 0.14} ${R * 0.25} 0 q${R * 0.12} ${R * 0.14} ${R * 0.25} 0 q${R * 0.12} ${R * 0.14} ${R * 0.25} 0" stroke="#e9e3d6" stroke-width="3" fill="none"/>`;
  g += `</g><circle cx="${cx}" cy="${cy}" r="${R - 1}" fill="none" stroke="${f.accent || brass}" stroke-width="1.5" opacity=".8"/></svg>`;
  return g;
}

function ring(pct, color, S = 44) {
  const r = S / 2 - 4, c = 2 * Math.PI * r, off = c * (1 - pct / 100);
  return `<svg viewBox="0 0 ${S} ${S}"><circle cx="${S / 2}" cy="${S / 2}" r="${r}" fill="none" stroke="#28324a" stroke-width="4"/><circle cx="${S / 2}" cy="${S / 2}" r="${r}" fill="none" stroke="${color}" stroke-width="4" stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${off}"/></svg>`;
}
const pol = (cx, cy, r, d) => { const a = d * Math.PI / 180; return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) }; };
function arcPath(cx, cy, r, a0, a1, color, w, op, id) {
  const p0 = pol(cx, cy, r, a0), p1 = pol(cx, cy, r, a1), large = (a1 - a0) > 180 ? 1 : 0;
  return `<path d="M${p0.x} ${p0.y} A${r} ${r} 0 ${large} 1 ${p1.x} ${p1.y}" fill="none" stroke="${color}" stroke-width="${w}" stroke-linecap="round" opacity="${op}" ${id ? `class="cv-seg" data-id="${id}" style="cursor:pointer"` : ""}/>`;
}

export async function renderCouncil(view, pid, onBack) {
  injectStyles();
  view.innerHTML = `<div class="cv"><p style="color:#93a1bd;padding:30px">Convocando al Consejo…</p></div>`;
  let data;
  try {
    const res = await fetch(`/portal/api/projects/${encodeURIComponent(pid)}/council`,
      { headers: { "Accept": "application/json" } });
    data = await res.json();
    if (!res.ok) throw new Error(data.detail || "error");
  } catch (e) {
    view.innerHTML = `<div class="cv"><p style="color:#e0736f;padding:30px">No se pudo cargar el Consejo.</p></div>`;
    return;
  }
  const byId = Object.fromEntries(data.personas.map((p) => [p.id, p]));

  // --- clock ---
  const n = data.personas.length, gap = 2.2, seg = 360 / n, R = 86, cx = 100, cy = 100, sw = 20;
  let clock = "";
  data.personas.forEach((p, i) => {
    const a0 = i * seg + gap / 2, a1 = (i + 1) * seg - gap / 2, pct = (p.progress || 0) / 100;
    clock += arcPath(cx, cy, R, a0, a1, "#28324a", sw, 1);
    if (pct > 0) clock += arcPath(cx, cy, R, a0, a0 + (a1 - a0) * pct, STATUS[p.status], sw, 1, p.id);
  });
  // tick marks
  let ticks = "";
  for (let i = 0; i < n; i++) { const a = i * seg, o = pol(cx, cy, R + 12, a), q = pol(cx, cy, R + 15, a); ticks += `<line x1="${o.x}" y1="${o.y}" x2="${q.x}" y2="${q.y}" stroke="#3a4661" stroke-width="1"/>`; }

  // --- bands / cards ---
  const bands = data.stages.map((st) => {
    const cards = st.ids.map((id) => {
      const p = byId[id]; if (!p) return "";
      const col = STATUS[p.status];
      return `<div class="cv-card" tabindex="0" role="button" data-id="${id}" aria-label="${p.name}">
        <span class="cv-pill" style="color:${col};background:${col}22">${STATUS_LBL[p.status]}</span>
        <div class="cv-face">${face(p)}</div>
        <div class="cv-who"><div class="cv-nm">${p.name}</div><div class="cv-rl">${p.role}</div></div>
        <div class="cv-ring">${ring(p.progress, col)}<b>${p.progress}</b></div></div>`;
    }).join("");
    return `<div class="cv-band"><div class="cv-bh"><span class="cv-bn">${st.name}</span><span class="cv-bl"></span></div><div class="cv-cards">${cards}</div></div>`;
  }).join("");

  view.innerHTML = `<div class="cv"><canvas class="cv-stars"></canvas>
    <div class="cv-top">
      <div><div class="cv-eyebrow">ACERO · consejo de investigación</div>
        <h2>El <em>Consejo</em></h2>
        <div class="cv-tag">Catorce mentes, cada una un flujo real. Se pasan el trabajo en cadena; el reloj se llena conforme avanzan en este proyecto.</div></div>
      <button class="cv-back" id="cv-back">← Dashboard</button>
    </div>
    <div class="cv-stage">
      <div class="cv-clockcard">
        <div class="cv-cw"><svg viewBox="0 0 200 200">${ticks}${clock}</svg>
          <div class="cv-cc"><div class="cv-cpct">${data.overall}%</div>
            <div class="cv-clbl">avance del consejo</div><div class="cv-csel" id="cv-sel"></div></div></div>
        <div class="cv-legend">
          <span><i class="cv-dot" style="background:#54c08a"></i>sólido</span>
          <span><i class="cv-dot" style="background:#e0a96d"></i>mejorable</span>
          <span><i class="cv-dot" style="background:#5b8def"></i>nuevo</span>
          <span><i class="cv-dot" style="background:#e0736f"></i>débil</span></div>
      </div>
      <div class="cv-council">${bands}</div>
    </div>
    <div class="cv-scrim" id="cv-scrim"></div>
    <aside class="cv-drawer" id="cv-drawer" aria-label="Detalle del personaje"></aside>
  </div>`;

  const root = view.querySelector(".cv");
  const scrim = root.querySelector("#cv-scrim"), drawer = root.querySelector("#cv-drawer");
  const selLbl = root.querySelector("#cv-sel");
  const back = root.querySelector("#cv-back");
  if (back && onBack) back.onclick = () => onBack();

  function open(id) {
    const p = byId[id]; if (!p) return;
    const col = STATUS[p.status];
    selLbl.textContent = "▸ " + p.name;
    const verds = (data.verdicts || []).map((v) => {
      const c = STATUS[v.status] || "#93a1bd";
      return `<div class="cv-verd"><span class="cv-vchip" style="color:${c};background:${c}22">${v.verdict || v.label || "—"}</span><span>${v.title || ""}</span></div>`;
    }).join("") || `<div style="color:#5f6d88;font-size:12px">Sin veredictos aún en este proyecto.</div>`;
    drawer.innerHTML = `<div class="cv-dh"><div class="cv-df">${face(p, 72)}</div>
      <div><div class="cv-dn">${p.name}</div><div class="cv-dr">${p.role}</div><div class="cv-dm">${p.module}</div></div>
      <button class="cv-close" id="cv-x" aria-label="Cerrar">✕</button></div>
      <div class="cv-db">
        <div class="cv-dsum">${p.summary}</div>
        <div class="cv-flow"><div><div class="cv-k">recibe de</div><div class="cv-v">${p.awaits}</div></div>
          <div><div class="cv-k">le pasa a</div><div class="cv-v">${p.hands_to}</div></div></div>
        <div><div class="cv-st">avance en este proyecto</div>
          <div style="display:flex;align-items:center;gap:14px;margin-top:8px">
            <div class="cv-ring" style="width:54px;height:54px;flex:0 0 54px">${ring(p.progress, col, 54)}<b style="font-size:13px">${p.progress}</b></div>
            <div style="color:#93a1bd;font-size:13px">estado <b style="color:${col}">${STATUS_LBL[p.status]}</b><div class="cv-src">avance: ${p.source === "project" ? "señal real del proyecto" : "madurez de la capacidad"}</div></div></div></div>
        <div><div class="cv-st">tareas</div>${(p.tasks || []).map((t) => `<div class="cv-task"><span class="cv-tb" style="background:${TASK[t[1]][0]}"></span><span class="cv-tt">${t[0]}</span><span class="cv-ts">${TASK[t[1]][1]}</span></div>`).join("")}</div>
        <div><div class="cv-st">veredictos del proyecto</div>${verds}</div>
      </div>`;
    drawer.classList.add("open"); scrim.classList.add("open");
    drawer.querySelector("#cv-x").onclick = close;
    root.querySelectorAll(".cv-card").forEach((c) => c.classList.toggle("on", c.dataset.id === id));
  }
  function close() {
    drawer.classList.remove("open"); scrim.classList.remove("open"); selLbl.textContent = "";
    root.querySelectorAll(".cv-card").forEach((c) => c.classList.remove("on"));
  }
  scrim.addEventListener("click", close);
  root.querySelectorAll(".cv-card").forEach((c) => {
    c.addEventListener("click", () => open(c.dataset.id));
    c.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(c.dataset.id); } });
  });
  root.querySelectorAll(".cv-seg").forEach((s) => s.addEventListener("click", () => open(s.dataset.id)));

  // starfield
  const cvs = root.querySelector(".cv-stars"), ctx = cvs.getContext("2d");
  function draw() {
    cvs.width = root.clientWidth; cvs.height = root.clientHeight;
    for (let i = 0; i < 120; i++) { const x = Math.random() * cvs.width, y = Math.random() * cvs.height * 0.55, r = Math.random() * 1.3; ctx.globalAlpha = Math.random() * 0.7 + 0.15; ctx.fillStyle = Math.random() > 0.85 ? "#e0a96d" : "#cfe0ff"; ctx.beginPath(); ctx.arc(x, y, r, 0, 6.28); ctx.fill(); }
    ctx.globalAlpha = 1;
  }
  requestAnimationFrame(draw);
}
