"use strict";
// Editor slice page. The server owns the document and its rules (docmodel.py).
// This file only draws the current sheet and turns mouse actions into commands for POST /api/op.
// Page units are millimetres with y up; SVG has y down, so every y is flipped with (H - y).

const NS = "http://www.w3.org/2000/svg";
const S = { meta: null, doc: null, canUndo: false, sheet: 0, sel: null, geo: {}, drag: null, pending: 0 };
let W = 431.8, H = 279.4, renderNo = 0;
const $ = id => document.getElementById(id);
const svg = $("sheet");

function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function status(msg, isError) { $("status").textContent = msg; $("status").className = isError ? "err" : ""; }
const r1 = x => Math.round(x * 10) / 10;

async function api(path, body) {
  const opt = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}

// ---- view geometry: fetched once per camera, kept as ready-made SVG path text ----
const pathD = lines => lines.map(p => "M" + p.map(q => q[0] + " " + q[1]).join("L")).join("");
const geoKey = (cam, up) => cam.join(",") + "|" + up.join(",");
function keep(g) { g.dVis = pathD(g.visible); g.dTan = pathD(g.tangent); return g; }
async function getGeo(cam, up) {
  const k = geoKey(cam, up);
  if (!S.geo[k]) S.geo[k] = keep(await api("/api/view?cam=" + cam.join(",") + "&up=" + up.join(",")));
  return S.geo[k];
}

// ---- the sheet: paper, border, and grey boxes where the engine draws the title and tolerance blocks ----
function drawFrame() {
  svg.setAttribute("viewBox", "-4 -4 " + (W + 8) + " " + (H + 8));
  svg.replaceChildren();
  el("rect", { x: 0, y: 0, width: W, height: H, fill: "#fff", stroke: "#8a929d", "stroke-width": 0.3 }, svg);
  el("rect", { class: "frame", x: 5, y: 5, width: W - 10, height: H - 10, "stroke-width": 0.18 }, svg);
  el("rect", { class: "frame", x: 10, y: 10, width: W - 20, height: H - 20, "stroke-width": 0.7 }, svg);
  for (let i = 1; i < 8; i++) {
    const x = 10 + i * (W - 20) / 8;
    el("line", { class: "frame", x1: x, y1: 5, x2: x, y2: 10, "stroke-width": 0.18 }, svg);
    el("line", { class: "frame", x1: x, y1: H - 5, x2: x, y2: H - 10, "stroke-width": 0.18 }, svg);
  }
  for (let j = 1; j < 4; j++) {
    const y = 10 + j * (H - 20) / 4;
    el("line", { class: "frame", x1: 5, y1: y, x2: 10, y2: y, "stroke-width": 0.18 }, svg);
    el("line", { class: "frame", x1: W - 5, y1: y, x2: W - 10, y2: y, "stroke-width": 0.18 }, svg);
  }
  const tb = W - 10 - 178;                                    // same boxes as the engine's frame()
  el("rect", { class: "ghost", x: tb, y: H - 62, width: 178, height: 52 }, svg);
  el("text", { class: "ghost-t", x: tb + 89, y: H - 35 }, svg).textContent = "TITLE BLOCK (drawn by the engine in the PDF)";
  el("rect", { class: "ghost", x: tb - 92, y: H - 50, width: 92, height: 40 }, svg);
  el("text", { class: "ghost-t", x: tb - 46, y: H - 29 }, svg).textContent = "TOLERANCE BLOCK";
  el("g", { id: "layer" }, svg);
}

function drawView(v, g, sheetScale, layer) {
  const k = v.scale === null ? sheetScale : v.scale;
  const b = g.bbox, w = (b[2] - b[0]) * k, h = (b[3] - b[1]) * k, pad = 3;
  const grp = el("g", { class: "view" + (v.id === S.sel ? " sel" : ""), "data-id": v.id }, layer);
  const T = "translate(" + v.x + " " + (H - v.y) + ") scale(" + k + " " + (-k) + ") translate(" + (-(b[0] + b[2]) / 2) + " " + (-(b[1] + b[3]) / 2) + ")";
  el("path", { class: "geo", d: g.dVis, transform: T, "stroke-width": 0.5 / k }, grp);
  if (g.dTan) el("path", { class: "geo", d: g.dTan, transform: T, "stroke-width": 0.25 / k }, grp);
  el("rect", { class: "hit", "pointer-events": "all", x: v.x - w / 2 - pad, y: H - v.y - h / 2 - pad, width: w + 2 * pad, height: h + 2 * pad }, grp);
  el("text", { x: v.x, y: H - (v.y - h / 2 - 9) + 3.6 }, grp).textContent = v.label;
}

function currentSheet() { return S.doc.sheets[S.sheet]; }
function selected() { return currentSheet().views.find(v => v.id === S.sel) || null; }

