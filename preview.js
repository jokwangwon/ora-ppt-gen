#!/usr/bin/env node
/**
 * QA 프리뷰: 슬라이드 스펙 → HTML(동일 좌표) → 슬라이드별 PNG (Chromium).
 *
 * LibreOffice 변환이 막힌 환경에서 시각 QA를 하기 위한 도구. layout.js의 좌표를
 * 그대로 써서 PPTX와 배치가 동일하므로 오버플로/겹침 검수가 신뢰할 수 있다.
 * (한글은 브라우저의 WenQuanYi 폰트로 렌더 — 맑은 고딕의 근사 프록시)
 *
 * 사용법: node preview.js out/sql_tuning.slides.json           # out/qa/*.png + out/preview.html
 */

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright-core");
const L = require("./layout");
const { W, H, M } = L;

const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const C = {
  ink: "#20303F", accent: "#C74634", white: "#FFFFFF", paper: "#FAF8F4", muted: "#6B6256", muted2: "#A79E90",
  dark: "#2C3742", card: "#F4F1EA", line: "#E7E1D6", tint: "#FBE7DE", tint2: "#E89B8C",
  slate: "#334155", codeFg: "#E7E2D8", codeComment: "#9AA6A0",
  dot1: "#EF4444", dot2: "#F59E0B", dot3: "#22C55E",
};
const esc = (s) => String(s == null ? "" : s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
const box = (x, y, w, h, style, inner = "") =>
  `<div style="position:absolute;left:${x}in;top:${y}in;width:${w}in;height:${h}in;${style}">${inner}</div>`;
const txt = (x, y, w, h, size, color, extra, s) =>
  box(x, y, w, h, `font-size:${size}pt;color:${color};${extra || ""}`, esc(s));

function brand() { return txt(10.61, 0.72, 1.8, 0.3, 10, C.accent, "font-weight:700;text-align:right;letter-spacing:2px;display:flex;align-items:center;justify-content:flex-end", "ORACLE"); }
function footer(sl) {
  if (!sl.footer) return "";
  let h = txt(M, 6.95, 7, 0.3, 9, C.muted, "display:flex;align-items:center", sl.footer);
  if (sl.deckPage) h += txt(W - M - 1, 6.95, 1, 0.3, 9, C.muted, "text-align:right;display:flex;align-items:center;justify-content:flex-end", String(sl.deckPage).padStart(2, "0"));
  return h;
}

function slideTitle(sl) {
  let h = txt(M, 0.66, 4, 0.4, 13, C.tint2, "font-weight:700;letter-spacing:4px;display:flex;align-items:center", "ORACLE");
  if (sl.source) h += txt(7.41, 0.66, 5, 0.4, 11, C.muted2, "text-align:right;display:flex;align-items:center;justify-content:flex-end", sl.source);
  h += box(M, 2.62, 0.62, 0.09, `background:${C.accent};border-radius:5px`);
  if (sl.tag) h += txt(M + 0.82, 2.5, 10.6, 0.34, 13, C.tint2, "letter-spacing:1px;display:flex;align-items:center", sl.tag);
  h += txt(M, 3.05, 11.7, 1.9, 48, C.white, "font-weight:700;line-height:1.04", sl.title);
  if (sl.subtitle) h += txt(M, 5.15, 11.49, 0.7, 17, C.muted2, "", sl.subtitle);
  h += txt(M, 6.55, 8, 0.5, 12, C.muted2, "", sl.presenter || "Oracle DBA 부트캠프");
  return { bg: C.dark, inner: h };
}
function slideSection(sl) {
  let h = brand();
  if (sl.num) h += txt(M - 0.05, 1.5, 5, 2.2, 130, C.slate, "font-weight:700;line-height:1", sl.num);
  h += box(M, 4.5, 0.62, 0.09, `background:${C.accent};border-radius:5px`);
  h += txt(M, 4.75, 11.49, 0.9, 38, C.white, "font-weight:700", sl.title);
  if (sl.subtitle) h += txt(M, 5.72, 11.49, 0.6, 16, C.muted2, "", sl.subtitle);
  return { bg: C.dark, inner: h };
}
function slideRoadmap(sl) {
  let h = box(M, 0.66, 0.46, 0.08, `background:${C.accent};border-radius:4px`);
  h += txt(M, 0.84, 6, 0.55, 25, C.ink, "font-weight:700", "발표 흐름");
  h += txt(M, 1.44, 6, 0.3, 11, C.muted2, "letter-spacing:2px", "ROADMAP");
  h += brand() + footer(sl);
  h += box(M, 1.78, L.CONTENT_W, 0.012, `background:${C.line}`);
  const items = sl.items, cols = items.length > 6 ? 2 : 1, perCol = Math.ceil(items.length / cols);
  const colW = cols === 2 ? 5.55 : 11.49, rowH = Math.min(1.0, L.CONTENT_H / perCol);
  items.forEach((it, i) => {
    const col = Math.floor(i / perCol), row = i % perCol;
    const x = M + col * (colW + 0.39), y = L.CONTENT_Y0 + row * rowH;
    h += txt(x, y, 0.9, rowH - 0.15, 26, C.accent, "font-weight:700", it.num || String(i + 1).padStart(2, "0"));
    h += txt(x + 1.0, y + 0.02, colW - 1.0, 0.4, 17, C.ink, "font-weight:700", it.title);
    if (it.subtitle) h += txt(x + 1.0, y + 0.45, colW - 1.0, 0.4, 12, C.muted, "", it.subtitle);
  });
  return { bg: C.paper, inner: h };
}
function slideClosing(sl) {
  let h = txt(M, 0.66, 4, 0.4, 13, C.tint2, "font-weight:700;letter-spacing:4px;display:flex;align-items:center", "ORACLE");
  h += box(M, 2.95, 0.62, 0.09, `background:${C.accent};border-radius:5px`);
  h += txt(M, 3.25, 11.49, 1.1, 44, C.white, "font-weight:700", sl.title);
  if (sl.subtitle) h += txt(M, 4.5, 11.49, 0.7, 16, C.muted2, "", sl.subtitle);
  return { bg: C.dark, inner: h };
}

// ── 블록 ─────────────────────────────────────────────────────────
function bBullets(b) {
  const items = b.items.map((it) =>
    `<div style="display:flex;margin-bottom:8pt;line-height:1.3"><span style="color:${C.accent};margin-right:8px">▪</span><span>${esc(it)}</span></div>`).join("");
  return box(b.x, b.y, b.w, b.h, `font-size:16pt;color:${C.ink}`, items);
}
function bTable(b) {
  const th = b.headers.length ? `<tr>${b.headers.map((c) => `<th style="background:${C.ink};color:#fff;font-weight:700;padding:4px 6px;text-align:left;border:0.5px solid ${C.line}">${esc(c)}</th>`).join("")}</tr>` : "";
  const tr = b.rows.map((r) => `<tr>${r.map((c) => `<td style="padding:4px 6px;border:0.5px solid ${C.line};color:${C.ink}">${esc(c)}</td>`).join("")}</tr>`).join("");
  return box(b.x, b.y, b.w, b.h, "font-size:12pt", `<table style="width:100%;border-collapse:collapse">${th}${tr}</table>`);
}
function bCallout(b) {
  const stripe = b.tone === "why" ? C.accent : C.slate;
  const label = b.head || (b.tone === "why" ? "왜 중요한가" : "기억할 점");
  const inner = `<div style="font-size:14pt;font-weight:700;color:${stripe === C.accent ? C.accent : C.ink};margin-bottom:8px">${esc(label)}</div>`
    + `<div style="font-size:13pt;color:${C.ink};line-height:1.35">${esc(b.body)}</div>`;
  return box(b.x, b.y, b.w, b.h, `background:${C.card};border:1px solid ${C.line};border-left:6px solid ${stripe};border-radius:12px;padding:14px 18px 14px 20px;box-shadow:0 4px 14px rgba(138,127,106,.16);box-sizing:border-box;overflow:hidden`, inner);
}
function bCode(b) {
  const dots = [C.dot1, C.dot2, C.dot3].map((c) => `<span style="width:11px;height:11px;border-radius:50%;background:${c};display:inline-block;margin-right:6px"></span>`).join("");
  const lines = b.lines.map((ln) => { const t = ln || " "; const cmt = /^\s*(--|#)/.test(t); return `<div style="color:${cmt ? C.codeComment : C.codeFg};white-space:pre">${esc(t)}</div>`; }).join("");
  return box(b.x, b.y, b.w, b.h, `background:${C.dark};border-radius:12px;padding:12px 16px;box-shadow:0 4px 14px rgba(138,127,106,.18);box-sizing:border-box;overflow:hidden`,
    `<div style="margin-bottom:8px">${dots}</div><div style="font-family:'WenQuanYi Zen Hei Mono',monospace;font-size:12.5pt;line-height:1.35">${lines}</div>`);
}
function bFigure(b) {
  const inner = `<div style="font-size:13pt"><b style="color:${C.accent}">다이어그램</b>&nbsp;&nbsp;<b style="color:${C.ink}">${esc(b.caption)}</b></div>`
    + (b.summary ? `<div style="font-size:12pt;color:${C.muted};font-style:italic;margin-top:6px;line-height:1.3">${esc(b.summary)}</div>` : "");
  return box(b.x, b.y, b.w, b.h, `background:${C.card};border:1px solid ${C.line};border-left:6px solid ${C.accent};border-radius:12px;padding:12px 18px 12px 20px;box-shadow:0 4px 14px rgba(138,127,106,.16);box-sizing:border-box;overflow:hidden`, inner);
}
function bAnalogy(b) {
  const inner = `<div style="font-size:13pt;font-weight:700;color:${C.accent};margin-bottom:6px">비유</div>`
    + `<div style="font-size:14pt;font-style:italic;color:${C.ink};line-height:1.35">${esc(b.text)}</div>`;
  return box(b.x, b.y, b.w, b.h, `background:${C.tint};border:1px solid ${C.line};border-left:6px solid ${C.accent};border-radius:12px;padding:12px 18px 12px 20px;box-shadow:0 4px 14px rgba(138,127,106,.16);box-sizing:border-box;overflow:hidden`, inner);
}
function bSteps(b) {
  const rows = b.items.map((it, i) =>
    `<div style="display:flex;margin-bottom:12px">`
    + `<div style="flex:0 0 auto;width:0.4in;height:0.4in;border-radius:50%;background:${C.accent};color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center;font-size:15pt">${esc(it.n || String(i + 1))}</div>`
    + `<div style="margin-left:0.15in">`
    + (it.head ? `<div style="font-size:15pt;font-weight:700;color:${C.ink}">${esc(it.head)}</div>` : "")
    + (it.body ? `<div style="font-size:13pt;color:${C.muted};line-height:1.3">${esc(it.body)}</div>` : "")
    + `</div></div>`).join("");
  return box(b.x, b.y, b.w, b.h, "", rows);
}
function bPlan(b) {
  const hdr = `<div style="font-size:12pt;margin-bottom:6px"><b style="color:${C.accent}">실행계획</b>`
    + (b.title ? `&nbsp;&nbsp;&nbsp;<b style="color:${C.ink}">${esc(b.title)}</b>` : "")
    + (b.order ? `<span style="color:${C.muted};font-size:11pt">&nbsp;&nbsp;&nbsp;&nbsp;읽는 순서 ${esc(b.order)}</span>` : "") + `</div>`;
  const rows = b.rows.map((r) => {
    const star = /\*/.test(String(r.id));
    return `<div style="white-space:pre">`
      + `<span style="color:${star ? C.accent : C.muted};font-weight:700">${esc(String(r.id).padEnd(4))} </span>`
      + `<span style="color:${C.ink}">${esc(r.op || "")}</span>`
      + (r.name ? `<span style="color:${C.muted}">  ${esc(r.name)}</span>` : "") + `</div>`;
  }).join("");
  const pred = b.predicate ? `<div style="color:${C.muted};font-size:11pt;margin-top:6px;white-space:pre-wrap">${esc(b.predicate)}</div>` : "";
  return box(b.x, b.y, b.w, b.h, `background:${C.card};border:1px solid ${C.line};border-radius:12px;padding:10px 14px;box-shadow:0 4px 14px rgba(138,127,106,.16);box-sizing:border-box;overflow:hidden`,
    hdr + `<div style="font-family:'WenQuanYi Zen Hei Mono',monospace;font-size:12pt;line-height:1.35">${rows}</div>${pred}`);
}
function bSvg(b) {
  const capH = b.h - (b.caption ? 0.35 : 0);
  const effW = Math.min(b.w, b.maxw || L.SVG_MAXW);
  const svg = String(b.svg || "").replace("<svg", '<svg style="max-width:100%;max-height:100%;height:auto"');
  const inner = `<div style="width:100%;height:${capH}in;display:flex;align-items:center;justify-content:center">`
    + `<div style="width:${effW}in;max-width:100%;display:flex;align-items:center;justify-content:center">${svg}</div></div>`
    + (b.caption ? `<div style="text-align:center;font-size:11pt;color:${C.muted};font-style:italic;margin-top:3px">${esc(b.caption)}</div>` : "");
  return box(b.x, b.y, b.w, b.h, "box-sizing:border-box", inner);
}
const drawB = { bullets: bBullets, table: bTable, callout: bCallout, code: bCode, figure: bFigure, svg: bSvg, analogy: bAnalogy, steps: bSteps, plan: bPlan };

function slideContent(sl) {
  const longTitle = (sl.title || "").length > 34;
  let h = box(M, 0.66, 0.46, 0.08, `background:${C.accent};border-radius:4px`);
  h += txt(M, 0.84, 10.2, 0.95, longTitle ? 19 : 24, C.ink, "font-weight:700;line-height:1.05", sl.title);
  h += brand() + footer(sl);
  if (sl.pages > 1) h += txt(W - M - 2.9, 0.66, 1.6, 0.4, 11, C.muted2, "text-align:right;display:flex;align-items:center;justify-content:flex-end", `${sl.page} / ${sl.pages}`);
  h += box(M, 1.78, L.CONTENT_W, 0.012, `background:${C.line}`);
  if (sl.layout === "split") h += drawB[sl.left.kind](sl.left) + drawB[sl.right.kind](sl.right);
  else for (const b of sl.blocks) h += (drawB[b.kind] || (() => ""))(b);
  return { bg: C.paper, inner: h };
}

const render = { title: slideTitle, section: slideSection, roadmap: slideRoadmap, closing: slideClosing, content: slideContent };

function buildHtml(planned) {
  const slides = planned.map((sl, i) => {
    const { bg, inner } = render[sl.type](sl);
    return `<div class="slide" data-i="${i}" style="background:${bg}">${inner}</div>`;
  }).join("\n");
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:'WenQuanYi Zen Hei',sans-serif;background:#334}
    .slide{width:${W}in;height:${H}in;position:relative;overflow:hidden;margin:10px auto}
  </style></head><body>${slides}</body></html>`;
}

async function main() {
  const inPath = process.argv[2];
  if (!inPath) { console.error("사용법: node preview.js <spec.json>"); process.exit(1); }
  const spec = JSON.parse(fs.readFileSync(inPath, "utf-8"));
  const planned = L.planDeck(spec);
  const html = buildHtml(planned);
  fs.mkdirSync("out/qa", { recursive: true });
  fs.writeFileSync("out/preview.html", html);

  const browser = await chromium.launch({ executablePath: CHROME, args: ["--no-sandbox"] });
  const page = await browser.newPage({ viewport: { width: 1300, height: 760 }, deviceScaleFactor: 1.5 });
  await page.setContent(html, { waitUntil: "networkidle" });
  const n = await page.locator(".slide").count();
  for (let i = 0; i < n; i++) {
    await page.locator(`.slide[data-i="${i}"]`).screenshot({ path: `out/qa/slide-${String(i + 1).padStart(2, "0")}.png` });
  }
  await browser.close();
  console.log(`[preview] ${n} slides → out/qa/slide-*.png,  out/preview.html`);
}

main().catch((e) => { console.error(e); process.exit(1); });
