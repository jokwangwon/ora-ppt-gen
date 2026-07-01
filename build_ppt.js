#!/usr/bin/env node
/**
 * 슬라이드 스펙(JSON) → PPTX 렌더. 파이프라인 2단계.
 *
 * 디자인은 참고 템플릿(Slate + Oracle Red, 맑은 고딕)을 따른다. 좌표 계획은
 * layout.js가 담당(프리뷰 QA와 동일 기하). 이 파일은 "그리기"만 한다.
 *
 * 사용법: node build_ppt.js out/sql_tuning.slides.json -o out/sql_tuning.pptx
 */

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const sharp = require("sharp");
const L = require("./layout");
const { W, H, M } = L;

// ── 팔레트 (참고 슬라이드에서 추출) ───────────────────────────────
const C = {
  ink: "20303F", accent: "C74634", white: "FFFFFF", paper: "FAF8F4",
  muted: "6B6256", muted2: "A79E90", dark: "2C3742",
  card: "F4F1EA", line: "E7E1D6", tint: "FBE7DE", tint2: "E89B8C",
  slate: "334155", codeFg: "E7E2D8", codeComment: "9AA6A0",
  dot1: "EF4444", dot2: "F59E0B", dot3: "22C55E",
};
const FONT = "맑은 고딕";
const MONO = "Consolas";
// 부드러운 그림자 (웜 페이퍼)
const shadow = () => ({ type: "outer", color: "8A7F6A", blur: 12, offset: 2, angle: 90, opacity: 0.14 });
const RAD = 0.12;  // 카드 모서리 반경 (모던: 좀 더 둥글게)

// ── 공통 요소 ────────────────────────────────────────────────────
function brandMark(pres, s) {
  s.addText("ORACLE", { x: 10.61, y: 0.72, w: 1.8, h: 0.3, fontFace: FONT, fontSize: 10, bold: true, color: C.accent, align: "right", valign: "middle", charSpacing: 2, margin: 0 });
}
function footer(s, sl) {
  if (!sl.footer) return;
  s.addText(sl.footer, { x: M, y: 6.95, w: 7, h: 0.3, fontFace: FONT, fontSize: 9, color: C.muted, align: "left", valign: "middle", margin: 0 });
  if (sl.deckPage) s.addText(String(sl.deckPage).padStart(2, "0"), { x: W - M - 1, y: 6.95, w: 1, h: 0.3, fontFace: FONT, fontSize: 9, color: C.muted, align: "right", valign: "middle", margin: 0 });
}

// ── 슬라이드 종류 ────────────────────────────────────────────────
function titleSlide(pres, s, sl) {
  s.background = { color: C.dark };
  // 워드마크 (밴드 없이 — 모던 에디토리얼)
  s.addText("ORACLE", { x: M, y: 0.66, w: 4, h: 0.4, fontFace: FONT, fontSize: 13, bold: true, color: C.tint2, align: "left", valign: "middle", charSpacing: 4, margin: 0 });
  if (sl.source) s.addText(sl.source, { x: 7.41, y: 0.66, w: 5, h: 0.4, fontFace: FONT, fontSize: 11, color: C.muted2, align: "right", valign: "middle", margin: 0 });
  // 킥커 액센트 바 + 태그
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 2.62, w: 0.62, h: 0.09, fill: { color: C.accent }, line: { color: C.accent }, rectRadius: 0.045 });
  if (sl.tag) s.addText(sl.tag, { x: M + 0.82, y: 2.5, w: 10.6, h: 0.34, fontFace: FONT, fontSize: 13, color: C.tint2, align: "left", valign: "middle", charSpacing: 1, margin: 0 });
  s.addText(sl.title, { x: M, y: 3.05, w: 11.7, h: 1.9, fontFace: FONT, fontSize: 48, bold: true, color: C.white, align: "left", valign: "top", lineSpacingMultiple: 1.04, margin: 0 });
  if (sl.subtitle) s.addText(sl.subtitle, { x: M, y: 5.15, w: 11.49, h: 0.7, fontFace: FONT, fontSize: 17, color: C.muted2, align: "left", valign: "top", margin: 0 });
  const who = sl.presenter ? sl.presenter : "Oracle DBA 부트캠프";
  s.addText(who, { x: M, y: 6.55, w: 8, h: 0.5, fontFace: FONT, fontSize: 12, color: C.muted2, align: "left", valign: "top", margin: 0 });
}