async function render() {
  const no = ++renderNo, sh = currentSheet();
  let geos;
  try { geos = await Promise.all(sh.views.map(v => getGeo(v.cam, v.up))); }
  catch (e) { status(e.message, true); return; }
  if (no !== renderNo) return;                                // a newer render started while this one waited
  drawTabs(); drawBar();
  const layer = $("layer"), byId = {};
  layer.replaceChildren();
  sh.views.forEach(v => { byId[v.id] = v; });
  sh.views.forEach(v => {                                     // dashed blue line = this child is linked to its parent
    const p = byId[v.parent];
    if (v.linked && p) el("line", { class: "link", x1: v.x, y1: H - v.y, x2: p.x, y2: H - p.y }, layer);
  });
  sh.views.forEach((v, i) => drawView(v, geos[i], sh.scale, layer));
}

function drawTabs() {
  const tabs = $("tabs");
  tabs.replaceChildren();
  S.doc.sheets.forEach((sh, i) => {
    const b = document.createElement("button");
    b.textContent = "Sheet " + (i + 1) + (i === 0 ? " (title block)" : "");
    if (i === S.sheet) b.className = "on";
    b.onclick = () => { S.sheet = i; S.sel = null; render(); };
    tabs.appendChild(b);
  });
  const add = document.createElement("button"), rem = document.createElement("button");
  add.textContent = "+ Add sheet"; add.onclick = () => run({ op: "add_sheet" });
  rem.textContent = "Remove this sheet"; rem.disabled = S.sheet === 0;
  rem.title = S.sheet === 0 ? "Sheet 1 carries the title block and cannot be removed" : "";
  rem.onclick = () => run({ op: "remove_sheet", sheet: S.sheet });
  tabs.appendChild(add); tabs.appendChild(rem);
}

function drawBar() {
  const v = selected(), sh = currentSheet();
  ["p-left", "p-right", "p-top", "p-bottom", "delete"].forEach(id => { $(id).disabled = !v; });
  $("break").disabled = !(v && v.linked);
  $("undo").disabled = !S.canUndo;
  $("scale").selectedIndex = S.meta.scales.findIndex(s => Math.abs(s.value - sh.scale) < 1e-9);
}

function setSel(id) {
  S.sel = id;
  $("layer").querySelectorAll(".view").forEach(g => g.classList.toggle("sel", Number(g.getAttribute("data-id")) === id));
  drawBar();
}

// ---- commands ----
function applyState(st) {
  S.doc = st.doc; S.canUndo = st.can_undo;
  S.sheet = Math.min(S.sheet, S.doc.sheets.length - 1);
  if (!selected()) S.sel = null;
  return render();
}
// One command at a time: a click made while the server is still answering waits its turn.
let chain = Promise.resolve();
function queue(fn) { S.pending++; chain = chain.then(fn).finally(() => { S.pending--; }); return chain; }
function run(op, done) { return queue(() => runNow(op, done)); }
function undo() { return queue(undoNow); }
async function runNow(op, done) {
  try {
    const st = await api("/api/op", op);
    if (op.op === "place" || op.op === "project") S.sel = st.made;
    if (op.op === "add_sheet") { S.sheet = st.made; S.sel = null; }
    await applyState(st);
    status(done || "Done: " + op.op.replace("_", " "));
  } catch (e) { status(e.message, true); render(); }
}
async function undoNow() {
  try { await applyState(await api("/api/undo", null)); status("Undone"); }
  catch (e) { status(e.message, true); }
}

// ---- mouse: where on the page, moving a placed view ----
function pagePt(ev) {
  const p = svg.createSVGPoint();
  p.x = ev.clientX; p.y = ev.clientY;
  const q = p.matrixTransform(svg.getScreenCTM().inverse());
  return [q.x, H - q.y];
}
function movingIds(sh, v) {                                   // the view plus every linked view below it
  const out = [v.id];
  sh.views.forEach(c => { if (c.parent === v.id && c.linked) out.push(...movingIds(sh, c)); });
  return out;
}
svg.addEventListener("pointerdown", ev => {
  const g = ev.target.closest ? ev.target.closest(".view") : null;
  if (!g) { if (S.doc) setSel(null); return; }
  if (ev.button !== 0 || S.pending) return;                  // no drag while a command is still running
  ev.preventDefault();
  const id = Number(g.getAttribute("data-id")), sh = currentSheet(), v = sh.views.find(x => x.id === id);
  setSel(id);
  const ids = movingIds(sh, v);
  const els = Array.from($("layer").querySelectorAll(".view")).filter(e => ids.includes(Number(e.getAttribute("data-id"))));
  S.drag = { id: id, v: v, start: pagePt(ev), dx: 0, dy: 0, els: els, moved: false };
  svg.setPointerCapture(ev.pointerId);
});
svg.addEventListener("pointermove", ev => {
  const d = S.drag;
  if (!d) return;
  const p = pagePt(ev);
  d.dx = p[0] - d.start[0]; d.dy = p[1] - d.start[1];
  if (d.v.linked) {                                           // preview of the server rule: a linked child slides on one axis
    if (d.v.side === "left" || d.v.side === "right") d.dy = 0; else d.dx = 0;
  }
  if (!d.moved && Math.hypot(d.dx, d.dy) > 0.5) {
    d.moved = true;
    $("layer").querySelectorAll(".link").forEach(e => e.remove());
  }
  if (d.moved) d.els.forEach(e => e.setAttribute("transform", "translate(" + d.dx + " " + (-d.dy) + ")"));
});
function endDrag(ev, commit) {
  const d = S.drag;
  if (!d) return;
  S.drag = null;
  if (svg.hasPointerCapture(ev.pointerId)) svg.releasePointerCapture(ev.pointerId);
  if (commit && d.moved) run({ op: "drag", id: d.id, dx: r1(d.dx), dy: r1(d.dy) }, "Moved " + d.v.label);
  else if (d.moved) render();
}
svg.addEventListener("pointerup", ev => endDrag(ev, true));
svg.addEventListener("pointercancel", ev => endDrag(ev, false));

