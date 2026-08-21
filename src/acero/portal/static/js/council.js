// El Consejo — 3 fases (pasteles) + rostros distintos + riel de pelotas (hipótesis en flujo).
// Fetches /portal/api/projects/{pid}/council.
import { post } from "./api.js";
import { helpIcon } from "./components.js";

const SC = { good: "#54c08a", warn: "#e0a96d", new: "#5b8def", weak: "#e0736f" };
const SL = { good: "sólido", warn: "mejorable", new: "nuevo", weak: "débil" };
const TASK = { done: ["#54c08a", "hecho"], doing: ["#e0a96d", "en curso"], todo: ["#5f6d88", "pendiente"] };
const PHC = { creativa: "#7ba7ff", investig: "#5ec7a8", critica: "#e0a96d" };
const VC = { verified: "#54c08a", refuted: "#e0736f", formally_supported: "#54c08a", holds_empirically: "#e0a96d", inconclusive: "#93a1bd", probado: "#54c08a", propuesto: "#5b8def", partial_progress: "#7ba7ff" };
// A qué tablero rico (fichas para dar seguimiento) lleva cada personaje: ["phase", clave] o ["ops"].
const PERSONA_VIEW = {
  hilbert: ["phase", "hipotesis"], euler: ["phase", "hipotesis"],
  hipatia: ["phase", "literatura"], tycho: ["phase", "experimentos"],
  davinci: ["phase", "experimentos"], kepler: ["phase", "experimentos"],
  popper: ["phase", "experimentos"], euclides: ["phase", "resultados"],
  godel: ["phase", "resultados"], aristoteles: ["phase", "hipotesis"],
  feynman: ["phase", "hipotesis"], gauss: ["phase", "conclusiones"],
  arquimedes: ["ops"], bohr: ["ops"],
  ramanujan: ["phase", "hipotesis"], turing: ["phase", "experimentos"], noether: ["phase", "conclusiones"],
};
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
let _pollTimer = null;   // refresco EN VIVO del Consejo (un solo timer por página)

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
  .cv-board{position:relative;z-index:1;display:grid;grid-template-columns:1fr auto;gap:18px;align-items:stretch}
  @media(max-width:820px){.cv-board{grid-template-columns:1fr}.cv-rail{display:none}}
  .cv-rail{min-width:128px;max-width:320px}
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
  .cv-rail-h{font-family:var(--mono);font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--faint);text-align:center;margin-bottom:6px;display:flex;align-items:center;justify-content:center;gap:8px}
  .cv-max-btn{font-family:var(--mono);font-size:9px;letter-spacing:.08em;text-transform:none;color:var(--faint);background:transparent;border:1px solid var(--line);border-radius:8px;padding:2px 8px;cursor:pointer}
  .cv-max-btn:hover{color:#e7ecf7;border-color:#4a5878}
  .cv-rail-backdrop{position:fixed;inset:0;background:rgba(8,11,18,.72);z-index:998}
  .cv-rail-maxed{position:fixed !important;inset:3vh 3vw;z-index:999;max-width:none;padding:16px 0;box-shadow:0 20px 60px rgba(0,0,0,.6);display:flex;flex-direction:column}
  .cv-rail-maxed .cv-fcols{flex:1;overflow-y:auto;flex-wrap:wrap}
  body.cv-rail-lock{overflow:hidden}
  .cv-bare{margin:0 10px 10px;border:1px solid var(--line);border-radius:12px;background:#141b2b}
  .cv-bare-head{width:100%;display:flex;align-items:center;gap:6px;background:transparent;border:0;color:#cfd8ea;font-family:var(--mono);font-size:11px;padding:8px 10px;cursor:pointer;text-align:left}
  .cv-bare-head:hover{color:#e7ecf7}
  .cv-bare-car{margin-left:auto;transition:transform .15s}
  .cv-bare.open .cv-bare-car{transform:rotate(90deg)}
  .cv-bare-list{border-top:1px solid var(--line);padding:8px 10px;max-height:260px;overflow-y:auto}
  .cv-bare-row{display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px;border-bottom:1px solid #1e263a}
  .cv-bare-row:last-of-type{border-bottom:0}
  .cv-bare-tag{font-family:var(--mono);font-size:10px;color:var(--faint);min-width:28px}
  .cv-bare-title{flex:1;color:#cfd8ea;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
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
  .cv-halo-now{border-radius:50%;animation:cvPulse 1.5s ease-in-out infinite}
  .cv-halo-from{border-radius:50%;box-shadow:0 0 16px 5px rgba(230,196,90,.45)}
  .cv-halo-next{border-radius:50%;box-shadow:0 0 16px 5px rgba(224,142,80,.5)}
  @keyframes cvPulse{0%,100%{box-shadow:0 0 12px 4px rgba(84,192,138,.4)}50%{box-shadow:0 0 26px 10px rgba(84,192,138,.7)}}
  .cv-legend{display:flex;gap:14px;align-items:center;font-family:var(--mono);font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);margin-top:6px}
  .cv-legend i{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:5px;vertical-align:-1px}
  .cv-journey{position:relative;z-index:1;background:linear-gradient(180deg,#1b2438,#151d2e);border:1px solid #28324a;border-radius:14px;padding:12px 16px;margin-bottom:12px}
  .cv-jtop{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
  .cv-jpct{font-family:var(--serif);font-size:26px;font-weight:700;color:var(--brass);font-variant-numeric:tabular-nums;line-height:1}
  .cv-jlabel{font-family:var(--mono);font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:var(--faint)}
  .cv-jbar{flex:1;min-width:180px;height:10px;background:#0f1626;border:1px solid #28324a;border-radius:99px;overflow:hidden}
  .cv-jbar span{display:block;height:100%;background:linear-gradient(90deg,#7ba7ff,#5ec7a8,#e0a96d);transition:width .6s}
  .cv-jnext{font-size:13px;color:#eef2fb}.cv-jnext b{color:#e0a96d}
  .cv-jsteps{display:flex;gap:4px 14px;flex-wrap:wrap;margin-top:9px}
  .cv-jstep{display:flex;align-items:center;gap:5px;font-size:10.5px;color:var(--faint)}
  .cv-jstep.done{color:#9fd6b8}
  .cv-jstep i{width:12px;height:12px;border-radius:50%;border:1.5px solid #5f6d88;display:inline-flex;align-items:center;justify-content:center;font-size:8px;font-style:normal;flex:0 0 12px}
  .cv-jstep.done i{border-color:#54c08a;background:rgba(84,192,138,.18);color:#54c08a}
  .cv-live{position:relative;z-index:1;display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:linear-gradient(90deg,rgba(84,192,138,.10),rgba(21,29,46,.9));
    border:1px solid #2b4a3a;border-radius:14px;padding:10px 14px;margin-bottom:16px}
  .cv-live.done{background:linear-gradient(90deg,rgba(123,167,255,.08),rgba(21,29,46,.9));border-color:#28324a}
  .cv-live-dot{width:10px;height:10px;border-radius:50%;background:#54c08a;animation:cvPulse 1.2s infinite;flex:0 0 10px}
  .cv-live-face{width:34px;height:34px;flex:0 0 34px;line-height:0}
  .cv-live b{font-size:13px}.cv-live .tagx{font-family:var(--mono);font-size:10px;color:var(--dim)}
  .cv-live-bar{flex:1;min-width:120px;height:7px;background:#1b2438;border-radius:99px;overflow:hidden;border:1px solid #28324a}
  .cv-live-bar span{display:block;height:100%;background:linear-gradient(90deg,#54c08a,#7ba7ff);transition:width .6s}
  .cv-live-stmt{width:100%;font-size:11px;color:#93a1bd;font-style:italic}
  .cv-report{position:relative;z-index:1;background:#10192b;border:1px solid #28324a;border-radius:14px;
    padding:0;margin-bottom:16px;overflow:hidden}
  .cv-report-bar{display:flex;gap:8px;align-items:center;padding:10px 14px;border-bottom:1px solid #28324a;background:#151d2e}
  .cv-report-bar b{font-family:var(--mono);font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--brass)}
  .cv-report-body{white-space:pre-wrap;font-size:12.5px;line-height:1.55;color:#cfd8ea;
    max-height:440px;overflow:auto;font-family:ui-monospace,Menlo,monospace;padding:14px 18px}
  .cv-fcols{display:flex;gap:12px;justify-content:center;align-items:flex-start;overflow-x:auto;padding:4px 8px 10px}
  .cv-fcol{display:flex;flex-direction:column;align-items:center;gap:3px;min-width:52px;border-radius:12px;padding:5px 4px;border:1px solid transparent}
  .cv-fh{font-family:var(--mono);font-size:10px;font-weight:700;color:var(--brass);margin-bottom:2px}
  .cv-fcol.closed{filter:grayscale(1);opacity:.42}
  .cv-fcol.closed .cv-fh{color:#8a93a8}
  .cv-fcol.closed .cv-fface{animation:none!important;box-shadow:none!important}
  .cv-fcol.attention{background:rgba(224,115,111,.06);border-color:rgba(224,115,111,.3)}
  .cv-fcol.attention .cv-fh{color:#e0736f}
  .cv-fcol.attention .cv-fface:not(.is-decision){box-shadow:0 0 9px 3px rgba(224,115,111,.4);animation:none}
  .cv-fcol.attention .cv-fface.is-decision{animation:cvPulse 1.5s infinite}
  .cv-fstep{display:flex;flex-direction:column;align-items:center;gap:1px}
  .cv-fface{width:26px;height:26px;line-height:0;border-radius:50%}
  .cv-fface.is-now{animation:cvPulse 1.5s infinite}
  .cv-fface.is-next{opacity:.55;box-shadow:0 0 10px 3px rgba(224,142,80,.5)}
  .cv-fname{font-size:7.5px;color:var(--faint);line-height:1}
  .cv-fdid{font-size:7px;color:#5f6d88;line-height:1;max-width:60px;text-align:center}
  .cv-farrow{color:#5f6d88;font-size:10px;line-height:1;margin:1px 0}
  .cv-fiches{display:flex;flex-direction:column;gap:9px;margin-top:8px}
  .cv-fiche{background:#151d2e;border:1px solid #28324a;border-left:3px solid var(--fc,#5f6d88);border-radius:11px;padding:10px 12px}
  .cv-fiche-t{font-size:13px;line-height:1.42;color:#eef2fb}
  .cv-fiche-m{display:flex;gap:8px;align-items:center;margin-top:7px;flex-wrap:wrap}
  .cv-chip{font-family:var(--mono);font-size:9.5px;letter-spacing:.06em;text-transform:uppercase;padding:2px 8px;border-radius:999px;border:1px solid currentColor}
  .cv-by{font-family:var(--mono);font-size:10px;color:#93a1bd}
  .cv-note{color:#93a1bd;font-size:12.5px;line-height:1.5;background:#151d2e;border:1px dashed #28324a;border-radius:11px;padding:10px 12px;margin-top:8px}
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

export async function renderCouncil(view, pid, cb, opts = {}) {
  // `cb` puede ser el objeto de callbacks del app o (compat) una función onBack.
  const onBack = () => { if (typeof cb === "function") return cb(); if (cb && cb.openHome) return cb.openHome(); };
  const onOps = () => { if (cb && cb.openOperations) return cb.openOperations(pid); };
  // Doble clic / botón → el tablero rico del personaje (sus fichas de seguimiento).
  const openPersonaDash = (id) => {
    const v = PERSONA_VIEW[id] || ["ops"];
    if (v[0] === "phase" && cb && cb.openPhase) return cb.openPhase(pid, v[1]);
    if (cb && cb.openOperations) return cb.openOperations(pid);
  };
  injectStyles();
  view.innerHTML = `<div class="cv"><p style="color:#93a1bd;padding:30px">Convocando al Consejo…</p></div>`;
  let d;
  try {
    const res = await fetch(`/portal/api/projects/${encodeURIComponent(pid)}/council`, { headers: { Accept: "application/json" } });
    d = await res.json(); if (!res.ok) throw new Error();
  } catch (e) { view.innerHTML = `<div class="cv"><p style="color:#e0736f;padding:30px">No se pudo cargar el Consejo.</p></div>`; return; }
  if (!d || !d.phases) {
    view.innerHTML = `<div class="cv"><div class="cv-top"><h2 style="font-family:var(--serif)">El <em style="color:#e0a96d">Consejo</em></h2>
      <button class="cv-back" id="cv-back2">← Investigaciones</button></div>
      <p style="color:#e0a96d;padding:20px 4px">Reinicia el portal para cargar la vista nueva del Consejo (el servidor está sirviendo una versión anterior del endpoint).</p></div>`;
    const b = view.querySelector("#cv-back2"); if (b) b.onclick = () => onBack();
    return;
  }
  const byId = Object.fromEntries(d.personas.map((p) => [p.id, p]));
  // nebulosas: verde = trabaja AHORA · amarillo = de dónde viene · naranja = a dónde va
  const H = d.halos || { now: [], from: [], next: [] };
  const haloOf = (id) => (H.now || []).includes(id) ? " cv-halo-now"
    : (H.from || []).includes(id) ? " cv-halo-from"
    : (H.next || []).includes(id) ? " cv-halo-next" : "";

  const phasesHtml = d.phases.map((ph) => {
    const col = PHC[ph.key] || "#e0a96d";
    const meds = ph.ids.map((id) => {
      const p = byId[id]; if (!p) return "";
      const sc = SC[p.status];
      const hstate = (H.now || []).includes(id) ? " · 🟢 trabajando AHORA"
        : (H.from || []).includes(id) ? " · 🟡 acaba de pasar la info"
        : (H.next || []).includes(id) ? " · 🟠 la recibirá"
        : (p.progress > 0 ? "" : " · sin actividad aún");
      return `<div class="cv-med" tabindex="0" role="button" data-id="${id}" aria-label="${p.name}"
        title="${esc(p.name)} — avance ${p.progress}%${hstate ? esc(hstate) : ""}">
        <div class="cv-por${haloOf(id)}"><div class="prg">${ring(p.progress, sc, 68, 4)}</div>${face(p, 60)}
          <span class="cv-stt" style="background:${sc}"></span></div>
        <div class="cv-mnm">${p.name}</div><div class="cv-mrl">${p.role} · <b style="color:${p.progress > 0 ? "#54c08a" : "#5f6d88"}">${p.progress}%</b></div></div>`;
    }).join("");
    return `<div class="cv-phase" style="--pc:${col}">
      <div class="cv-donut">${ring(ph.progress, col, 120, 12)}
        <div class="mid"><div class="pct" style="color:${col}">${ph.progress}%</div><div class="n">${ph.name.replace("Fase ", "")}</div></div></div>
      <div><div class="cv-ph-name">${ph.name}</div><div class="cv-ph-sub">${ph.sub}</div><div class="cv-meds">${meds}</div></div></div>`;
  }).join("");

  // --- VIAJE: progreso GENERAL de la investigación + qué sigue (hasta arriba) ---
  const jn = d.journey;
  const journeyHtml = !jn ? "" :
    `<div class="cv-journey">
      <div class="cv-jtop">
        <div><div class="cv-jlabel">investigación completa · hitos${helpIcon(
          "Este % mide el PROYECTO completo contra una lista fija de hitos (conjetura " +
          "planteada, novedad revisada, atacada computacionalmente, etc.) — sube poco a " +
          "poco y casi nunca llega a 100 rápido. Es DISTINTO del % que ves más abajo en " +
          "'ronda X/Y', que es solo el avance del ciclo de Bohr QUE ESTÁ CORRIENDO AHORA " +
          "MISMO (ese sí puede llegar a 100% en minutos y reiniciar en la próxima ronda). " +
          "Y también es distinto del anillo de 'fases con trabajo' del dashboard de " +
          "Operaciones, que solo cuenta cuántas de las 6 fases tienen algo. Tres números, " +
          "tres preguntas distintas — no es un error si no coinciden.")}</div><div class="cv-jpct">${jn.pct}%</div></div>
        <div class="cv-jbar"><span style="width:${jn.pct}%"></span></div>
        <div class="cv-jnext">➜ Siguiente: <b>${esc(jn.next_step)}</b></div>
      </div>
      <div class="cv-jsteps">${(jn.milestones || []).map((m) =>
        `<span class="cv-jstep${m.done ? " done" : ""}"><i>${m.done ? "✓" : ""}</i>${esc(m.label)}</span>`).join("")}
      </div>
      ${jn.frontier ? `<div style="margin-top:9px;font-size:12px;color:#cfd8ea;border-top:1px solid #28324a;padding-top:8px">🧭 <b style="color:${{ detras: "#93a1bd", camino: "#7ba7ff", en: "#e0a96d", tocando: "#54c08a" }[jn.frontier.level] || "#e0a96d"}">Frontera del conocimiento</b> — ${esc(jn.frontier.label)}</div>` : ""}
    </div>`;

  // --- barra EN VIVO: qué hace el ciclo AHORA, ronda, ¿dará otra vuelta?, % total ---
  const lv = d.live;
  const lvP = lv ? byId[lv.persona] : null;
  const wrC = { "sí": "#54c08a", no: "#e0736f" }[lv && lv.will_retry] || "#e0a96d";
  // conclusión en palabras humanas por disposición (honesto: sin inflar)
  const DISPO_TXT = {
    verified: "demostrada formalmente",
    refuted: "refutada — hay contraejemplo concreto",
    partial_progress: "progreso parcial VERIFICADO (condición/lema probado)",
    formally_supported: "lema núcleo probado; el puente espera revisión humana",
    needs_human_review: "sobrevivió a la búsqueda; requiere revisión humana",
    inconclusive: "sin conclusión: ni confirmada ni refutada — ACERO se abstiene",
    dropped: "descartada",
  };
  const sm = (lv && lv.summary) || null;
  const liveHtml = !lv ? "" : (!lv.done
    ? `<div class="cv-live"><span class="cv-live-dot"></span>
        ${lvP ? `<span class="cv-live-face">${face({ ...lvP, id: lvP.id + "lv" }, 34)}</span>` : ""}
        <b>${esc(lv.label || "trabajando…")}</b>
        <span class="tagx">ronda ${lv.round || 1}/${lv.max_rounds || 3} · ¿otra vuelta? <b style="color:${wrC}">${esc(lv.will_retry || "…")}</b></span>
        <div class="cv-live-bar"><span style="width:${lv.pct || 0}%"></span></div>
        <span class="tagx">${lv.pct || 0}%${helpIcon(
          "Avance de ESTE ciclo de Bohr nada más (ronda actual sobre el máximo de rondas). " +
          "Llega a 100% cuando el ciclo termina y VUELVE A EMPEZAR en 0% en el próximo — no " +
          "es el progreso total del proyecto. Ese es el % de arriba, 'investigación completa · hitos'.")}</span>
        ${lv.statement ? `<div class="cv-live-stmt">“${esc(lv.statement)}”</div>` : ""}</div>`
    : `<div class="cv-live done"><span class="tagx">ciclo terminado</span>
        <div class="cv-live-bar" style="max-width:140px"><span style="width:100%"></span></div>
        <span class="tagx"><b style="color:#54c08a">100%</b></span>
        ${lv.disposition ? `<span class="cv-chip" style="color:${VC[lv.disposition] || "#93a1bd"}">${esc(lv.disposition)}</span>` : ""}
        <b>${esc(DISPO_TXT[lv.disposition] || lv.label || "terminado")}</b>
        ${sm ? `<span class="tagx">reformulaciones ${sm.reformulations ?? 0} · lemas probados ${sm.lemmas_proved ?? 0}${sm.critic ? " · crítico: " + esc(sm.critic) : ""}${sm.anomalies ? " · 🔥 anomalías: " + sm.anomalies : ""}</span>` : ""}
        ${lv.statement ? `<div class="cv-live-stmt">conclusión sobre: “${esc(lv.statement)}”</div>` : ""}
        ${d.report ? `<button class="cv-back" id="cv-report-btn" style="border-color:#c8863c;color:#e0a96d">📜 Informe de Bohr</button>` : ""}
        <button class="cv-back" id="cv-report-regen" title="Bohr reconstruye el informe del ciclo YA corrido con el motor nuevo (narrativa + referencias), sin repetir el ciclo">🔁 Regenerar informe</button>
        <span id="cv-regen-msg" class="tagx"></span>
        <span class="tagx" style="margin-left:auto">🎩 otra ronda: Bohr → Investigar — esta barra se REINICIA y avanza con el nuevo ciclo</span></div>`);

  // --- riel: una COLUMNA por hipótesis con la cadena de quién hizo qué (en orden) ---
  const allFlows = d.flows || [];
  // 'bare' = propuestas crudas sin trabajo ni decisión -- si se dejan como columna
  // completa, 30 de estas ahogan las pocas que sí avanzan. Van en un bloque
  // colapsado aparte con acción rápida para dictaminarlas (aprobar/rechazar).
  const flows = allFlows.filter((f) => !f.bare);
  const bareFlows = allFlows.filter((f) => f.bare);
  const bareHtml = !bareFlows.length ? "" : `<div class="cv-bare" id="cv-bare">
      <button class="cv-bare-head" id="cv-bare-toggle">📋 ${bareFlows.length} propuesta${bareFlows.length === 1 ? "" : "s"} sin trabajar aún ${helpIcon(
        "Hipótesis que se propusieron pero nadie decidió todavía -- ni se aprobaron " +
        "para investigarse, ni se rechazaron. Se agrupan aquí para no ahogar el riel " +
        "con columnas vacías. Ábrelas para aprobar o rechazar cada una; 'Rechazar " +
        "todas' las cierra de un golpe si ya no valen la pena.")} <span class="cv-bare-car">▸</span></button>
      <div class="cv-bare-list" id="cv-bare-list" hidden>
        ${bareFlows.map((f) => `<div class="cv-bare-row" data-hid="${esc(f.hid)}">
          <span class="cv-bare-tag">${esc(f.id)}</span>
          <span class="cv-bare-title">${esc(f.title || "(sin título)")}</span>
          <button class="act ghost" data-bare-approve="${esc(f.hid)}" data-tag="${esc(f.id)}">Aprobar</button>
          <button class="act ghost" data-bare-reject="${esc(f.hid)}">Rechazar</button></div>`).join("")}
        <button class="cv-back" id="cv-bare-reject-all" style="margin-top:8px">✕ Rechazar todas (${bareFlows.length})</button>
      </div></div>`;
  const railHtml = flows.length
    ? `<div class="cv-rail-h">flujo · quién hizo qué
         <button class="cv-max-btn" id="cv-rail-max" title="Maximizar — útil cuando hay muchas hipótesis y las columnas quedan apretadas">⛶ Maximizar</button></div>
       ${bareHtml}
       <div class="cv-fcols" id="cv-fcols">${flows.map((f) => {
         // estado de la columna: el ciclo EN VIVO la trabaja → normal;
         // 'closed' → GRIS (terminada, nada pendiente);
         // abierta sin ciclo → ROJA (espera decisión), salvo la cara que decide.
         const isWorking = lv && !lv.done && lv.hypothesis_id && f.hid === lv.hypothesis_id;
         const colCls = f.state === "closed" ? " closed" : (isWorking ? "" : " attention");
         const chain = f.steps.map((s, si) => {
           const p = byId[s.persona] || { id: s.persona, name: s.persona, face: {} };
           const isNow = si === f.steps.length - 1;
           const cls = isNow ? (colCls === " attention" ? " is-now is-decision" : " is-now") : "";
           const xn = s.n > 1 ? ` ×${s.n}` : "";
           return `${si ? '<div class="cv-farrow">↓</div>' : ""}
             <div class="cv-fstep" title="${esc(p.name)} — ${esc(s.did || "")}${esc(xn)}${s.verdict ? " · " + esc(s.verdict) : ""}">
               <div class="cv-fface${cls}" data-id="${esc(s.persona)}">${face({ ...p, id: p.id + "f" + f.id + si }, 26)}</div>
               <span class="cv-fname">${esc(p.name)}${esc(xn)}</span>
               <span class="cv-fdid">${esc(s.did || "")}${esc(xn)}${s.verdict ? " · " + esc(s.verdict) : ""}</span></div>`;
         }).join("");
         const nx = f.next && byId[f.next] && f.state !== "closed"
           ? `<div class="cv-farrow">↓</div>
              <div class="cv-fstep" title="siguiente: ${esc(byId[f.next].name)}">
                <div class="cv-fface is-next" data-id="${esc(f.next)}">${face({ ...byId[f.next], id: f.next + "fn" + f.id }, 26)}</div>
                <span class="cv-fname" style="color:#e08e50">${esc(byId[f.next].name)}</span></div>`
           : "";
         const tip = f.state === "closed" ? "terminada — nada pendiente"
           : isWorking ? "el Consejo la trabaja AHORA"
           : `espera decisión — ${(byId[f.current] || {}).name || f.current} tiene la pelota`;
         return `<div class="cv-fcol${colCls}" title="${esc(f.id)} · ${esc(tip)}${f.title ? " — " + esc(f.title) : ""}">
           <div class="cv-fh">${esc(f.id)}</div>${chain}${nx}</div>`;
       }).join("")}</div>`
    : (allFlows.length
        ? `<div class="cv-rail-h">flujo · quién hizo qué</div>${bareHtml}`
        : `<div class="cv-rail-h">flujo · hipótesis</div><div class="cv-track"></div>
        <div class="cv-zone"><span class="cv-zl">creativa</span><div class="cv-balls" data-b="creativa"></div></div>
        <div class="cv-zone"><span class="cv-zl">investig.</span><div class="cv-balls" data-b="investig"></div></div>
        <div class="cv-zone"><span class="cv-zl">crítica</span><div class="cv-balls" data-b="critica"></div></div>`);

  view.innerHTML = `<div class="cv"><canvas class="cv-stars"></canvas>
    <div class="cv-top"><div><div class="cv-eyebrow">ACERO · consejo de investigación</div>
      <h2>El <em>Consejo</em></h2>
      <div class="cv-tag">Tres fases, catorce mentes. <span style="color:#c8863c">Un clic = resumen · doble clic = su tablero.</span></div>
      <div class="cv-legend"><span><i style="background:#54c08a"></i>trabajando ahora</span>
        <span><i style="background:#e6c45a"></i>viene de</span>
        <span><i style="background:#e08e50"></i>pasará a</span>
        <span><i style="background:#5f6d88"></i>columna gris = H terminada</span>
        <span><i style="background:#e0736f"></i>roja = espera tu decisión</span></div></div>
      <div style="display:flex;gap:8px;align-items:center">
        <button class="cv-back" id="cv-ops" title="Panel clásico: barras de lanzamiento, loop, publicación, proactividad">⚙ Operaciones</button>
        <button class="cv-back" id="cv-back">← Investigaciones</button></div></div>
    ${journeyHtml}
    ${liveHtml}
    ${d.report ? `<div class="cv-report" id="cv-report" hidden>
      <div class="cv-report-bar"><b>📜 informe de bohr · bitácora del ciclo</b>
        <button class="cv-back" id="cv-report-pdf" style="margin-left:auto;border-color:#c8863c;color:#e0a96d">⬇ Descargar PDF</button>
        <button class="cv-back" id="cv-report-x">✕ Cerrar</button></div>
      <div class="cv-report-body">${esc(d.report.markdown || "")}</div></div>` : ""}
    <div class="cv-board"><div class="cv-phases">${phasesHtml}</div>
      <div class="cv-rail" id="cv-rail">${railHtml}</div></div>
    <div class="cv-rail-backdrop" id="cv-rail-backdrop" hidden></div>
    <div class="cv-scrim" id="cv-scrim"></div><aside class="cv-drawer" id="cv-drawer"></aside></div>`;

  const root = view.querySelector(".cv");
  if (!flows.length) (d.balls || []).forEach((b) => {
    const box = root.querySelector(`.cv-balls[data-b="${b.phase}"]`); if (!box) return;
    const w = byId[b.persona] || { name: "" };
    const e = document.createElement("div"); e.className = "cv-ball"; e.style.background = SC[b.status] || "#93a1bd";
    e.textContent = b.id; e.title = `${b.id} · ${w.name} (${w.role || ""})${b.verdict ? " — " + b.verdict : ""}`;
    e.dataset.id = b.persona; box.appendChild(e);
  });

  const scrim = root.querySelector("#cv-scrim"), drawer = root.querySelector("#cv-drawer");
  const back = root.querySelector("#cv-back"); if (back) back.onclick = () => onBack();
  const ops = root.querySelector("#cv-ops"); if (ops) ops.onclick = () => onOps();

  const railBox = root.querySelector("#cv-rail");
  const railMax = root.querySelector("#cv-rail-max");
  const railBackdrop = root.querySelector("#cv-rail-backdrop");
  const setRailMax = (on) => {
    if (!railBox) return;
    railBox.classList.toggle("cv-rail-maxed", on);
    if (railBackdrop) railBackdrop.hidden = !on;
    if (railMax) railMax.textContent = on ? "✕ Minimizar" : "⛶ Maximizar";
    document.body.classList.toggle("cv-rail-lock", on);
  };
  if (railMax) railMax.onclick = () => setRailMax(!railBox.classList.contains("cv-rail-maxed"));
  if (railBackdrop) railBackdrop.onclick = () => setRailMax(false);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && railBox && railBox.classList.contains("cv-rail-maxed")) setRailMax(false);
  });

  // 📋 propuestas sin trabajar: expandir/colapsar + aprobar/rechazar (individual y en bloque)
  const bareBox = root.querySelector("#cv-bare");
  const bareToggle = root.querySelector("#cv-bare-toggle");
  const bareList = root.querySelector("#cv-bare-list");
  if (bareToggle && bareList) bareToggle.onclick = () => {
    bareList.hidden = !bareList.hidden;
    if (bareBox) bareBox.classList.toggle("open", !bareList.hidden);
  };
  const setHypStatus = async (hid, status, reason) => {
    await post(`/portal/api/projects/${encodeURIComponent(pid)}/hypothesis/${encodeURIComponent(hid)}/status`,
      { status, reason });
  };
  root.querySelectorAll("[data-bare-approve]").forEach((b) => b.addEventListener("click", async () => {
    const reason = prompt(`Razón para aprobar ${b.dataset.tag} (los siguientes pasos correrán sobre esta hipótesis):`);
    if (!reason) return;
    await setHypStatus(b.dataset.bareApprove, "APPROVED", reason);
    renderCouncil(view, pid, cb, opts);
  }));
  root.querySelectorAll("[data-bare-reject]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("¿Rechazar esta hipótesis?")) return;
    await setHypStatus(b.dataset.bareReject, "REJECTED", "rechazada por el humano");
    renderCouncil(view, pid, cb, opts);
  }));
  const bareRejectAll = root.querySelector("#cv-bare-reject-all");
  if (bareRejectAll) bareRejectAll.onclick = async () => {
    const n = bareFlows.length;
    if (!confirm(`¿Rechazar las ${n} propuestas sin trabajar? No se puede deshacer en bloque -- habría que reabrirlas una por una.`)) return;
    for (const f of bareFlows) await setHypStatus(f.hid, "REJECTED", "rechazada en bloque — propuesta nunca trabajada");
    renderCouncil(view, pid, cb, opts);
  };

  // 📜 la bitácora de Bohr: el informe tipo paper del último ciclo
  const rbtn = root.querySelector("#cv-report-btn");
  const rpanel = root.querySelector("#cv-report");
  if (rbtn) rbtn.onclick = () => {
    if (rpanel) { rpanel.hidden = !rpanel.hidden; if (!rpanel.hidden) rpanel.scrollIntoView({ behavior: "smooth", block: "nearest" }); }
  };
  const rx = root.querySelector("#cv-report-x");
  if (rx) rx.onclick = () => { if (rpanel) rpanel.hidden = true; };
  // 🔁 regenerar el informe del ciclo YA corrido con el motor nuevo (sin repetir ciclo)
  const rgen = root.querySelector("#cv-report-regen");
  if (rgen) rgen.onclick = async () => {
    rgen.disabled = true; rgen.textContent = "⏳ Bohr redactando…";
    const msg = root.querySelector("#cv-regen-msg");
    const { ok, body } = await post(`/portal/api/projects/${encodeURIComponent(pid)}/report/regenerate`, {});
    if (msg) msg.textContent = ok ? (body.message || "generando — refresca en ~1 min") : "no se pudo regenerar";
    if (!ok) { rgen.disabled = false; rgen.textContent = "🔁 Regenerar informe"; }
  };
  // ⬇ PDF: ventana de impresión con formato de paper → "Guardar como PDF"
  const rpdf = root.querySelector("#cv-report-pdf");
  if (rpdf) rpdf.onclick = () => {
    const md = (d.report && d.report.markdown) || "";
    const html = esc(md)
      .replace(/^### (.*)$/gm, "<h3>$1</h3>").replace(/^## (.*)$/gm, "<h2>$1</h2>")
      .replace(/^# (.*)$/gm, "<h1>$1</h1>").replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
      .replace(/^&gt; (.*)$/gm, "<blockquote>$1</blockquote>")
      .replace(/^- (.*)$/gm, "<li>$1</li>").replace(/^---$/gm, "<hr>")
      .replace(/\n/g, "\n");
    const w = window.open("", "_blank");
    if (!w) { alert("El navegador bloqueó la ventana — permite pop-ups para descargar el PDF."); return; }
    w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Informe de Bohr — ACERO</title>
      <style>body{font-family:Georgia,'Times New Roman',serif;max-width:760px;margin:36px auto;padding:0 28px;color:#1a1a1a;line-height:1.65;font-size:13.5px}
      h1{font-size:22px;border-bottom:2px solid #333;padding-bottom:8px}h2{font-size:16px;margin-top:22px}h3{font-size:14px}
      li{margin:4px 0 4px 18px}blockquote{border-left:3px solid #999;margin:8px 0;padding:4px 14px;color:#444;font-style:italic}
      hr{border:none;border-top:1px solid #bbb;margin:20px 0}pre{white-space:pre-wrap}
      .meta{color:#666;font-size:11px;margin-bottom:18px}</style></head>
      <body><div class="meta">ACERO · Consejo de Investigación · generado ${new Date().toLocaleString()}</div>
      <pre style="font-family:inherit">${html}</pre>
      <script>window.onload=()=>setTimeout(()=>window.print(),300)</`+`script></body></html>`);
    w.document.close(); w.focus();
  };
  // ¿ya hay un ciclo de Bohr vivo? Misma regla que el candado del backend
  // (investigator_bridge.cycle_running: sin done y con latido <6h) -- para que el
  // botón NO invite a lanzar un segundo ciclo que el servidor va a rechazar solo.
  function bohrCycleRunning() {
    const lv = d.live;
    if (!lv || lv.done) return false;
    const ts = Number(lv.ts) || 0;
    return ts > 0 && (Date.now() / 1000 - ts) < 6 * 3600;
  }

  function open(id) {
    const p = byId[id]; if (!p) return; const col = SC[p.status];
    const held = (d.balls || []).filter((b) => b.persona === id).map((b) => b.id);
    const bohrRunning = id === "bohr" && bohrCycleRunning();
    drawer.innerHTML = `<div class="cv-dh"><div class="cv-df">${face(p, 76)}</div>
      <div><div class="cv-dn">${p.name}</div><div class="cv-dr">${p.role}</div><div class="cv-dm">${p.module}</div></div>
      <button class="cv-close" id="cv-x">✕</button></div>
      <div class="cv-db"><div class="cv-dsum">${p.summary}</div>
        <button id="cv-persona-dash" style="background:#1b2438;border:1px solid #c8863c;color:#e0a96d;border-radius:10px;padding:11px 14px;font-weight:600;font-size:13px;cursor:pointer;text-align:left;display:flex;align-items:center;gap:8px">📋 Abrir el tablero de ${esc(p.name)} <span style="color:#93a1bd;font-weight:400">— fichas para dar seguimiento →</span></button>
        ${id === "bohr" ? (bohrRunning
          ? `<button id="cv-investigate" disabled style="background:#233022;color:#7fb88a;border:1px solid #33422f;border-radius:10px;padding:11px 14px;font-weight:700;font-size:14px;cursor:not-allowed">✓ El Consejo YA está trabajando en esto</button><div id="cv-inv-msg" style="font-size:12px;color:#93a1bd">Un ciclo sigue vivo (latido reciente) — lanzar otro duplicaría el gasto. Espera a que termine.</div>`
          : `<button id="cv-investigate" style="background:#e0a96d;color:#0d121e;border:0;border-radius:10px;padding:11px 14px;font-weight:700;font-size:14px;cursor:pointer">▶ Investigar esta conjetura (correr el ciclo)</button><div id="cv-inv-msg" style="font-size:12px;color:#93a1bd"></div>`) : ""}
        ${id === "ramanujan" ? `<div style="display:flex;flex-direction:column;gap:8px"><textarea id="cv-spark-txt" rows="3" placeholder="Describe la FRONTERA: ¿qué es lo que 'no se puede' con los métodos actuales y por qué?" style="background:#0d121e;border:1px solid #2a3550;border-radius:10px;color:#e8edf7;padding:10px;font-size:13px;resize:vertical"></textarea><button id="cv-spark" style="background:#e8b23c;color:#0d121e;border:0;border-radius:10px;padding:11px 14px;font-weight:700;font-size:14px;cursor:pointer">💡 Buscar la chispa (¿y si sí?)</button><div id="cv-spark-msg" style="font-size:12px;color:#93a1bd"></div></div>` : ""}
        ${id === "mendeleev" ? `<div style="display:flex;flex-direction:column;gap:6px"><div class="cv-st">🕸 mapa de patrones — EN VIVO</div><canvas id="cv-patgraph" width="380" height="300" style="width:100%;background:#0d121e;border:1px solid #2a3550;border-radius:12px"></canvas><div id="cv-patgraph-msg" style="font-size:11.5px;color:#93a1bd;line-height:1.4"></div><div style="font-size:11px;color:#5f6d88">Patrón ≠ descubrimiento: cada rombo es un CANDIDATO con causalidad NO establecida y rivales H1-H4. El Consejo intenta destruirlo antes de creerle.</div></div>` : ""}
        <div class="cv-flow"><div><div class="cv-k">recibe de</div><div class="cv-v">${p.awaits}</div></div>
          <div><div class="cv-k">le pasa a</div><div class="cv-v">${p.hands_to}</div></div></div>
        ${held.length ? `<div><div class="cv-st">tiene la pelota</div><div style="font-size:13px;color:#cfd8ea">Trabaja ahora: <b style="color:${col}">${held.join(", ")}</b></div></div>` : ""}
        ${(p.story && p.story.length) ? `<div><div class="cv-st">🗣 mi trabajo, hipótesis por hipótesis</div>${
          p.story.map((s) => `<div class="cv-task"><span class="cv-tt" style="font-size:12.5px;line-height:1.45">${esc(s)}</span></div>`).join("")
        }</div>` : ""}
        ${p.items_label
          ? `<div><div class="cv-st">${esc(p.items_label)} del proyecto${p.items_count ? " (" + p.items_count + ")" : ""}</div>${
              (p.items && p.items.length)
                ? `<div class="cv-fiches">${p.items.map((it) => {
                    const vc = VC[it.verdict] || "#93a1bd";
                    return `<div class="cv-fiche" style="--fc:${it.verdict ? vc : "#5f6d88"}">
                      <div class="cv-fiche-t">${esc(it.title)}</div>
                      ${(it.verdict || it.by) ? `<div class="cv-fiche-m">${it.verdict ? `<span class="cv-chip" style="color:${vc}">${esc(it.verdict)}</span>` : ""}${it.by ? `<span class="cv-by">· ${esc(it.by)}</span>` : ""}</div>` : ""}</div>`;
                  }).join("")}</div>`
                : `<div class="cv-note">Aún no hay ${esc(p.items_label)}. Abre <b>🎩 Bohr</b> y pulsa <b>Investigar</b> para que el Consejo las genere.</div>`
            }</div>`
          : `<div><div class="cv-st">cómo contribuye</div><div class="cv-note">${esc(p.name)} no acumula fichas propias: trabaja lo que recibe de <b>${esc(p.awaits)}</b> y lo pasa a <b>${esc(p.hands_to)}</b>.</div></div>`}
        <div><div class="cv-st">avance en este proyecto</div>
          <div style="display:flex;align-items:center;gap:14px;margin-top:8px">
            <div style="position:relative;width:54px;height:54px">${ring(p.progress, col, 54, 5)}<b style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:13px">${p.progress}</b></div>
            <div style="color:#93a1bd;font-size:13px">capacidad <b style="color:${col}">${SL[p.status]}</b> · <span style="color:#5f6d88">${p.source === "project" ? "avance real" : "sin actividad aún"}</span></div></div></div>
        <div><div class="cv-st">tareas</div>${(p.tasks || []).map((t) => `<div class="cv-task"><span class="cv-tb" style="background:${TASK[t[1]][0]}"></span><span class="cv-tt">${t[0]}</span><span class="cv-ts">${TASK[t[1]][1]}</span></div>`).join("")}</div></div>`;
    drawer.classList.add("open"); scrim.classList.add("open"); drawer.querySelector("#cv-x").onclick = close;
    stopPatternGraph();
    const patCv = drawer.querySelector("#cv-patgraph");
    if (patCv) startPatternGraph(patCv, drawer.querySelector("#cv-patgraph-msg"));
    const pdash = drawer.querySelector("#cv-persona-dash");
    if (pdash) pdash.onclick = () => { close(); openPersonaDash(id); };
    const inv = drawer.querySelector("#cv-investigate");
    if (inv) inv.onclick = async () => {
      inv.disabled = true; inv.textContent = "Convocando al Consejo…";
      const msg = drawer.querySelector("#cv-inv-msg");
      const { ok, body } = await post(`/portal/api/projects/${encodeURIComponent(pid)}/investigate`, {});
      inv.textContent = ok ? "✓ El Consejo está trabajando" : "▶ Investigar esta conjetura";
      inv.disabled = !ok;
      if (msg) msg.textContent = ok
        ? (body.message || "Refresca en un minuto para ver hipótesis y veredicto.")
        : ((body && (body.detail || body.error)) || "No se pudo iniciar. ¿El proyecto tiene un tema?");
    };
    const spk = drawer.querySelector("#cv-spark");
    if (spk) spk.onclick = async () => {
      const txt = drawer.querySelector("#cv-spark-txt");
      const msg = drawer.querySelector("#cv-spark-msg");
      const frontier = (txt && txt.value || "").trim();
      if (!frontier) { if (msg) msg.textContent = "Describe primero la frontera (¿qué 'no se puede'?)."; return; }
      spk.disabled = true; spk.textContent = "Chispeando…";
      const { ok, body } = await post(`/portal/api/projects/${encodeURIComponent(pid)}/spark`, { frontier });
      spk.textContent = ok ? "✓ Ramanujan y Turing trabajando" : "💡 Buscar la chispa (¿y si sí?)";
      spk.disabled = !ok;
      if (msg) msg.textContent = ok
        ? (body.message || "Sigue el avance en la barra EN VIVO.")
        : ((body && (body.detail || body.error)) || "No se pudo lanzar la chispa.");
    };
  }
  function close() { stopPatternGraph(); drawer.classList.remove("open"); scrim.classList.remove("open"); }

  // ---- 🕸 mapa de patrones de Mendeleev: grafo de fuerzas EN VIVO (canvas puro) ----
  let _patTimer = null, _patAnim = null;
  function stopPatternGraph() {
    if (_patTimer) { clearInterval(_patTimer); _patTimer = null; }
    if (_patAnim) { cancelAnimationFrame(_patAnim); _patAnim = null; }
  }
  function startPatternGraph(canvas, msgEl) {
    stopPatternGraph();
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    let nodes = [], edges = [], byId2 = {};
    const sync = (g) => {
      const seen = new Set();
      (g.nodes || []).forEach((n) => {
        seen.add(n.id);
        if (byId2[n.id]) { Object.assign(byId2[n.id], n); return; }
        const node = { ...n, x: W / 2 + (Math.random() - 0.5) * 120,
                       y: H / 2 + (Math.random() - 0.5) * 120, vx: 0, vy: 0 };
        byId2[n.id] = node; nodes.push(node);
      });
      nodes = nodes.filter((n) => seen.has(n.id));
      byId2 = Object.fromEntries(nodes.map((n) => [n.id, n]));
      edges = (g.edges || []).filter((e) => byId2[e.source] && byId2[e.target]);
      if (msgEl) msgEl.textContent = g.n_patterns
        ? `${g.n_patterns} patrón(es) candidato(s) · rombo = patrón (tamaño = soporte, borde grueso = +vistas independientes) · círculo = variable`
        : "Aún sin patrones — cuando Mendeleev analice datos, el mapa se dibuja solo aquí.";
    };
    const fetchGraph = async () => {
      try {
        const r = await fetch(`/portal/api/projects/${encodeURIComponent(pid)}/patterns/graph`, { credentials: "same-origin" });
        if (r.ok) sync(await r.json());
      } catch (e) { /* siguiente tick */ }
    };
    const step = () => {
      // fuerzas: repulsión entre todos + resorte por arista + gravedad al centro
      for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        let dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy + 0.01, d = Math.sqrt(d2);
        const f = 1200 / d2;
        dx /= d; dy /= d; a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f;
      }
      edges.forEach((e) => {
        const a = byId2[e.source], b = byId2[e.target];
        let dx = b.x - a.x, dy = b.y - a.y, d = Math.sqrt(dx * dx + dy * dy) + 0.01;
        const f = (d - 70) * 0.02 * (0.5 + (e.weight || 0.5));
        dx /= d; dy /= d; a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f;
      });
      nodes.forEach((n) => {
        n.vx += (W / 2 - n.x) * 0.002; n.vy += (H / 2 - n.y) * 0.002;
        n.vx *= 0.85; n.vy *= 0.85; n.x += n.vx; n.y += n.vy;
        n.x = Math.max(14, Math.min(W - 14, n.x)); n.y = Math.max(14, Math.min(H - 14, n.y));
      });
      ctx.clearRect(0, 0, W, H);
      ctx.lineCap = "round";
      edges.forEach((e) => {
        const a = byId2[e.source], b = byId2[e.target];
        ctx.strokeStyle = `rgba(63,174,140,${0.15 + 0.5 * (e.weight || 0.4)})`;
        ctx.lineWidth = 0.5 + 2.5 * (e.weight || 0.4);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      });
      nodes.forEach((n) => {
        if (n.type === "pattern") {
          const s = 6 + 10 * (n.support || 0.5);
          ctx.save(); ctx.translate(n.x, n.y); ctx.rotate(Math.PI / 4);
          ctx.fillStyle = n.ptype === "ley" ? "#e8b23c" : (n.ptype === "invariante" ? "#b07cc6" : "#e0a96d");
          ctx.fillRect(-s / 2, -s / 2, s, s);
          ctx.strokeStyle = "#eef2fb"; ctx.lineWidth = (n.views || 1) > 1 ? 2.2 : 0.8;
          ctx.strokeRect(-s / 2, -s / 2, s, s); ctx.restore();
        } else {
          ctx.fillStyle = "#3fae8c"; ctx.beginPath(); ctx.arc(n.x, n.y, 5, 0, 7); ctx.fill();
        }
        ctx.fillStyle = "#93a1bd"; ctx.font = "9.5px ui-monospace,monospace";
        ctx.fillText((n.label || "").slice(0, 26), n.x + 8, n.y + 3);
      });
      _patAnim = requestAnimationFrame(step);
    };
    fetchGraph(); step();
    _patTimer = setInterval(fetchGraph, 4000);   // EN VIVO: nuevos patrones aparecen solos
  }
  scrim.onclick = close; document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  root.querySelectorAll(".cv-med").forEach((m) => {
    m.onclick = () => open(m.dataset.id);
    m.ondblclick = () => { close(); openPersonaDash(m.dataset.id); };
    m.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(m.dataset.id); } };
  });
  root.querySelectorAll(".cv-ball").forEach((b) => {
    b.onclick = () => open(b.dataset.id);
    b.ondblclick = () => { close(); openPersonaDash(b.dataset.id); };
  });
  // caritas del riel de flujo → resumen del personaje
  root.querySelectorAll(".cv-fface[data-id]").forEach((ff) => {
    ff.style.cursor = "pointer";
    ff.onclick = () => open(ff.dataset.id);
  });
  // Apertura directa de un personaje (p.ej. Bohr tras crear la investigación desde el chat).
  if (opts && opts.openPersona && byId[opts.openPersona]) open(opts.openPersona);

  // --- EN VIVO: refresca solo el Consejo cada 6 s mientras esta vista siga en pantalla
  // (si el cajón O el informe están abiertos se salta el ciclo — no te cierra la lectura).
  if (_pollTimer) clearInterval(_pollTimer);
  _pollTimer = setInterval(async () => {
    if (!document.body.contains(root)) { clearInterval(_pollTimer); _pollTimer = null; return; }
    if (drawer.classList.contains("open")) return;
    const rp2 = root.querySelector("#cv-report");
    if (rp2 && !rp2.hidden) return;              // leyendo el informe → no refrescar
    const rl2 = root.querySelector("#cv-rail");
    if (rl2 && rl2.classList.contains("cv-rail-maxed")) return;  // riel maximizado → no refrescar (te lo cerraría)
    try {
      const r2 = await fetch(`/portal/api/projects/${encodeURIComponent(pid)}/council`,
        { headers: { Accept: "application/json" } });
      if (r2.ok) { const nd = await r2.json(); if (nd && nd.phases) renderCouncil(view, pid, cb); }
    } catch (e) { /* red caída: reintenta al siguiente tick */ }
  }, 6000);

  const cvs = root.querySelector(".cv-stars"), x = cvs.getContext("2d");
  requestAnimationFrame(() => { cvs.width = root.clientWidth; cvs.height = root.clientHeight; for (let i = 0; i < 130; i++) { const a = Math.random() * cvs.width, b = Math.random() * cvs.height * 0.55, r = Math.random() * 1.3; x.globalAlpha = Math.random() * 0.7 + 0.15; x.fillStyle = Math.random() > 0.85 ? "#e0a96d" : "#cfe0ff"; x.beginPath(); x.arc(a, b, r, 0, 6.28); x.fill(); } x.globalAlpha = 1; });
}
