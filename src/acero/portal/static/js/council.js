// El Consejo — 3 fases (pasteles) + rostros distintos + riel de pelotas (hipótesis en flujo).
// Fetches /portal/api/projects/{pid}/council.

const SC = { good: "#54c08a", warn: "#e0a96d", new: "#5b8def", weak: "#e0736f" };
const SL = { good: "sólido", warn: "mejorable", new: "nuevo", weak: "débil" };
const TASK = { done: ["#54c08a", "hecho"], doing: ["#e0a96d", "en curso"], todo: ["#5f6d88", "pendiente"] };
const PHC = { creativa: "#7ba7ff", investig: "#5ec7a8", critica: "#e0a96d" };

function injectStyles() {
  if (document.getElementById("council-styles")) return;
  const s = document.createElement("style"); s.id = "council-styles";
  s.textContent = `
  .cv{--ink:#0d121e;--panel:#151d2e;--panel2:#1b2438;--line:#28324a;--star:#eef2fb;--dim:#93a1bd;--faint:#5f6d88;
    --brass:#e0a96d;--serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;--mono:ui-monospace,Menlo,monospace;
    background:radial-gradient(1200px 620px at 50% -12%,#1a2740 0,transparent 60%),
      radial-gradient(800px 500px at 90% 15%,rgba(224,169,109,.06),transparent 55%),var(--ink);
    color:var(--star);border-radius:16px;padding:22px clamp(12px,3vw,32px) 40px;position:relative;overflow:hidden;
    font-family:system-ui,sans-serif}
  .cv *{box-sizing:border-box}
  .cv-stars{position:absolute;inset:0;pointer-events:none;opacity:.5}
  .cv-top{position:relative;z-index:1;display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:14px;margin-bottom:20px}
  .cv-eyebrow{font-family:var(--mono);font-size:10px;letter-spacing:.28em;text-transform:uppercase;color:var(--brass)}
  .cv h2{font-family:var(--serif);font-weight:600;font-size:clamp(26px,4vw,42px);margin:.08em 0 0}
  .cv h2 em{font-style:italic;color:var(--brass)}
  .cv-tag{color:var(--dim);font-size:13px;max-width:58ch;line-height:1.5;margin-top:4px}
  .cv-back{background:var(--panel);border:1px solid var(--line);color:var(--dim);border-radius:10px;padding:9px 14px;font-size:13px;cursor:pointer}
  .cv-back:hover{color:var(--star);border-color:#c8863c}
  .cv-board{position:relative;z-index:1;display:grid;grid-template-columns:1fr 128px;gap:18px;align-items:stretch}
  @media(max-width:820px){.cv-board{grid-template-columns:1fr}.cv-rail{display:none}}
  .cv-phases{display:flex;flex-direction:column;gap:16px}
  .cv-phase{background:linear-gradient(180deg,var(--panel),#121a29);border:1px solid var(--line);border-radius:20px;
    padding:16px 18px;display:grid;grid-template-columns:auto 1fr;gap:20px;align-items:center;position:relative;overflow:hidden}
  .cv-phase::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--pc)}
  .cv-donut{position:relative;width:120px;height:120px;flex:0 0 120px}
  .cv-donut svg{width:100%;height:100%;transform:rotate(-90deg)}
  .cv-donut .mid{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
  .cv-donut .pct{font-family:var(--serif);font-size:28px;font-weight:600;font-variant-numeric:tabular-nums;line-height:1}
  .cv-donut .n{font-family:var(--mono);font-size:8px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint);margin-top:3px}
  .cv-ph-name{font-family:var(--serif);font-size:21px;font-weight:600}
  .cv-ph-sub{color:var(--dim);font-size:12px;margin-bottom:11px}
  .cv-meds{display:flex;flex-wrap:wrap;gap:13px}
  .cv-med{display:flex;flex-direction:column;align-items:center;gap:5px;width:76px;cursor:pointer;transition:transform .12s}
  .cv-med:hover{transform:translateY(-3px)}.cv-med:focus-visible{outline:2px solid var(--brass);outline-offset:3px;border-radius:12px}
  .cv-por{position:relative;width:60px;height:60px}
  .cv-por .prg{position:absolute;inset:-4px}.cv-por .prg svg{width:100%;height:100%;transform:rotate(-90deg)}
  .cv-mnm{font-family:var(--serif);font-size:13px;font-weight:600;line-height:1;text-align:center}
  .cv-mrl{font-size:9px;color:var(--faint);text-align:center;line-height:1.15;height:22px;overflow:hidden}
  .cv-stt{position:absolute;bottom:-2px;right:-2px;width:14px;height:14px;border-radius:50%;border:2px solid #121a29}
  .cv-rail{position:relative;background:linear-gradient(180deg,var(--panel),#111826);border:1px solid var(--line);border-radius:20px;padding:12px 0}
  .cv-rail-h{font-family:var(--mono);font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--faint);text-align:center;margin-bottom:6px}
  .cv-track{position:absolute;left:50%;top:48px;bottom:14px;width:3px;transform:translateX(-50%);
    background:linear-gradient(180deg,#7ba7ff,#5ec7a8,#e0a96d);border-radius:3px;opacity:.5}
  .cv-zone{position:relative;height:calc((100% - 54px)/3);display:flex;align-items:center;justify-content:center}
  .cv-zl{position:absolute;left:7px;top:5px;font-family:var(--mono);font-size:8px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint)}
  .cv-balls{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;max-width:100px}
  .cv-ball{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-family:var(--mono);font-size:10px;font-weight:600;color:#0d121e;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.4);transition:transform .12s}
  .cv-ball:hover{transform:scale(1.14)}
  .cv-scrim{position:fixed;inset:0;background:rgba(6,9,15,.6);backdrop-filter:blur(3px);opacity:0;pointer-events:none;transition:opacity .2s;z-index:60}
  .cv-scrim.open{opacity:1;pointer-events:auto}
  .cv-drawer{position:fixed;top:0;right:0;height:100%;width:min(430px,94vw);z-index:61;background:linear-gradient(180deg,#1b2438,#121a29);
    border-left:1px solid #28324a;color:#eef2fb;transform:translateX(100%);transition:transform .28s cubic-bezier(.2,.7,.2,1);display:flex;flex-direction:column;overflow:auto}
  .cv-drawer.open{transform:none}
  .cv-dh{display:flex;gap:15px;align-items:center;padding:20px 20px 15px;border-bottom:1px solid #28324a}
  .cv-df{width:76px;height:76px;flex:0 0 76px}
  .cv-dn{font-family:var(--serif);font-size:24px;font-weight:600;line-height:1}.cv-dr{color:#e0a96d;font-family:var(--mono);font-size:12px;margin-top:5px}
  .cv-dm{color:#5f6d88;font-family:var(--mono);font-size:11px;margin-top:3px}
  .cv-db{padding:16px 20px 30px;display:flex;flex-direction:column;gap:15px}
  .cv-dsum{font-size:14px;line-height:1.55;color:#cfd8ea}
  .cv-flow{display:flex;gap:10px}.cv-flow div{flex:1;background:#151d2e;border:1px solid #28324a;border-radius:10px;padding:9px}
  .cv-k{font-family:var(--mono);font-size:8.5px;letter-spacing:.16em;text-transform:uppercase;color:#5f6d88;margin-bottom:3px}.cv-v{font-size:13px}
  .cv-st{font-family:var(--mono);font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:#e0a96d;margin-bottom:4px}
  .cv-task{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #28324a}.cv-task:last-child{border-bottom:0}
  .cv-tb{width:8px;height:8px;border-radius:50%;flex:0 0 8px}.cv-tt{flex:1;font-size:13px}.cv-ts{font-family:var(--mono);font-size:10px;color:#93a1bd;text-transform:uppercase}
  .cv-close{margin-left:auto;background:#151d2e;border:1px solid #28324a;color:#93a1bd;width:34px;height:34px;border-radius:9px;cursor:pointer}
  @media(prefers-reduced-motion:reduce){.cv *{transition:none!important}}`;
  document.head.appendChild(s);
}

