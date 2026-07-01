/**
 * 레이아웃 엔진 (렌더러 공유) — 참고 템플릿(Slate + Oracle Red) 그리드 기준.
 *
 * 슬라이드 스펙(JSON)을 받아 좌표가 확정된 슬라이드 목록으로 계획한다.
 * build_ppt.js(pptxgenjs)와 preview.js(HTML QA)가 이 모듈을 공유하므로
 * PPTX와 프리뷰의 기하 배치가 동일하다 → 오버플로/겹침 QA가 신뢰할 수 있다.
 *
 * 단위는 인치. 캔버스 LAYOUT_WIDE(13.33 × 7.5). 참고 슬라이드에서 추출한 그리드:
 *  좌여백 0.92, 콘텐츠 폭 11.49, 제목 y≈0.78, 본문 y0≈1.9, 푸터 y≈6.95.
 */

const W = 13.33, H = 7.5;
const M = 0.92;                 // 좌우 여백 (참고와 동일)
const CONTENT_X = M;
const CONTENT_W = W - 2 * M;    // 11.49
const CONTENT_Y0 = 1.9;
const CONTENT_Y1 = 6.6;         // 푸터(6.95) 위 여유
const CONTENT_H = CONTENT_Y1 - CONTENT_Y0;
const GAP = 0.2;

// 좌/우 2단(참고 slide6): 좌 불릿 7.3, 우 카드 x=8.72 폭 3.69
const SPLIT_LEFT_W = 7.3;
const SPLIT_RIGHT_X = 8.72;
const SPLIT_RIGHT_W = W - M - SPLIT_RIGHT_X; // ≈ 3.69

// ── 높이 추정 (인치) — 한글 16pt 기준 보수적으로 ──────────────────
const cplFor = (w) => Math.max(10, Math.round(w * 4.3)); // 폭당 대략 글자수(한글 여유)
const wrapLines = (s, w) => Math.max(1, Math.ceil((s || "").length / cplFor(w)));