function sectionSlide(pres, s, sl) {
  s.background = { color: C.dark };
  brandMark(pres, s);
  // 큰 숫자를 옅은 톤으로 뒤에 깔고, 그 위에 킥커 바 + 제목 (모던)
  if (sl.num) s.addText(sl.num, { x: M - 0.05, y: 1.5, w: 5, h: 2.2, fontFace: FONT, fontSize: 130, bold: true, color: C.slate, align: "left", valign: "top", margin: 0 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 4.5, w: 0.62, h: 0.09, fill: { color: C.accent }, line: { color: C.accent }, rectRadius: 0.045 });
  s.addText(sl.title, { x: M, y: 4.75, w: 11.49, h: 0.9, fontFace: FONT, fontSize: 38, bold: true, color: C.white, align: "left", valign: "top", margin: 0 });
  if (sl.subtitle) s.addText(sl.subtitle, { x: M, y: 5.72, w: 11.49, h: 0.6, fontFace: FONT, fontSize: 16, color: C.muted2, align: "left", valign: "top", margin: 0 });
}

function contentHeader(pres, s, sl) {
  // 주장형 헤드라인(assertion). 킥커 액센트 바 + 제목 + 하단 헤어라인 (모던 에디토리얼)
  const longTitle = (sl.title || "").length > 34;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 0.66, w: 0.46, h: 0.08, fill: { color: C.accent }, line: { color: C.accent }, rectRadius: 0.04 });
  s.addText(sl.title, { x: M, y: 0.84, w: 10.2, h: 0.95, fontFace: FONT, fontSize: longTitle ? 19 : 24, bold: true, color: C.ink, align: "left", valign: "top", lineSpacingMultiple: 1.04, margin: 0 });
  brandMark(pres, s);
  if (sl.pages > 1) s.addText(`${sl.page} / ${sl.pages}`, { x: W - M - 2.9, y: 0.66, w: 1.6, h: 0.4, fontFace: FONT, fontSize: 11, color: C.muted2, align: "right", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: M, y: 1.78, w: L.CONTENT_W, h: 0.012, fill: { color: C.line }, line: { color: C.line } });
  footer(s, sl);
}

function roadmapSlide(pres, s, sl) {
  s.background = { color: C.paper };
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 0.66, w: 0.46, h: 0.08, fill: { color: C.accent }, line: { color: C.accent }, rectRadius: 0.04 });
  s.addText("발표 흐름", { x: M, y: 0.84, w: 6, h: 0.55, fontFace: FONT, fontSize: 25, bold: true, color: C.ink, align: "left", valign: "top", margin: 0 });
  s.addText("ROADMAP", { x: M, y: 1.44, w: 6, h: 0.3, fontFace: FONT, fontSize: 11, color: C.muted2, align: "left", charSpacing: 2, margin: 0 });
  brandMark(pres, s);
  s.addShape(pres.shapes.RECTANGLE, { x: M, y: 1.78, w: L.CONTENT_W, h: 0.012, fill: { color: C.line }, line: { color: C.line } });
  footer(s, sl);
  const items = sl.items;
  const cols = items.length > 6 ? 2 : 1;
  const perCol = Math.ceil(items.length / cols);
  const colW = cols === 2 ? 5.55 : 11.49;
  const rowH = Math.min(1.0, (L.CONTENT_H) / perCol);
  items.forEach((it, i) => {
    const col = Math.floor(i / perCol), row = i % perCol;
    const x = M + col * (colW + 0.39);
    const y = L.CONTENT_Y0 + row * rowH;
    s.addText(it.num || String(i + 1).padStart(2, "0"), { x, y, w: 0.9, h: rowH - 0.15, fontFace: FONT, fontSize: 26, bold: true, color: C.accent, align: "left", valign: "top", margin: 0 });
    s.addText(it.title, { x: x + 1.0, y: y + 0.02, w: colW - 1.0, h: 0.4, fontFace: FONT, fontSize: 17, bold: true, color: C.ink, align: "left", valign: "top", margin: 0 });
    if (it.subtitle) s.addText(it.subtitle, { x: x + 1.0, y: y + 0.45, w: colW - 1.0, h: 0.4, fontFace: FONT, fontSize: 12, color: C.muted, align: "left", valign: "top", margin: 0 });
  });
}