// ---- drop a view from the panel ----
svg.addEventListener("dragover", ev => { ev.preventDefault(); ev.dataTransfer.dropEffect = "copy"; svg.classList.add("drop"); });
svg.addEventListener("dragleave", () => svg.classList.remove("drop"));
svg.addEventListener("drop", ev => {
  ev.preventDefault();
  svg.classList.remove("drop");
  const name = ev.dataTransfer.getData("text/plain"), p = pagePt(ev);
  if (S.meta.views.includes(name)) run({ op: "place", sheet: S.sheet, name: name, x: r1(p[0]), y: r1(p[1]) }, "Placed " + name);
});

async function buildPanel() {
  for (const name of S.meta.views) {
    const g = keep(await api("/api/view?name=" + name));
    S.geo[geoKey(g.cam, g.up)] = g;
    const b = g.bbox, w = b[2] - b[0], h = b[3] - b[1], m = Math.max(w, h) * 0.06;
    const div = document.createElement("div");
    div.className = "pv"; div.draggable = true; div.title = "Drag onto the sheet";
    const t = el("svg", { viewBox: (b[0] - m) + " " + (-b[3] - m) + " " + (w + 2 * m) + " " + (h + 2 * m) }, div);
    el("path", { d: g.dVis + g.dTan, transform: "scale(1 -1)", fill: "none", stroke: "#000", "stroke-width": Math.max(w, h) / 70 }, t);
    const span = document.createElement("span");
    span.textContent = name;
    div.appendChild(span);
    div.addEventListener("dragstart", ev => { ev.dataTransfer.setData("text/plain", name); ev.dataTransfer.effectAllowed = "copy"; });
    div.addEventListener("dblclick", () => run({ op: "place", sheet: S.sheet, name: name, x: r1(W / 2 - 40), y: r1(H / 2 + 20) }, "Placed " + name));
    $("views").appendChild(div);
  }
}

// ---- buttons and keys ----
["p-left", "p-right", "p-top", "p-bottom"].forEach(id => {
  $(id).onclick = () => { if (S.sel !== null) run({ op: "project", id: S.sel, side: $(id).getAttribute("data-side") }); };
});
$("break").onclick = () => { if (S.sel !== null) run({ op: "break_link", id: S.sel }, "Link broken: this view now moves freely"); };
$("delete").onclick = () => { if (S.sel !== null) run({ op: "delete", id: S.sel }); };
$("scale").onchange = () => run({ op: "set_scale", sheet: S.sheet, scale: S.meta.scales[$("scale").selectedIndex].value });
$("undo").onclick = undo;
$("save").onclick = () => queue(async () => {
  try { await applyState(await api("/api/doc", S.doc)); status("Saved"); }
  catch (e) { status(e.message, true); }
});
$("export").onclick = () => { window.open("/api/export.pdf", "_blank"); status("PDF exported in a new tab"); };
document.addEventListener("keydown", ev => {
  if (ev.target.tagName === "SELECT" || ev.target.tagName === "INPUT") return;
  if (ev.key === "Delete" && S.sel !== null) { ev.preventDefault(); run({ op: "delete", id: S.sel }); }
  if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "z") { ev.preventDefault(); undo(); }
});

(async function init() {
  try {
    S.meta = await api("/api/meta");
    W = S.meta.size.w; H = S.meta.size.h;
    S.meta.scales.forEach(s => { const o = document.createElement("option"); o.textContent = s.label; $("scale").appendChild(o); });
    drawFrame();
    await buildPanel();
    await applyState(await api("/api/doc"));
    status("Model: " + S.meta.source + ". Drag a view from the left onto the sheet.");
  } catch (e) { status(e.message, true); }
})();