function bulletHeight(items, w = CONTENT_W) {
  let lines = 0;
  for (const it of items) lines += wrapLines(it, w);
  return lines * 0.36 + 0.16;
}
function tableHeight(t) {
  return ((t.headers.length ? 1 : 0) + t.rows.length) * 0.42 + 0.16;
}
function calloutHeight(c, w = CONTENT_W) {
  return 0.52 + wrapLines(c.body, w - 0.7) * 0.3 + 0.32;
}
function codeHeight(c) {
  return 0.55 + c.lines.length * 0.28 + 0.3; // 상단 신호등 여백 포함
}
function figureHeight(f, w = CONTENT_W) {
  return 0.5 + wrapLines(f.caption, w - 0.5) * 0.3 + (f.summary ? wrapLines(f.summary, w - 0.5) * 0.28 : 0) + 0.3;
}
function analogyHeight(a, w = CONTENT_W) {          // 비유 오프너 (P1)
  return 0.5 + wrapLines(a.text, w - 0.9) * 0.3 + 0.2;
}
function stepsHeight(s, w = CONTENT_W) {             // 문제→원인→해결 (P2)
  let h = 0.1;
  for (const it of s.items) h += 0.42 + wrapLines(it.body || "", w - 1.1) * 0.28 + 0.16;
  return h;
}
function planHeight(p, w = CONTENT_W) {              // 실행계획 표 (P3)
  const pred = p.predicate ? wrapLines(p.predicate, w - 0.9) * 0.26 + 0.2 : 0;
  return 0.5 + p.rows.length * 0.3 + pred + 0.25;
}
function svgAspect(svg) {                            // viewBox → 가로/세로 비 (작은/큰따옴표 모두)
  const m = /viewBox\s*=\s*['"]\s*[\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)/.exec(svg || "");
  return m ? (+m[1]) / (+m[2]) : 2.5;
}
const SVG_MAXW = 8.8;                                // 다이어그램 최대 폭(가로로 안 늘어나게 중앙 배치)
function svgHeight(b, w = CONTENT_W) {               // 다이어그램(evidence) — 비율로 높이 산정
  if (b.h) return b.h;
  const effW = Math.min(w, b.maxw || SVG_MAXW);
  let h = effW / svgAspect(b.svg);
  const cap = CONTENT_H - (b.caption ? 0.4 : 0.1);
  if (h > cap) h = cap;
  return h + (b.caption ? 0.35 : 0);
}
function blockHeight(b, w = CONTENT_W) {
  switch (b.kind) {
    case "bullets": return bulletHeight(b.items, w);
    case "table": return tableHeight(b);
    case "callout": return calloutHeight(b, w);
    case "code": return codeHeight(b);
    case "figure": return figureHeight(b, w);
    case "svg": return svgHeight(b, w);
    case "analogy": return analogyHeight(b, w);
    case "steps": return stepsHeight(b, w);
    case "plan": return planHeight(b, w);
    default: return 0.5;
  }
}

// ── 큰 블록 분할 (한 슬라이드에 담기게) ───────────────────────────
function splitBlock(b) {
  const MAXH = CONTENT_H - 0.15;
  if (b.kind === "bullets") {
    const out = []; let cur = [], h = 0;
    for (const it of b.items) {
      const ih = wrapLines(it, CONTENT_W) * 0.36;
      if (h + ih > MAXH && cur.length) { out.push({ kind: "bullets", items: cur }); cur = []; h = 0; }
      cur.push(it); h += ih;
    }
    if (cur.length) out.push({ kind: "bullets", items: cur });
    return out;
  }
  if (b.kind === "table") {
    const per = Math.max(3, Math.floor((MAXH - 0.6) / 0.42));
    if (b.rows.length <= per) return [b];
    const out = [];
    for (let i = 0; i < b.rows.length; i += per) out.push({ kind: "table", headers: b.headers, rows: b.rows.slice(i, i + per) });
    return out;
  }
  if (b.kind === "code") {
    const per = Math.max(6, Math.floor((MAXH - 0.85) / 0.28));
    if (b.lines.length <= per) return [b];
    const out = [];
    for (let i = 0; i < b.lines.length; i += per) out.push({ kind: "code", lines: b.lines.slice(i, i + per) });
    return out;
  }
  if (b.kind === "steps") {
    const out = []; let cur = [], h = 0.1;
    for (const it of b.items) {
      const ih = 0.42 + wrapLines(it.body || "", CONTENT_W - 1.1) * 0.28 + 0.16;
      if (h + ih > MAXH && cur.length) { out.push({ kind: "steps", items: cur }); cur = []; h = 0.1; }
      cur.push(it); h += ih;
    }
    if (cur.length) out.push({ kind: "steps", items: cur });
    return out;
  }
  if (b.kind === "plan") {
    const per = Math.max(4, Math.floor((MAXH - 1.0) / 0.3));
    if (b.rows.length <= per) return [b];
    const out = [];
    for (let i = 0; i < b.rows.length; i += per) {
      const last = i + per >= b.rows.length;
      out.push({ kind: "plan", title: i === 0 ? b.title : (b.title ? b.title + " (계속)" : ""), rows: b.rows.slice(i, i + per), predicate: last ? b.predicate : "", order: last ? b.order : "" });
    }
    return out;
  }
  return [b];
}

/** content 블록들을 페이지로 나눠 각 페이지에 layout('split'|'stack')과 좌표 부여. */
function planContent(blocks) {
  const flat = (blocks || []).flatMap(splitBlock);

  // 대표 레이아웃: [bullets + (callout|figure)] 정확히 2개이며 각각 콘텐츠 높이에 맞으면 좌/우 2단.
  if (flat.length === 2) {
    const bl = flat.find((b) => b.kind === "bullets");
    const card = flat.find((b) => b.kind === "callout" || b.kind === "figure");
    if (bl && card) {
      const lh = bulletHeight(bl.items, SPLIT_LEFT_W);
      const ch = blockHeight(card, SPLIT_RIGHT_W);
      if (lh <= CONTENT_H && ch <= CONTENT_H) {
        return [{
          layout: "split",
          left: { ...bl, x: CONTENT_X, y: CONTENT_Y0, w: SPLIT_LEFT_W, h: Math.min(lh, CONTENT_H) },
          right: { ...card, x: SPLIT_RIGHT_X, y: CONTENT_Y0, w: SPLIT_RIGHT_W, h: Math.min(ch, CONTENT_H) },
        }];
      }
    }
  }

  // 기본: 세로 스택 + 용량 페이지네이션
  const pages = []; let cur = [], y = CONTENT_Y0;
  for (const b of flat) {
    const h = blockHeight(b, CONTENT_W);
    if (y + h > CONTENT_Y1 && cur.length) { pages.push(cur); cur = []; y = CONTENT_Y0; }
    cur.push({ ...b, x: CONTENT_X, y, w: CONTENT_W, h });
    y += h + GAP;
  }
  if (cur.length) pages.push(cur);

  // 의도적 여백(Reynolds/Duarte): 내용이 콘텐츠 밴드보다 짧으면 수직 중앙으로 내려
  // 위에 붙고 아래가 뻥 뚫린 '사고성 여백'을 '프레임형 여백'으로 바꾼다.
  for (const pg of pages) {
    const used = pg[pg.length - 1].y + pg[pg.length - 1].h - CONTENT_Y0;
    const slack = CONTENT_H - used;
    if (slack > 0.4) { const off = slack / 2; for (const b of pg) b.y += off; }
  }
  return (pages.length ? pages : [[]]).map((blocks) => ({ layout: "stack", blocks }));
}

/** 스펙 전체 → 좌표 확정된 슬라이드 목록 (+ 로드맵/감사 슬라이드). */
function planDeck(spec) {
  const slides = [];
  const footer = `Oracle DBA · ${spec.footer || spec.title}`;

  // 섹션 목록(로드맵용)
  const sections = spec.slides.filter((s) => s.type === "section").map((s) => ({ num: s.num, title: s.title, subtitle: s.subtitle }));

  spec.slides.forEach((sl) => {
    if (sl.type === "title") {
      slides.push({ type: "title", title: spec.title, subtitle: spec.subtitle, source: spec.source, tag: spec.tag || "Oracle DBA 학습 정리", presenter: spec.presenter || "" });
      if (sections.length >= 2) slides.push({ type: "roadmap", items: sections, footer });
    } else if (sl.type === "section") {
      slides.push({ type: "section", num: sl.num, title: sl.title, subtitle: sl.subtitle });
    } else if (sl.type === "content") {
      const pages = planContent(sl.blocks);
      pages.forEach((pg, pi) => slides.push({ type: "content", title: sl.title, page: pi + 1, pages: pages.length, footer, notes: pi === 0 ? sl.notes : undefined, ...pg }));
    }
  });

  slides.push({ type: "closing", title: "감사합니다", subtitle: spec.closing || "질문이 있으면 편하게 말씀해 주세요.", footer });
  // 콘텐츠 슬라이드에 문서 전체 페이지 번호 부여
  let pageNo = 0;
  slides.forEach((s) => { if (s.type === "content") s.deckPage = ++pageNo; });
  return slides;
}

/** QA 보조: content 스택 슬라이드가 콘텐츠 영역을 넘치는지 수치 점검. */
function overflowReport(planned) {
  const bad = [];
  planned.forEach((s, i) => {
    if (s.type !== "content" || s.layout !== "stack" || !s.blocks.length) return;
    const last = s.blocks[s.blocks.length - 1];
    const bottom = last.y + last.h;
    if (bottom > CONTENT_Y1 + 0.03) bad.push({ i, title: s.title, bottom: +bottom.toFixed(2), limit: CONTENT_Y1 });
  });
  return bad;
}

module.exports = {
  W, H, M, CONTENT_X, CONTENT_W, CONTENT_Y0, CONTENT_Y1, CONTENT_H, GAP,
  SPLIT_LEFT_W, SPLIT_RIGHT_X, SPLIT_RIGHT_W,
  blockHeight, splitBlock, planContent, planDeck, overflowReport,
  svgAspect, svgHeight, SVG_MAXW,
};