function closingSlide(pres, s, sl) {
  s.background = { color: C.dark };
  s.addText("ORACLE", { x: M, y: 0.66, w: 4, h: 0.4, fontFace: FONT, fontSize: 13, bold: true, color: C.tint2, align: "left", valign: "middle", charSpacing: 4, margin: 0 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 2.95, w: 0.62, h: 0.09, fill: { color: C.accent }, line: { color: C.accent }, rectRadius: 0.045 });
  s.addText(sl.title, { x: M, y: 3.25, w: 11.49, h: 1.1, fontFace: FONT, fontSize: 44, bold: true, color: C.white, align: "left", valign: "top", margin: 0 });
  if (sl.subtitle) s.addText(sl.subtitle, { x: M, y: 4.5, w: 11.49, h: 0.7, fontFace: FONT, fontSize: 16, color: C.muted2, align: "left", valign: "top", margin: 0 });
}

// ── 블록 그리기 (좌표는 b.x/b.y/b.w/b.h 확정) ─────────────────────
function drawBullets(pres, s, b) {
  const runs = b.items.map((it) => ({ text: it, options: { bullet: { indent: 16 }, breakLine: true, color: C.ink, fontSize: 16, paraSpaceAfter: 8 } }));
  s.addText(runs, { x: b.x, y: b.y, w: b.w, h: b.h, fontFace: FONT, valign: "top", margin: 0 });
}
function drawTable(pres, s, b) {
  const rows = [];
  if (b.headers.length) rows.push(b.headers.map((c) => ({ text: c, options: { fill: { color: C.ink }, color: C.white, bold: true, fontSize: 12 } })));
  for (const r of b.rows) rows.push(r.map((c) => ({ text: c, options: { color: C.ink, fontSize: 12, fill: { color: C.white } } })));
  s.addTable(rows, { x: b.x, y: b.y, w: b.w, h: b.h, fontFace: FONT, border: { pt: 0.5, color: C.line }, align: "left", valign: "middle", margin: [3, 6, 3, 6], autoPage: false });
}
function drawCallout(pres, s, b) {
  const stripe = b.tone === "why" ? C.accent : C.slate;
  const label = b.head || (b.tone === "why" ? "왜 중요한가" : "기억할 점");
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: b.x, y: b.y, w: b.w, h: b.h, fill: { color: C.card }, line: { color: C.line }, rectRadius: RAD, shadow: shadow() });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: b.x + 0.03, y: b.y + 0.13, w: 0.08, h: b.h - 0.26, fill: { color: stripe }, line: { color: stripe }, rectRadius: 0.04 });
  s.addText(label, { x: b.x + 0.35, y: b.y + 0.22, w: b.w - 0.6, h: 0.4, fontFace: FONT, fontSize: 14, bold: true, color: stripe === C.accent ? C.accent : C.ink, align: "left", valign: "middle", margin: 0 });
  s.addText(b.body, { x: b.x + 0.35, y: b.y + 0.72, w: b.w - 0.6, h: b.h - 0.9, fontFace: FONT, fontSize: 13, color: C.ink, align: "left", valign: "top", margin: 0 });
}
function drawCode(pres, s, b) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: b.x, y: b.y, w: b.w, h: b.h, fill: { color: C.dark }, line: { color: C.dark }, rectRadius: 0.06, shadow: shadow() });
  [C.dot1, C.dot2, C.dot3].forEach((col, i) => s.addShape(pres.shapes.OVAL, { x: b.x + 0.35 + i * 0.25, y: b.y + 0.28, w: 0.13, h: 0.13, fill: { color: col }, line: { color: col } }));
  const runs = b.lines.map((ln) => {
    const t = (ln || " ");
    const isComment = /^\s*(--|#)/.test(t);
    return { text: t === "" ? " " : t, options: { breakLine: true, color: isComment ? C.codeComment : C.codeFg, fontSize: 12.5 } };
  });
  s.addText(runs, { x: b.x + 0.35, y: b.y + 0.72, w: b.w - 0.6, h: b.h - 0.9, fontFace: MONO, align: "left", valign: "top", margin: 0 });
}
function drawFigure(pres, s, b) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: b.x, y: b.y, w: b.w, h: b.h, fill: { color: C.card }, line: { color: C.line }, rectRadius: RAD, shadow: shadow() });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: b.x + 0.03, y: b.y + 0.13, w: 0.08, h: b.h - 0.26, fill: { color: C.accent }, line: { color: C.accent }, rectRadius: 0.04 });
  const parts = [{ text: "다이어그램  ", options: { bold: true, color: C.accent, fontSize: 12 } }];
  if (b.caption) parts.push({ text: b.caption, options: { bold: true, color: C.ink, fontSize: 13 } });
  s.addText(parts, { x: b.x + 0.35, y: b.y + 0.2, w: b.w - 0.6, h: 0.55, fontFace: FONT, align: "left", valign: "top", margin: 0 });
  if (b.summary) s.addText(b.summary, { x: b.x + 0.35, y: b.y + 0.78, w: b.w - 0.6, h: b.h - 0.95, fontFace: FONT, fontSize: 12, color: C.muted, italic: true, align: "left", valign: "top", margin: 0 });
}
function drawAnalogy(pres, s, b) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: b.x, y: b.y, w: b.w, h: b.h, fill: { color: C.tint }, line: { color: C.tint }, rectRadius: RAD, shadow: shadow() });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: b.x + 0.03, y: b.y + 0.13, w: 0.08, h: b.h - 0.26, fill: { color: C.accent }, line: { color: C.accent }, rectRadius: 0.04 });
  s.addText("비유", { x: b.x + 0.35, y: b.y + 0.16, w: 2, h: 0.34, fontFace: FONT, fontSize: 13, bold: true, color: C.accent, align: "left", valign: "middle", margin: 0 });
  s.addText(b.text, { x: b.x + 0.35, y: b.y + 0.56, w: b.w - 0.6, h: b.h - 0.7, fontFace: FONT, fontSize: 14, italic: true, color: C.ink, align: "left", valign: "top", margin: 0 });
}
function drawSteps(pres, s, b) {
  let y = b.y + 0.05;
  b.items.forEach((it, i) => {
    const bh = 0.42 + Math.max(1, Math.ceil((it.body || "").length / 70)) * 0.28;
    s.addShape(pres.shapes.OVAL, { x: b.x, y: y + 0.02, w: 0.4, h: 0.4, fill: { color: C.accent }, line: { color: C.accent } });
    s.addText(it.n || String(i + 1), { x: b.x, y: y + 0.02, w: 0.4, h: 0.4, fontFace: FONT, fontSize: 15, bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    if (it.head) s.addText(it.head, { x: b.x + 0.55, y: y, w: b.w - 0.7, h: 0.38, fontFace: FONT, fontSize: 15, bold: true, color: C.ink, align: "left", valign: "middle", margin: 0 });
    if (it.body) s.addText(it.body, { x: b.x + 0.55, y: y + 0.38, w: b.w - 0.7, h: bh - 0.38, fontFace: FONT, fontSize: 13, color: C.muted, align: "left", valign: "top", margin: 0 });
    y += bh + 0.16;
  });
}
function drawSvg(pres, s, b) {
  // evidence 다이어그램. sharp가 미리 래스터한 PNG(b._png)를 비율 유지·중앙 배치.
  const ar = L.svgAspect(b.svg);
  let w = Math.min(b.w, b.maxw || L.SVG_MAXW), h = w / ar;
  const capH = b.h - (b.caption ? 0.35 : 0);
  if (h > capH) { h = capH; w = h * ar; }
  const x = b.x + (b.w - w) / 2, y = b.y;
  if (b._png) s.addImage({ data: b._png, x, y, w, h });
  if (b.caption) s.addText(b.caption, { x: b.x, y: y + h + 0.06, w: b.w, h: 0.3, fontFace: FONT, fontSize: 11, italic: true, color: C.muted, align: "center", valign: "top", margin: 0 });
}
function drawPlan(pres, s, b) {
  s.addShape(pres.shapes.RECTANGLE, { x: b.x, y: b.y, w: b.w, h: b.h, fill: { color: C.card }, line: { color: C.line }, shadow: shadow() });
  const hdr = [{ text: "실행계획", options: { bold: true, color: C.accent, fontSize: 12 } }];
  if (b.title) hdr.push({ text: `   ${b.title}`, options: { color: C.ink, fontSize: 12, bold: true } });
  if (b.order) hdr.push({ text: `      읽는 순서 ${b.order}`, options: { color: C.muted, fontSize: 11 } });
  s.addText(hdr, { x: b.x + 0.25, y: b.y + 0.12, w: b.w - 0.5, h: 0.32, fontFace: FONT, align: "left", valign: "middle", margin: 0 });
  const runs = b.rows.map((r) => {
    const star = /\*/.test(String(r.id));
    return [
      { text: `${String(r.id).padEnd(4)} `, options: { color: star ? C.accent : C.muted, bold: true } },
      { text: (r.op || ""), options: { color: C.ink } },
      { text: r.name ? `  ${r.name}` : "", options: { color: C.muted } },
      { text: "", options: { breakLine: true } },
    ];
  }).flat();
  s.addText(runs, { x: b.x + 0.25, y: b.y + 0.5, w: b.w - 0.5, h: b.rows.length * 0.3, fontFace: MONO, fontSize: 12, align: "left", valign: "top", margin: 0 });
  if (b.predicate) s.addText(b.predicate, { x: b.x + 0.25, y: b.y + 0.5 + b.rows.length * 0.3, w: b.w - 0.5, h: b.h - 0.5 - b.rows.length * 0.3 - 0.1, fontFace: MONO, fontSize: 11, color: C.muted, align: "left", valign: "top", margin: 0 });
}
function drawBlock(pres, s, b) {
  ({ bullets: drawBullets, table: drawTable, callout: drawCallout, code: drawCode, figure: drawFigure, svg: drawSvg, analogy: drawAnalogy, steps: drawSteps, plan: drawPlan }[b.kind] || (() => {}))(pres, s, b);
}

function contentSlide(pres, s, sl) {
  s.background = { color: C.paper };
  contentHeader(pres, s, sl);
  if (sl.layout === "split") { drawBlock(pres, s, sl.left); drawBlock(pres, s, sl.right); }
  else for (const b of sl.blocks) drawBlock(pres, s, b);
  // Mayer 중복/양식 원리: 상세 설명은 화면이 아니라 발표자 노트로.
  if (sl.notes) s.addNotes(sl.notes);
}

// ── 엔트리 ───────────────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  const inPath = args[0];
  const oIdx = args.indexOf("-o");
  const outPath = oIdx >= 0 ? args[oIdx + 1] : inPath.replace(/\.slides\.json$|\.json$/, ".pptx");
  if (!inPath) { console.error("사용법: node build_ppt.js <spec.json> -o <out.pptx>"); process.exit(1); }

  const spec = JSON.parse(fs.readFileSync(inPath, "utf-8"));
  const planned = L.planDeck(spec);
  const bad = L.overflowReport(planned);
  if (bad.length) console.warn("[build] ⚠ 오버플로 의심:", bad.map((b) => `${b.title}(${b.bottom}/${b.limit})`));

  // svg 블록을 미리 PNG로 래스터(sharp) — 그리기는 동기라 사전 처리 필요.
  for (const sl of planned) {
    const blocks = sl.layout === "split" ? [sl.left, sl.right] : (sl.blocks || []);
    for (const b of blocks) {
      if (b && b.kind === "svg" && b.svg) {
        try {
          const px = Math.round((b.w || 8) * 200);
          const buf = await sharp(Buffer.from(b.svg), { density: 220 }).resize({ width: px }).png().toBuffer();
          b._png = "image/png;base64," + buf.toString("base64");
        } catch (e) { console.warn("[build] ⚠ svg 래스터 실패:", e.message); }
      }
    }
  }

  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "Oracle DBA Study";
  pres.title = spec.title;

  const draw = { title: titleSlide, section: sectionSlide, roadmap: roadmapSlide, closing: closingSlide, content: contentSlide };
  for (const sl of planned) draw[sl.type](pres, pres.addSlide(), sl);

  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  await pres.writeFile({ fileName: outPath });
  console.log(`[build] ${planned.length} slides → ${outPath}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