// Bohr's face params (mirrors backend _FACES) so the dashboard button can draw him.
export const BOHR_FACE = { hair: "short", hairc: "#cfc7b6", skin: 2, long: 1, browc: "#8a7f6a" };

export function face(p, S = 60) {
  const f = p.face || {}, SKIN = { 1: "#e7c7a6", 2: "#d8b48c", 3: "#efdcc4", 4: "#c99b74" }[f.skin || 1];
  const hair = f.hairc || "#cbb89c", ink = "#1b2233", brass = "#e0a96d";
  const R = S / 2, cx = R, cy = R, id = p.id, A = [];
  A.push(`<svg viewBox="0 0 ${S} ${S}" width="${S}" height="${S}"><defs><clipPath id="c${id}"><circle cx="${cx}" cy="${cy}" r="${R - 2}"/></clipPath></defs>`);
  A.push(`<circle cx="${cx}" cy="${cy}" r="${R - 1}" fill="#0f1626"/><g clip-path="url(#c${id})"><rect width="${S}" height="${S}" fill="#101a2c"/>`);
  A.push(`<path d="M${cx - R * 0.7} ${S} Q${cx - R * 0.55} ${cy + R * 0.5} ${cx} ${cy + R * 0.5} Q${cx + R * 0.55} ${cy + R * 0.5} ${cx + R * 0.7} ${S}Z" fill="${f.robe || "#2a3550"}"/>`);
  A.push(`<rect x="${cx - 5}" y="${cy + 5}" width="10" height="12" fill="${SKIN}"/>`);
  const fw = f.wide ? 0.58 : 0.5, fh = f.long ? 0.66 : 0.6;
  A.push(`<ellipse cx="${cx}" cy="${cy - 1}" rx="${R * fw}" ry="${R * fh}" fill="${SKIN}"/>`);
  A.push(`<circle cx="${cx - R * fw}" cy="${cy}" r="2.4" fill="${SKIN}"/><circle cx="${cx + R * fw}" cy="${cy}" r="2.4" fill="${SKIN}"/>`);
  if (f.earring) A.push(`<circle cx="${cx - R * fw}" cy="${cy + 3}" r="1.6" fill="${brass}"/>`);
  const ey = cy - R * 0.06, H = f.hair;
  if (!f.bald) {
    if (H === "long") A.push(`<path d="M${cx - R * 0.62} ${cy + R * 0.55} Q${cx - R * 0.68} ${cy - R * 0.75} ${cx} ${cy - R * 0.8} Q${cx + R * 0.68} ${cy - R * 0.75} ${cx + R * 0.62} ${cy + R * 0.55} Q${cx + R * 0.4} ${cy - R * 0.1} ${cx + R * 0.42} ${cy - R * 0.35} Q${cx} ${cy - R * 0.5} ${cx - R * 0.42} ${cy - R * 0.35} Q${cx - R * 0.4} ${cy - R * 0.1} ${cx - R * 0.62} ${cy + R * 0.55}Z" fill="${hair}"/>`);
    else if (H === "wild") A.push(`<path d="M${cx - R * 0.64} ${cy + R * 0.1} Q${cx - R * 0.88} ${cy - R * 0.75} ${cx - R * 0.34} ${cy - R * 0.66} Q${cx - R * 0.5} ${cy - R} ${cx} ${cy - R * 0.9} Q${cx + R * 0.5} ${cy - R} ${cx + R * 0.34} ${cy - R * 0.66} Q${cx + R * 0.88} ${cy - R * 0.75} ${cx + R * 0.64} ${cy + R * 0.1} Q${cx + R * 0.3} ${cy - R * 0.42} ${cx} ${cy - R * 0.5} Q${cx - R * 0.3} ${cy - R * 0.42} ${cx - R * 0.64} ${cy + R * 0.1}Z" fill="${hair}"/>`);
    else if (H === "curly") { for (let i = -3; i <= 3; i++) A.push(`<circle cx="${cx + i * R * 0.16}" cy="${cy - R * 0.5 + Math.abs(i) * R * 0.03}" r="${R * 0.14}" fill="${hair}"/>`); }
    else if (H === "bun") { A.push(`<circle cx="${cx}" cy="${cy - R * 0.74}" r="${R * 0.18}" fill="${hair}"/><path d="M${cx - R * 0.5} ${cy + R * 0.05} Q${cx - R * 0.5} ${cy - R * 0.6} ${cx} ${cy - R * 0.6} Q${cx + R * 0.5} ${cy - R * 0.6} ${cx + R * 0.5} ${cy + R * 0.05} Q${cx} ${cy - R * 0.42} ${cx - R * 0.5} ${cy + R * 0.05}Z" fill="${hair}"/>`); }
    else if (H === "wavy") A.push(`<path d="M${cx - R * 0.52} ${cy - R * 0.02} Q${cx - R * 0.5} ${cy - R * 0.62} ${cx - R * 0.16} ${cy - R * 0.58} Q${cx} ${cy - R * 0.72} ${cx + R * 0.16} ${cy - R * 0.58} Q${cx + R * 0.5} ${cy - R * 0.62} ${cx + R * 0.52} ${cy - R * 0.02} Q${cx + R * 0.2} ${cy - R * 0.4} ${cx} ${cy - R * 0.46} Q${cx - R * 0.2} ${cy - R * 0.4} ${cx - R * 0.52} ${cy - R * 0.02}Z" fill="${hair}"/>`);
    else if (H === "recede") A.push(`<path d="M${cx - R * 0.5} ${cy} Q${cx - R * 0.52} ${cy - R * 0.5} ${cx - R * 0.12} ${cy - R * 0.46} Q${cx - R * 0.28} ${cy - R * 0.18} ${cx - R * 0.5} ${cy}Z M${cx + R * 0.5} ${cy} Q${cx + R * 0.52} ${cy - R * 0.5} ${cx + R * 0.12} ${cy - R * 0.46} Q${cx + R * 0.28} ${cy - R * 0.18} ${cx + R * 0.5} ${cy}Z" fill="${hair}"/>`);
    else A.push(`<path d="M${cx - R * 0.52} ${cy - R * 0.06} Q${cx - R * 0.54} ${cy - R * 0.66} ${cx} ${cy - R * 0.66} Q${cx + R * 0.54} ${cy - R * 0.66} ${cx + R * 0.52} ${cy - R * 0.06} Q${cx + R * 0.28} ${cy - R * 0.44} ${cx} ${cy - R * 0.44} Q${cx - R * 0.28} ${cy - R * 0.44} ${cx - R * 0.52} ${cy - R * 0.06}Z" fill="${hair}"/>`);
  } else if (f.fringe) A.push(`<path d="M${cx - R * 0.42} ${cy - R * 0.28} Q${cx - R * 0.44} ${cy - R * 0.5} ${cx} ${cy - R * 0.5} Q${cx + R * 0.44} ${cy - R * 0.5} ${cx + R * 0.42} ${cy - R * 0.28} Q${cx} ${cy - R * 0.36} ${cx - R * 0.42} ${cy - R * 0.28}Z" fill="${hair}"/>`);
  if (f.hat === "cap") A.push(`<path d="M${cx - R * 0.5} ${cy - R * 0.36} Q${cx} ${cy - R * 0.9} ${cx + R * 0.5} ${cy - R * 0.36} Q${cx} ${cy - R * 0.6} ${cx - R * 0.5} ${cy - R * 0.36}Z" fill="${f.hatc || "#3a2f4a"}"/>`);
  if (f.beard === "long") A.push(`<path d="M${cx - R * 0.36} ${cy + R * 0.05} Q${cx - R * 0.4} ${cy + R * 0.8} ${cx} ${cy + R * 0.98} Q${cx + R * 0.4} ${cy + R * 0.8} ${cx + R * 0.36} ${cy + R * 0.05} Q${cx} ${cy + R * 0.35} ${cx - R * 0.36} ${cy + R * 0.05}Z" fill="${hair}"/>`);
  else if (f.beard === "full") A.push(`<path d="M${cx - R * 0.4} ${cy + R * 0.02} Q${cx - R * 0.44} ${cy + R * 0.55} ${cx} ${cy + R * 0.66} Q${cx + R * 0.44} ${cy + R * 0.55} ${cx + R * 0.4} ${cy + R * 0.02} Q${cx} ${cy + R * 0.34} ${cx - R * 0.4} ${cy + R * 0.02}Z" fill="${hair}"/>`);
  else if (f.beard === "goatee") A.push(`<path d="M${cx - R * 0.16} ${cy + R * 0.3} Q${cx} ${cy + R * 0.62} ${cx + R * 0.16} ${cy + R * 0.3} Q${cx} ${cy + R * 0.4} ${cx - R * 0.16} ${cy + R * 0.3}Z" fill="${hair}"/>`);
  if (f.beard === "mous" || f.beard === "full" || f.beard === "long" || f.mous) A.push(`<path d="M${cx - R * 0.22} ${cy + R * 0.22} Q${cx} ${cy + R * 0.31} ${cx + R * 0.22} ${cy + R * 0.22}" stroke="${hair}" stroke-width="3" fill="none" stroke-linecap="round"/>`);
  A.push(`<path d="M${cx - R * 0.32} ${ey - R * 0.13} q${R * 0.11} -${R * 0.06} ${R * 0.22} 0 M${cx + R * 0.1} ${ey - R * 0.13} q${R * 0.11} -${R * 0.06} ${R * 0.22} 0" stroke="${f.browc || "#4a3d2c"}" stroke-width="1.6" fill="none" stroke-linecap="round"/>`);
  A.push(`<circle cx="${cx - R * 0.2}" cy="${ey}" r="1.7" fill="${ink}"/><circle cx="${cx + R * 0.2}" cy="${ey}" r="1.7" fill="${ink}"/>`);
  if (f.nose === "metal") A.push(`<path d="M${cx - 2} ${ey + 2} L${cx + 2} ${ey + 2} L${cx + 1.3} ${cy + R * 0.2} L${cx - 1.3} ${cy + R * 0.2}Z" fill="${brass}"/>`);
  else A.push(`<path d="M${cx} ${ey + 1} L${cx - 2} ${cy + R * 0.16} Q${cx} ${cy + R * 0.22} ${cx + 2} ${cy + R * 0.16}" stroke="${ink}" stroke-width="1" fill="none" opacity=".5"/>`);
  if (f.beard !== "full" && f.beard !== "long") {
    if (f.smile) A.push(`<path d="M${cx - R * 0.16} ${cy + R * 0.32} Q${cx} ${cy + R * 0.46} ${cx + R * 0.16} ${cy + R * 0.32}" stroke="${ink}" stroke-width="1.5" fill="none" stroke-linecap="round"/>`);
    else A.push(`<path d="M${cx - R * 0.13} ${cy + R * 0.36} Q${cx} ${cy + R * 0.4} ${cx + R * 0.13} ${cy + R * 0.36}" stroke="${ink}" stroke-width="1.4" fill="none" stroke-linecap="round" opacity=".7"/>`);
  }
  if (f.glasses === "round") A.push(`<g stroke="${brass}" stroke-width="1.3" fill="none"><circle cx="${cx - R * 0.2}" cy="${ey}" r="${R * 0.17}"/><circle cx="${cx + R * 0.2}" cy="${ey}" r="${R * 0.17}"/><line x1="${cx - R * 0.03}" y1="${ey}" x2="${cx + R * 0.03}" y2="${ey}"/></g>`);
  else if (f.glasses === "square") A.push(`<g stroke="${brass}" stroke-width="1.3" fill="none"><rect x="${cx - R * 0.37}" y="${ey - R * 0.13}" width="${R * 0.28}" height="${R * 0.26}" rx="2"/><rect x="${cx + R * 0.09}" y="${ey - R * 0.13}" width="${R * 0.28}" height="${R * 0.26}" rx="2"/><line x1="${cx - R * 0.09}" y1="${ey}" x2="${cx + R * 0.09}" y2="${ey}"/></g>`);
  else if (f.glasses === "pince") A.push(`<g stroke="${brass}" stroke-width="1.1" fill="none"><circle cx="${cx - R * 0.16}" cy="${ey}" r="${R * 0.12}"/><circle cx="${cx + R * 0.16}" cy="${ey}" r="${R * 0.12}"/></g>`);
  if (f.hat === "laurel") A.push(`<path d="M${cx - R * 0.52} ${cy - R * 0.28} Q${cx - R * 0.78} ${cy - R * 0.66} ${cx - R * 0.3} ${cy - R * 0.74} M${cx + R * 0.52} ${cy - R * 0.28} Q${cx + R * 0.78} ${cy - R * 0.66} ${cx + R * 0.3} ${cy - R * 0.74}" stroke="#9bbf6a" stroke-width="2.4" fill="none" stroke-linecap="round"/>`);
  if (f.hat === "ruff") A.push(`<path d="M${cx - R * 0.5} ${cy + R * 0.5} q${R * 0.12} ${R * 0.14} ${R * 0.25} 0 q${R * 0.12} ${R * 0.14} ${R * 0.25} 0 q${R * 0.12} ${R * 0.14} ${R * 0.25} 0 q${R * 0.12} ${R * 0.14} ${R * 0.25} 0" stroke="#e9e3d6" stroke-width="3" fill="none"/>`);
  A.push(`</g><circle cx="${cx}" cy="${cy}" r="${R - 1}" fill="none" stroke="${f.accent || brass}" stroke-width="1.5" opacity=".85"/></svg>`);
  return A.join("");
}
function ring(pct, color, S, w) {
  w = w || 4; const r = S / 2 - w / 2 - 1, c = 2 * Math.PI * r, off = c * (1 - pct / 100);
  return `<svg viewBox="0 0 ${S} ${S}"><circle cx="${S / 2}" cy="${S / 2}" r="${r}" fill="none" stroke="#28324a" stroke-width="${w}"/><circle cx="${S / 2}" cy="${S / 2}" r="${r}" fill="none" stroke="${color}" stroke-width="${w}" stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${off}"/></svg>`;
}

export async function renderCouncil(view, pid, onBack) {
  injectStyles();
  view.innerHTML = `<div class="cv"><p style="color:#93a1bd;padding:30px">Convocando al Consejo…</p></div>`;
  let d;
  try {
    const res = await fetch(`/portal/api/projects/${encodeURIComponent(pid)}/council`, { headers: { Accept: "application/json" } });
    d = await res.json(); if (!res.ok) throw new Error();
  } catch (e) { view.innerHTML = `<div class="cv"><p style="color:#e0736f;padding:30px">No se pudo cargar el Consejo.</p></div>`; return; }
  if (!d || !d.phases) {
    view.innerHTML = `<div class="cv"><div class="cv-top"><h2 style="font-family:var(--serif)">El <em style="color:#e0a96d">Consejo</em></h2>
      <button class="cv-back" id="cv-back2">← Dashboard</button></div>
      <p style="color:#e0a96d;padding:20px 4px">Reinicia el portal para cargar la vista nueva del Consejo (el servidor está sirviendo una versión anterior del endpoint).</p></div>`;
    const b = view.querySelector("#cv-back2"); if (b && onBack) b.onclick = () => onBack();
    return;
  }
  const byId = Object.fromEntries(d.personas.map((p) => [p.id, p]));

  const phasesHtml = d.phases.map((ph) => {
    const col = PHC[ph.key] || "#e0a96d";
    const meds = ph.ids.map((id) => {
      const p = byId[id]; if (!p) return "";
      const sc = SC[p.status];
      return `<div class="cv-med" tabindex="0" role="button" data-id="${id}" aria-label="${p.name}">
        <div class="cv-por"><div class="prg">${ring(p.progress, sc, 68, 4)}</div>${face(p, 60)}
          <span class="cv-stt" style="background:${sc}"></span></div>
        <div class="cv-mnm">${p.name}</div><div class="cv-mrl">${p.role}</div></div>`;
    }).join("");
    return `<div class="cv-phase" style="--pc:${col}">
      <div class="cv-donut">${ring(ph.progress, col, 120, 12)}
        <div class="mid"><div class="pct" style="color:${col}">${ph.progress}%</div><div class="n">${ph.name.replace("Fase ", "")}</div></div></div>
      <div><div class="cv-ph-name">${ph.name}</div><div class="cv-ph-sub">${ph.sub}</div><div class="cv-meds">${meds}</div></div></div>`;
  }).join("");

  view.innerHTML = `<div class="cv"><canvas class="cv-stars"></canvas>
    <div class="cv-top"><div><div class="cv-eyebrow">ACERO · consejo de investigación</div>
      <h2>El <em>Consejo</em></h2>
      <div class="cv-tag">Tres fases, catorce mentes. Cada hipótesis es una <b>pelota</b> que viaja por el riel: quien la tiene, la trabaja.</div></div>
      <button class="cv-back" id="cv-back">← Dashboard</button></div>
    <div class="cv-board"><div class="cv-phases">${phasesHtml}</div>
      <div class="cv-rail"><div class="cv-rail-h">flujo · hipótesis</div><div class="cv-track"></div>
        <div class="cv-zone"><span class="cv-zl">creativa</span><div class="cv-balls" data-b="creativa"></div></div>
        <div class="cv-zone"><span class="cv-zl">investig.</span><div class="cv-balls" data-b="investig"></div></div>
        <div class="cv-zone"><span class="cv-zl">crítica</span><div class="cv-balls" data-b="critica"></div></div></div></div>
    <div class="cv-scrim" id="cv-scrim"></div><aside class="cv-drawer" id="cv-drawer"></aside></div>`;

  const root = view.querySelector(".cv");
  (d.balls || []).forEach((b) => {
    const box = root.querySelector(`.cv-balls[data-b="${b.phase}"]`); if (!box) return;
    const w = byId[b.persona] || { name: "" };
    const e = document.createElement("div"); e.className = "cv-ball"; e.style.background = SC[b.status] || "#93a1bd";
    e.textContent = b.id; e.title = `${b.id} · ${w.name} (${w.role || ""})${b.verdict ? " — " + b.verdict : ""}`;
    e.dataset.id = b.persona; box.appendChild(e);
  });

  const scrim = root.querySelector("#cv-scrim"), drawer = root.querySelector("#cv-drawer");
  const back = root.querySelector("#cv-back"); if (back && onBack) back.onclick = () => onBack();
  function open(id) {
    const p = byId[id]; if (!p) return; const col = SC[p.status];
    const held = (d.balls || []).filter((b) => b.persona === id).map((b) => b.id);
    drawer.innerHTML = `<div class="cv-dh"><div class="cv-df">${face(p, 76)}</div>
      <div><div class="cv-dn">${p.name}</div><div class="cv-dr">${p.role}</div><div class="cv-dm">${p.module}</div></div>
      <button class="cv-close" id="cv-x">✕</button></div>
      <div class="cv-db"><div class="cv-dsum">${p.summary}</div>
        <div class="cv-flow"><div><div class="cv-k">recibe de</div><div class="cv-v">${p.awaits}</div></div>
          <div><div class="cv-k">le pasa a</div><div class="cv-v">${p.hands_to}</div></div></div>
        ${held.length ? `<div><div class="cv-st">tiene la pelota</div><div style="font-size:13px;color:#cfd8ea">Trabaja ahora: <b style="color:${col}">${held.join(", ")}</b></div></div>` : ""}
        <div><div class="cv-st">avance en este proyecto</div>
          <div style="display:flex;align-items:center;gap:14px;margin-top:8px">
            <div style="position:relative;width:54px;height:54px">${ring(p.progress, col, 54, 5)}<b style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:13px">${p.progress}</b></div>
            <div style="color:#93a1bd;font-size:13px">estado <b style="color:${col}">${SL[p.status]}</b> · <span style="color:#5f6d88">${p.source === "project" ? "señal real" : "madurez"}</span></div></div></div>
        <div><div class="cv-st">tareas</div>${(p.tasks || []).map((t) => `<div class="cv-task"><span class="cv-tb" style="background:${TASK[t[1]][0]}"></span><span class="cv-tt">${t[0]}</span><span class="cv-ts">${TASK[t[1]][1]}</span></div>`).join("")}</div></div>`;
    drawer.classList.add("open"); scrim.classList.add("open"); drawer.querySelector("#cv-x").onclick = close;
  }
  function close() { drawer.classList.remove("open"); scrim.classList.remove("open"); }
  scrim.onclick = close; document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  root.querySelectorAll(".cv-med").forEach((m) => { m.onclick = () => open(m.dataset.id); m.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(m.dataset.id); } }; });
  root.querySelectorAll(".cv-ball").forEach((b) => (b.onclick = () => open(b.dataset.id)));

  const cvs = root.querySelector(".cv-stars"), x = cvs.getContext("2d");
  requestAnimationFrame(() => { cvs.width = root.clientWidth; cvs.height = root.clientHeight; for (let i = 0; i < 130; i++) { const a = Math.random() * cvs.width, b = Math.random() * cvs.height * 0.55, r = Math.random() * 1.3; x.globalAlpha = Math.random() * 0.7 + 0.15; x.fillStyle = Math.random() > 0.85 ? "#e0a96d" : "#cfe0ff"; x.beginPath(); x.arc(a, b, r, 0, 6.28); x.fill(); } x.globalAlpha = 1; });
}
