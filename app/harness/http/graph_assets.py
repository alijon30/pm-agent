"""The graph page's stylesheet and its force simulation, as strings.

They live apart from console.py for one reason: they are an asset, not logic. Nothing here is
imported by anything else, nothing here can be unit-tested by calling it, and mixing four
hundred lines of JavaScript into a module that assembles documents would make both harder to
read.

There is no library. A force-directed layout is a hundred lines of arithmetic — repulsion,
springs, damping, collision — and at a few hundred nodes the naive O(n²) pass is far below one
frame's budget. A CDN would have cost the page its self-containment, which is the property that
lets it be served from a locked-down Cloud Run service and opened by a judge with no network
trust. Every glow, arrowhead and glyph here is drawn by the page itself.

One rule that is not taste: every string that came from the database reaches the DOM through
`textContent`, never `innerHTML`. Labels are model output and issue titles; the console escapes
them on the server, and this page must not undo that by concatenating them into markup."""

from __future__ import annotations

GRAPH_STYLE = """
:root { --bg:#0b0d12; --fg:#e6e8ec; --muted:#8892a4; --line:#222736; --panel:#141824;
        --accent:#88c0d0; }
* { box-sizing: border-box; }
html, body { margin:0; height:100%; overflow:hidden; color:var(--fg);
  font:14px/1.5 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif; }
/* The void has a middle. Without it the canvas reads as a flat sheet and the nodes look
   pasted on rather than suspended in something. */
body { background:#07090d;
  background-image: radial-gradient(ellipse 90% 75% at 50% 45%, #11141c 0%, #07090d 78%); }
#stage { position:fixed; inset:0; }
svg { width:100%; height:100%; display:block; }

header { position:fixed; top:18px; left:20px; z-index:3; pointer-events:none; }
header h1 { margin:0; font-size:16px; font-weight:650; letter-spacing:.01em; }
header p { margin:2px 0 0; font-size:12.5px; color:var(--muted); }
header a { pointer-events:auto; color:var(--muted); text-decoration:none;
  border-bottom:1px solid var(--line); }
header a:hover { color:var(--fg); }

#rail { position:fixed; top:82px; left:20px; z-index:3; display:flex; flex-direction:column;
  gap:14px; width:250px; }
#now { background:var(--panel); border:1px solid var(--line); border-radius:10px;
  padding:10px 12px; font-size:12px; transition:opacity 180ms ease; }
#now.past { opacity:.4; pointer-events:none; }
#now-head { display:flex; align-items:center; gap:8px; cursor:pointer; color:var(--fg);
  line-height:1.4; }
#now-head .caret { color:var(--muted); font-size:9px; margin-left:auto; }
#pulse { width:7px; height:7px; border-radius:50%; background:var(--muted); flex:none;
  margin-top:1px; }
#pulse.busy { background:var(--accent); animation:beat 1.6s ease-in-out infinite; }
@keyframes beat {
  0%,100% { box-shadow:0 0 0 0 rgba(136,192,208,.55); }
  60% { box-shadow:0 0 0 6px rgba(136,192,208,0); }
}
#now-body { margin-top:2px; }
#now.shut #now-body { display:none; }
.now-group { margin-top:10px; border-top:1px solid var(--line); padding-top:8px; }
.now-group h4 { margin:0 0 5px; font-size:9.5px; letter-spacing:.12em; text-transform:uppercase;
  color:var(--muted); font-weight:600; }
.now-row { display:flex; gap:8px; align-items:baseline; padding:2px 0; color:var(--fg);
  line-height:1.35; }
.now-row em { font-style:normal; color:var(--muted); font-size:11px; margin-left:auto;
  white-space:nowrap; padding-left:6px; }
.now-more { color:var(--muted); font-size:11px; padding-top:3px; }
.now-past-hint { color:var(--muted); font-size:11px; margin-top:6px; font-style:italic; }

#legend { z-index:3; display:flex; flex-direction:column;
  gap:6px; font-size:12px; color:var(--muted); }
#legend span { display:flex; align-items:center; gap:8px; }
#legend i { width:15px; height:15px; border-radius:50%; display:flex; align-items:center;
  justify-content:center; font-size:8px; font-style:normal; color:#0b0d12; font-weight:700; }

#controls { position:fixed; left:50%; transform:translateX(-50%); bottom:20px; z-index:3;
  display:flex; align-items:center; gap:14px; background:var(--panel);
  border:1px solid var(--line); border-radius:11px; padding:10px 14px;
  box-shadow:0 10px 34px rgba(0,0,0,.5); }
button { background:#1b2030; color:var(--fg); border:1px solid var(--line); border-radius:8px;
  padding:6px 13px; font:inherit; font-size:13px; cursor:pointer; min-width:92px; }
button:hover { background:#232a3d; }
input[type=range] { width:min(44vw,420px); accent-color:var(--accent); cursor:pointer; }
#clock { font-variant-numeric:tabular-nums; color:var(--muted); min-width:118px;
  font-size:12.5px; transition:font-size 180ms ease, color 180ms ease; }
#clock.playing { font-size:15px; color:var(--fg); }
#count { color:var(--muted); font-size:12.5px; min-width:72px; text-align:right; }
#mode { font-size:10px; letter-spacing:.12em; padding:3px 8px; border-radius:99px;
  border:1px solid var(--line); color:var(--muted); transition:color 180ms, border-color 180ms; }
#mode.replay { color:var(--accent); border-color:var(--accent); }

.edge { fill:none; stroke:#39415a; stroke-width:1.1; opacity:.55;
  transition:opacity 150ms ease; }
.edge.watches { stroke-dasharray:3 3; }
.edge.learned { stroke:#5a4634; stroke-dasharray:2 4; }
.edge.lit { opacity:1; stroke-width:1.6; }
.edge.dimmed { opacity:.12; }

.node { cursor:default; transition:opacity 150ms ease; }
.node.link { cursor:pointer; }
.node.dimmed { opacity:.12; }
.node circle.body { stroke:#0b0d12; stroke-width:1.5; }
.node.link:hover circle.body { stroke:#e6e8ec; }
.glyph { fill:#0b0d12; font-weight:700; text-anchor:middle; dominant-baseline:central;
  pointer-events:none; font-family:ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif; }
.label { fill:#aeb6c6; font-size:10.5px; text-anchor:middle; pointer-events:none;
  paint-order:stroke; stroke:#07090d; stroke-width:3px; stroke-linejoin:round;
  font-variant-numeric:tabular-nums; }
.halo { fill:none; }
.early circle.body { animation:pulse 1.9s ease-in-out infinite; }
@keyframes pulse {
  0%,100% { filter:drop-shadow(0 0 0 rgba(163,190,140,0)); }
  50% { filter:drop-shadow(0 0 8px rgba(163,190,140,.95)); }
}
.ripple { fill:none; stroke-width:2; transform-box:fill-box; transform-origin:center;
  animation:ripple 500ms ease-out forwards; pointer-events:none; }
@keyframes ripple {
  from { transform:scale(1); opacity:.75; }
  to { transform:scale(3); opacity:0; }
}

#tooltip { position:fixed; z-index:5; pointer-events:none; opacity:0; max-width:320px;
  background:var(--panel); border:1px solid var(--line); border-radius:9px; padding:9px 12px;
  box-shadow:0 12px 36px rgba(0,0,0,.6); transition:opacity 120ms ease; }
#tooltip.on { opacity:1; }
#tooltip .t-type { color:var(--muted); font-size:10px; letter-spacing:.12em;
  text-transform:uppercase; }
#tooltip .t-label { color:var(--fg); font-size:13px; margin:4px 0 5px; line-height:1.4; }
#tooltip .t-meta { color:var(--muted); font-size:11.5px; }

#panel { position:fixed; top:0; right:0; bottom:0; width:360px; z-index:4;
  background:var(--panel); border-left:1px solid var(--line); overflow-y:auto;
  transform:translateX(100%); transition:transform 180ms ease;
  box-shadow:-14px 0 44px rgba(0,0,0,.45); padding:20px 20px 28px; }
#panel.open { transform:translateX(0); }
#panel-close { position:absolute; top:14px; right:14px; min-width:0; padding:2px 8px;
  font-size:14px; line-height:1.2; }
.p-chip { display:inline-flex; align-items:center; gap:7px; font-size:10px; letter-spacing:.12em;
  text-transform:uppercase; color:var(--muted); }
.p-chip i { width:15px; height:15px; border-radius:50%; display:flex; align-items:center;
  justify-content:center; font-size:8px; font-style:normal; color:#0b0d12; font-weight:700; }
.p-title { font-size:15px; line-height:1.45; margin:10px 0 3px; color:var(--fg); }
.p-when { font-size:11.5px; color:var(--muted); margin-bottom:16px; }
.p-head { font-size:10px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted);
  margin:18px 0 8px; border-top:1px solid var(--line); padding-top:14px; }
.p-fact { display:flex; gap:10px; font-size:12.5px; padding:3px 0; }
.p-fact b { color:var(--muted); font-weight:400; min-width:96px; flex:none; }
.p-fact span { color:var(--fg); }
.p-line { display:flex; gap:9px; align-items:baseline; padding:6px 0;
  border-bottom:1px solid var(--line); font-size:12.5px; }
.p-line em { font-style:normal; color:var(--muted); font-size:11px; white-space:nowrap;
  margin-left:auto; padding-left:8px; }
.p-dot { width:6px; height:6px; border-radius:50%; flex:none; margin-top:5px; }
.p-none { color:var(--muted); font-size:12.5px; font-style:italic; }
.p-open { display:inline-block; margin-top:18px; font-size:12.5px; color:var(--accent);
  text-decoration:none; border-bottom:1px solid var(--accent); }
.node.selected circle.body { stroke:#e6e8ec; stroke-width:2.5; }
.livering { fill:none; stroke:#88c0d0; stroke-width:1.5; animation:live 2s ease-in-out infinite; }
@keyframes live {
  0%,100% { opacity:.15; transform:scale(1); }
  50% { opacity:.85; transform:scale(1.14); }
}

#empty { position:fixed; inset:0; display:flex; align-items:center; justify-content:center;
  color:var(--muted); font-size:14px; }
"""

# Tuning constants live in one block at the top of the script and are taste, not truth: they
# were chosen because the result reads well at a few dozen nodes, not because they are derived
# from anything.
GRAPH_SCRIPT = """
const SIM = {
  repulsion: 2600,      // how hard any two nodes push apart
  spring: 0.014,        // how hard an edge pulls its ends together
  restLength: 96,       // the length an edge is happy at
  centering: 0.0018,    // a gentle pull to the middle, so nothing drifts off screen
  damping: 0.87,        // velocity kept per frame; lower settles faster and feels stiffer
  maxSpeed: 14,
  collisionPad: 14,     // clear space between two circles, so labels stop colliding
  curve: 0.12,          // how far an edge bows off the straight line, as a fraction of it
  enterBurst: 2.4,      // the kick a node gets as it appears, so arrivals feel alive
  enterMs: 320,         // how long a node takes to scale in
  drawMs: 400,          // how long an edge takes to draw itself
  rippleMs: 500,        // the expanding ring an arriving node leaves behind
  replayMs: 20000,      // a full replay lands in about this long
  stepMaxMs: 1200,      // ...unless there are few enough events to give each one this
};

const COLORS = {
  meeting: "#b48ead", decision: "#ebcb8b", issue: "#5e81ac",
  person: "#a3be8c", check: "#4c566a", lesson: "#d08770",
};
const CHECK_DONE = "#a3be8c", CHECK_FAILED = "#bf616a";
const RADIUS = { meeting: 16, decision: 8, issue: 10, person: 9, check: 6, lesson: 7 };
// The call is the sun: heavy things move less, so the story arranges itself around its origin
// instead of drifting wherever the last spring happened to pull.
const MASS = { meeting: 3, issue: 1.6, person: 1.4 };
const GLYPHS = { meeting: "\\u260E", decision: "\\u25C6", issue: "\\u25A3", lesson: "\\u2726" };
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const NS = "http://www.w3.org/2000/svg";
// The journal's categories, tinted the way the console tints them: green for work that landed,
// warm for anything the agent declined or could not do.
const CATEGORY_TINT = {
  filed: "#a3be8c", reported: "#a3be8c", early: "#a3be8c", planned: "#88c0d0",
  posted: "#88c0d0", nudged: "#ebcb8b", checked: "#8892a4", extracted: "#b48ead",
  reconciled: "#b48ead", deferred: "#d08770", refused: "#bf616a", failed: "#bf616a",
  cancelled: "#bf616a", reverted: "#d08770", pending: "#8892a4", done: "#8892a4",
};
const FACT_LABELS = {
  state: "state", assignee: "assignee", priority: "priority", due: "due",
  filed_from_call: "from a call", reason: "why", status: "status", on_unmet: "if unmet",
  observed: "last seen", early: "resolved early", statement: "decided", quote: "said",
  source: "source", role: "role", owns: "owns", pings_received: "pings sent",
  title: "call", when: "when", produced: "produced", evidence: "learned from",
};

const gDefs = document.getElementById("defs");
const gEdges = document.getElementById("edges");
const gNodes = document.getElementById("nodes");
const scrubber = document.getElementById("scrubber");
const clock = document.getElementById("clock");
const counter = document.getElementById("count");
const playButton = document.getElementById("play");
const modeChip = document.getElementById("mode");
const tooltip = document.getElementById("tooltip");
const dock = document.getElementById("now");
const dockHead = document.getElementById("now-head");
const dockBody = document.getElementById("now-body");
const dockPulse = document.getElementById("pulse");
const dockLine = document.getElementById("now-line");
const panel = document.getElementById("panel");
const panelBody = document.getElementById("panel-body");
const panelClose = document.getElementById("panel-close");
const canvas = document.getElementById("canvas");

// The replay advances over nodes, not over milliseconds. Everything a single call produces
// shares a timestamp to the second, so a clock-driven cursor would reveal the whole story in one
// frame and then crawl through the empty night that follows. One node per step always reads.
let nodes = [], edges = [], byId = new Map();
let cursor = 0, playing = false, lastFrame = 0, stepMs = 1200, selected = null;
let payload = null, live = new Set(), polling = null;
let width = window.innerWidth, height = window.innerHeight;

function svgEl(tag) { return document.createElementNS(NS, tag); }

function stamp(ms) {
  if (!ms) return "\\u2014";
  const d = new Date(ms);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${hh}:${mm}`;
}

function colorOf(node) {
  if (node.type !== "check") return COLORS[node.type] || COLORS.check;
  if (node.status === "failed" || node.status === "cancelled") return CHECK_FAILED;
  if (node.status === "done") return CHECK_DONE;
  return COLORS.check;
}

function glyphOf(node) {
  if (node.type === "check") return node.status === "done" ? "\\u2713" : "\\u25CB";
  return GLYPHS[node.type] || "";
}

// A person is a silhouette, not a monogram: an icon says "human" to someone who has never met
// the roster, and the name sits underneath where issues already set the precedent.
function personGlyph(r) {
  const g = svgEl("g");
  g.setAttribute("class", "personGlyph");
  const head = svgEl("circle");
  head.setAttribute("cx", "0"); head.setAttribute("cy", String(-r * 0.28));
  head.setAttribute("r", String(r * 0.30));
  const body = svgEl("path");
  const w = r * 0.62, top = r * 0.12, bottom = r * 0.62;
  body.setAttribute("d", `M ${-w} ${bottom} Q 0 ${top - r * 0.35} ${w} ${bottom} Z`);
  g.appendChild(head); g.appendChild(body);
  return g;
}

function personMark(size) {
  // The same silhouette the node draws, sized for a swatch. Reused rather than redrawn so the
  // legend and the panel can never disagree with the graph about what a person looks like.
  const svg = svgEl("svg");
  svg.setAttribute("width", String(size));
  svg.setAttribute("height", String(size));
  svg.setAttribute("viewBox", `${-size / 2} ${-size / 2} ${size} ${size}`);
  const mark = personGlyph(size * 0.42);
  mark.setAttribute("fill", "#0b0d12");
  svg.appendChild(mark);
  return svg;
}

function identifierOf(node) {
  const cut = String(node.id || "").indexOf(":");
  return cut < 0 ? "" : node.id.slice(cut + 1);
}

// --- the one-time definitions ------------------------------------------------------------------

function filterId(hue) { return "glow" + hue.replace("#", ""); }

function defineGlow(hue) {
  // Colour the blurred silhouette rather than the shape, then put the shape back on top: a
  // plain drop-shadow would tint the fill as well and mud every node the same grey.
  const filter = svgEl("filter");
  filter.setAttribute("id", filterId(hue));
  filter.setAttribute("x", "-90%"); filter.setAttribute("y", "-90%");
  filter.setAttribute("width", "280%"); filter.setAttribute("height", "280%");
  const blur = svgEl("feGaussianBlur");
  blur.setAttribute("in", "SourceAlpha");
  blur.setAttribute("stdDeviation", "4");
  blur.setAttribute("result", "blurred");
  const flood = svgEl("feFlood");
  flood.setAttribute("flood-color", hue);
  flood.setAttribute("flood-opacity", "0.5");
  flood.setAttribute("result", "tint");
  const composite = svgEl("feComposite");
  composite.setAttribute("in", "tint");
  composite.setAttribute("in2", "blurred");
  composite.setAttribute("operator", "in");
  composite.setAttribute("result", "glow");
  const merge = svgEl("feMerge");
  for (const source of ["glow", "SourceGraphic"]) {
    const node = svgEl("feMergeNode");
    node.setAttribute("in", source);
    merge.appendChild(node);
  }
  for (const part of [blur, flood, composite, merge]) filter.appendChild(part);
  gDefs.appendChild(filter);
}

function defineArrow() {
  const marker = svgEl("marker");
  marker.setAttribute("id", "arrow");
  marker.setAttribute("viewBox", "0 0 8 8");
  marker.setAttribute("refX", "7"); marker.setAttribute("refY", "4");
  marker.setAttribute("markerWidth", "5"); marker.setAttribute("markerHeight", "5");
  marker.setAttribute("orient", "auto-start-reverse");
  const head = svgEl("path");
  head.setAttribute("d", "M0,0 L8,4 L0,8 Z");
  head.setAttribute("fill", "#4b5570");
  marker.appendChild(head);
  gDefs.appendChild(marker);
}

function fillPersonSwatches() {
  for (const slot of [document.getElementById("legend-person"), null]) {
    if (slot) { slot.textContent = ""; slot.appendChild(personMark(11)); }
  }
}

function defineAll() {
  // One filter per colour, not one per node: at 250 nodes that is the difference between six
  // filters and two hundred and fifty.
  const hues = new Set([...Object.values(COLORS), CHECK_DONE, CHECK_FAILED]);
  for (const hue of hues) defineGlow(hue);
  defineArrow();
  fillPersonSwatches();
}

// --- building -----------------------------------------------------------------------------------

function build(data, placed) {
  // Nodes start on a ring rather than at random: the first frames of a replay look composed
  // instead of like an explosion, and the simulation still finds its own shape within a second.
  nodes = (data.nodes || []).map((n, i) => {
    const angle = (i / Math.max(1, data.nodes.length)) * Math.PI * 2;
    const spread = 140 + (i % 7) * 26;
    const before = placed && placed.get(n.id);
    return {
      ...n,
      index: i,
      x: before ? before.x : width / 2 + Math.cos(angle) * spread,
      y: before ? before.y : height / 2 + Math.sin(angle) * spread,
      vx: 0, vy: 0,
      shown: false, enteredAt: 0, ring: null,
      r: RADIUS[n.type] || 7,
      m: MASS[n.type] || 1,
    };
  });
  byId = new Map(nodes.map((n) => [n.id, n]));
  edges = (data.edges || [])
    .map((e, i) => ({ ...e, i, a: byId.get(e.source), b: byId.get(e.target),
                      shown: false, enteredAt: 0, dashed: false }))
    .filter((e) => e.a && e.b);

  scrubber.min = "0";
  scrubber.max = String(nodes.length);
  cursor = nodes.length;
  scrubber.value = String(cursor);
  stepMs = Math.min(SIM.stepMaxMs, SIM.replayMs / Math.max(1, nodes.length));

  if (!nodes.length) document.getElementById("empty").style.display = "flex";
  defineAll();
  renderNow(data.now || {working:{items:[],more:0}, up_next:{items:[],more:0},
                        waiting:{items:[],more:0}, open:0, watching:0});
  draw();
}

function visible(node) { return node.index < cursor; }

function cursorStamp() {
  // The clock shows the real time of the newest thing on screen, even though the cursor counts
  // nodes: the reader wants to know when this happened, not which node it is.
  let latest = "";
  for (const n of nodes) if (n.index < cursor && n.ts > latest) latest = n.ts;
  return latest ? stamp(Date.parse(latest)) : "\\u2014";
}

function reveal(now) {
  for (const node of nodes) {
    const should = visible(node);
    if (should && !node.shown) {
      node.shown = true;
      node.enteredAt = now;
      // A tiny kick outward from wherever it landed, so an arriving node announces itself.
      const angle = Math.random() * Math.PI * 2;
      node.vx += Math.cos(angle) * SIM.enterBurst;
      node.vy += Math.sin(angle) * SIM.enterBurst;
      ripple(node);
    } else if (!should && node.shown) {
      node.shown = false;
      node.enteredAt = 0;
    }
  }
  for (const edge of edges) {
    const should = edge.a.shown && edge.b.shown;
    if (should && !edge.shown) { edge.shown = true; edge.enteredAt = now; }
    else if (!should && edge.shown) { edge.shown = false; edge.enteredAt = 0; }
  }
}

function ripple(node) {
  // One at a time per node. Scrubbing quickly back and forth re-enters the same nodes over and
  // over, and without this every pass would leave another circle behind to expand and fade.
  if (node.rippling) return;
  node.rippling = true;
  const circle = svgEl("circle");
  circle.setAttribute("class", "ripple");
  circle.setAttribute("r", String(node.r));
  circle.setAttribute("stroke", colorOf(node));
  element(node).appendChild(circle);
  window.setTimeout(() => { circle.remove(); node.rippling = false; }, SIM.rippleMs);
}

// --- physics --------------------------------------------------------------------------------------

function physics() {
  const live = nodes.filter((n) => n.shown);
  for (let i = 0; i < live.length; i++) {
    const a = live[i];
    for (let j = i + 1; j < live.length; j++) {
      const b = live[j];
      let dx = a.x - b.x, dy = a.y - b.y;
      let d2 = dx * dx + dy * dy;
      if (d2 < 1) { dx = Math.random() - 0.5; dy = Math.random() - 0.5; d2 = 1; }
      const force = SIM.repulsion / d2;
      const d = Math.sqrt(d2);
      a.vx += (dx / d) * force / a.m; a.vy += (dy / d) * force / a.m;
      b.vx -= (dx / d) * force / b.m; b.vy -= (dy / d) * force / b.m;
    }
  }
  for (const e of edges) {
    if (!e.shown) continue;
    const dx = e.b.x - e.a.x, dy = e.b.y - e.a.y;
    const d = Math.sqrt(dx * dx + dy * dy) || 1;
    const pull = (d - SIM.restLength) * SIM.spring;
    e.a.vx += (dx / d) * pull / e.a.m; e.a.vy += (dy / d) * pull / e.a.m;
    e.b.vx -= (dx / d) * pull / e.b.m; e.b.vy -= (dy / d) * pull / e.b.m;
  }
  for (const n of live) {
    n.vx += (width / 2 - n.x) * SIM.centering;
    n.vy += (height / 2 - n.y) * SIM.centering;
    n.vx *= SIM.damping; n.vy *= SIM.damping;
    const speed = Math.hypot(n.vx, n.vy);
    if (speed > SIM.maxSpeed) { n.vx *= SIM.maxSpeed / speed; n.vy *= SIM.maxSpeed / speed; }
    n.x += n.vx; n.y += n.vy;
  }
  // Springs and repulsion balance on average; overlap is about the worst case. Separating any
  // two circles that ended up touching is what keeps the labels apart.
  for (let i = 0; i < live.length; i++) {
    for (let j = i + 1; j < live.length; j++) {
      const a = live[i], b = live[j];
      const dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.hypot(dx, dy) || 0.01;
      const need = a.r + b.r + SIM.collisionPad;
      if (d >= need) continue;
      const push = (need - d) / 2;
      const ux = dx / d, uy = dy / d;
      const total = a.m + b.m;
      a.x -= ux * push * (b.m / total) * 2; a.y -= uy * push * (b.m / total) * 2;
      b.x += ux * push * (a.m / total) * 2; b.y += uy * push * (a.m / total) * 2;
    }
  }
  for (const n of live) {
    const pad = n.r + 30;
    n.x = Math.max(pad, Math.min(width - pad, n.x));
    n.y = Math.max(pad, Math.min(height - pad, n.y));
  }
}

// --- elements ---------------------------------------------------------------------------------------

function element(node) {
  if (node.el) return node.el;
  const hue = colorOf(node);
  const g = svgEl("g");
  g.setAttribute("class", "node" + (node.url ? " link" : "") + (node.early ? " early" : ""));

  if (node.type === "meeting") {
    const halo = svgEl("circle");
    halo.setAttribute("class", "halo");
    halo.setAttribute("r", String(node.r + 7));
    halo.setAttribute("stroke", hue);
    halo.setAttribute("stroke-opacity", "0.25");
    g.appendChild(halo);
  }

  const circle = svgEl("circle");
  circle.setAttribute("class", "body");
  circle.setAttribute("r", String(node.r));
  circle.setAttribute("fill", hue);
  circle.setAttribute("filter", `url(#${filterId(hue)})`);
  g.appendChild(circle);

  if (node.type === "person") {
    g.appendChild(personGlyph(node.r));
  } else {
    const glyph = svgEl("text");
    glyph.setAttribute("class", "glyph");
    glyph.setAttribute("font-size", String(Math.round(node.r * 1.1)));
    glyph.textContent = glyphOf(node);
    g.appendChild(glyph);
  }

  // Issues and people keep a standing label: the identifier and the name are what a reader
  // tracks across the graph; everything else says what it is with its glyph or on hover.
  if (node.type === "issue" || node.type === "person") {
    const label = svgEl("text");
    label.setAttribute("class", "label");
    label.setAttribute("y", String(node.r + 14));
    label.textContent = identifierOf(node);
    g.appendChild(label);
  }

  // While a node is pinned its neighbourhood stays lit: hovering elsewhere must not re-dim the
  // thing the reader is currently looking at.
  g.addEventListener("mouseenter", (event) => {
    if (!selected) focus(node);
    if (!selected) showTip(node, event);
  });
  g.addEventListener("mousemove", (event) => { if (!selected) moveTip(event); });
  g.addEventListener("mouseleave", () => { if (!selected) { unfocus(); hideTip(); } });
  g.addEventListener("click", (event) => { event.stopPropagation(); select(node); });
  gNodes.appendChild(g);
  node.el = g;
  return g;
}

function edgeElement(edge) {
  if (edge.el) return edge.el;
  const path = svgEl("path");
  const kind = edge.rel === "watches" ? " watches"
    : edge.rel === "learned from" ? " learned" : "";
  path.setAttribute("class", "edge" + kind);
  if (edge.rel === "waits on") path.setAttribute("marker-end", "url(#arrow)");
  gEdges.appendChild(path);
  edge.el = path;
  return path;
}

function edgePath(edge) {
  const a = edge.a, b = edge.b;
  const dx = b.x - a.x, dy = b.y - a.y;
  const d = Math.hypot(dx, dy) || 1;
  const ux = dx / d, uy = dy / d;
  // Start and end on the rims, not the centres, so an arrowhead is not buried under a circle.
  const gap = edge.rel === "waits on" ? b.r + 7 : b.r + 2;
  const sx = a.x + ux * (a.r + 2), sy = a.y + uy * (a.r + 2);
  const ex = b.x - ux * gap, ey = b.y - uy * gap;
  // Alternating the bow means two edges between the same pair fan apart instead of overlapping.
  const off = d * SIM.curve * (edge.i % 2 === 0 ? 1 : -1);
  const mx = (sx + ex) / 2 - uy * off, my = (sy + ey) / 2 + ux * off;
  return `M${sx.toFixed(1)},${sy.toFixed(1)} Q${mx.toFixed(1)},${my.toFixed(1)} ` +
         `${ex.toFixed(1)},${ey.toFixed(1)}`;
}

// --- focus -------------------------------------------------------------------------------------------

function focus(node) {
  const near = new Set([node.id]);
  for (const e of edges) {
    if (e.source === node.id) near.add(e.target);
    if (e.target === node.id) near.add(e.source);
  }
  const hue = colorOf(node);
  for (const n of nodes) if (n.el) n.el.classList.toggle("dimmed", !near.has(n.id));
  for (const e of edges) {
    if (!e.el) continue;
    const touching = e.source === node.id || e.target === node.id;
    e.el.classList.toggle("lit", touching);
    e.el.classList.toggle("dimmed", !touching);
    e.el.style.stroke = touching ? hue : "";
  }
}

function unfocus() {
  for (const n of nodes) if (n.el) n.el.classList.remove("dimmed");
  for (const e of edges) {
    if (!e.el) continue;
    e.el.classList.remove("dimmed");
    e.el.classList.remove("lit");
    e.el.style.stroke = "";
  }
}

// --- the tooltip ---------------------------------------------------------------------------------------

function line(className, text) {
  const div = document.createElement("div");
  div.className = className;
  // textContent, never innerHTML: these strings are issue titles and model output.
  div.textContent = text;
  return div;
}

function showTip(node, event) {
  tooltip.textContent = "";
  tooltip.appendChild(line("t-type", node.type === "meeting" ? "call" : node.type));
  tooltip.appendChild(line("t-label", node.label));
  const meta = [];
  if (node.ts) meta.push(stamp(Date.parse(node.ts)));
  if (node.type === "check") {
    meta.push(node.status || "scheduled");
    if (node.early) meta.push("resolved early");
  }
  if (node.url) meta.push("click to open");
  if (meta.length) tooltip.appendChild(line("t-meta", meta.join(" \\u00B7 ")));
  tooltip.classList.add("on");
  moveTip(event);
}

function moveTip(event) {
  const pad = 16;
  const x = Math.min((event.clientX || 0) + pad, width - 340);
  const y = Math.min((event.clientY || 0) + pad, height - 110);
  tooltip.style.left = Math.max(pad, x) + "px";
  tooltip.style.top = Math.max(pad, y) + "px";
}

function hideTip() { tooltip.classList.remove("on"); }

// --- what the agent is doing right now ---------------------------------------------------------

function nowRow(text, meta) {
  const row = document.createElement("div");
  row.className = "now-row";
  const label = document.createElement("span");
  label.textContent = text;
  row.appendChild(label);
  if (meta) {
    const right = document.createElement("em");
    right.textContent = meta;
    row.appendChild(right);
  }
  return row;
}

function nowGroup(title, list, render) {
  const group = document.createElement("div");
  group.className = "now-group";
  const head = document.createElement("h4");
  head.textContent = title;
  group.appendChild(head);
  for (const item of list.items) group.appendChild(render(item));
  if (list.more) {
    const more = document.createElement("div");
    more.className = "now-more";
    more.textContent = `+${list.more} more`;
    group.appendChild(more);
  }
  return group;
}

function renderNow(now) {
  const busy = now.working.items.length > 0;
  dockPulse.classList.toggle("busy", busy);
  if (busy) {
    dockLine.textContent = "working: " + now.working.items[0].phrase;
  } else if (now.up_next.items.length) {
    const next = now.up_next.items[0];
    dockLine.textContent = `idle — next wake ${next.due_human}: ${next.phrase}`;
  } else {
    dockLine.textContent = "idle — nothing scheduled";
  }

  dockBody.textContent = "";
  if (now.working.items.length > 1) {
    dockBody.appendChild(nowGroup("also running", {
      items: now.working.items.slice(1), more: now.working.more,
    }, (w) => nowRow(w.phrase, "")));
  }
  if (now.up_next.items.length) {
    dockBody.appendChild(nowGroup("up next", now.up_next,
      (u) => nowRow(u.phrase, u.due_human)));
  }
  if (now.waiting.items.length) {
    dockBody.appendChild(nowGroup("waiting", now.waiting,
      (w) => nowRow(w.phrase, "")));
  }
  dockBody.appendChild(nowGroup(
    "queue",
    { items: [`${now.open} open \u00B7 ${now.watching} being watched`], more: 0 },
    (line) => nowRow(line, ""),
  ));

  // Any node this second's work is about wears a ring, so "working: filing INV-28" and the
  // graph point at the same thing without the reader having to match names.
  live = new Set();
  for (const item of now.working.items) {
    live.add("task:" + item.id);
    if (item.issue) live.add("issue:" + item.issue);
  }
  // The ring is applied in draw(), not here: nodes get their elements lazily on the first
  // frame, so a set built now would have nothing to mark yet.
}

function markLive(node) {
  const on = live.has(node.id);
  if (on && !node.ring) {
    node.ring = svgEl("circle");
    node.ring.setAttribute("class", "livering");
    node.ring.setAttribute("r", String(node.r + 5));
    node.el.appendChild(node.ring);
  } else if (!on && node.ring) {
    node.ring.remove();
    node.ring = null;
  }
}

function atLive() { return nodes.length === 0 || cursor >= nodes.length; }

function showsThePast() {
  const past = !atLive();
  dock.classList.toggle("past", past);
  const hint = document.getElementById("now-hint");
  if (hint) hint.style.display = past ? "" : "none";
}

function fingerprint(data) {
  return `${(data.nodes || []).length}|${(data.now || {}).last_tick || ""}`
    + `|${((data.now || {}).working || {}).items?.length || 0}`;
}

function adopt(fresh) {
  // Keep every node that survived exactly where it was: a poll that rearranged the graph would
  // undo the reader's mental map every minute for no reason.
  const placed = new Map(nodes.map((n) => [n.id, n]));
  gNodes.textContent = "";
  gEdges.textContent = "";
  const wasSelected = selected ? selected.id : null;
  selected = null;
  panel.classList.remove("open");
  build(fresh, placed);
  payload = fresh;
  if (wasSelected && byId.has(wasSelected)) select(byId.get(wasSelected));
}

async function poll() {
  // Never while the reader is somewhere in the past: replacing the data under a scrubbed
  // timeline would jump them back to the present without being asked.
  if (!atLive() || playing) return;
  try {
    const fresh = await fetch("/console/graph.json").then((r) => r.json());
    if (fingerprint(fresh) !== fingerprint(payload)) adopt(fresh);
    else renderNow(fresh.now || {});
  } catch (err) {
    // A poll that fails changes nothing; the page keeps showing the last state it trusted.
  }
}

// --- the story panel -----------------------------------------------------------------------------

function factValue(key, value) {
  if (Array.isArray(value)) return value.length ? value.join(", ") : "nothing yet";
  if (value === true) return "yes";
  if (value === false) return "no";
  if (value === null || value === undefined || value === "") return "\u2014";
  if (key === "produced" && typeof value === "object") {
    return `${value.decisions} decision(s), ${value.issues} issue(s)`;
  }
  return String(value);
}

function factRow(key, value) {
  const row = document.createElement("div");
  row.className = "p-fact";
  const label = document.createElement("b");
  label.textContent = FACT_LABELS[key] || key;
  const text = document.createElement("span");
  text.textContent = factValue(key, value);
  row.appendChild(label); row.appendChild(text);
  return row;
}

function storyRow(entry) {
  const row = document.createElement("div");
  row.className = "p-line";
  const dot = document.createElement("span");
  dot.className = "p-dot";
  dot.style.background = CATEGORY_TINT[entry.category] || "#8892a4";
  const text = document.createElement("span");
  text.textContent = entry.text;
  const when = document.createElement("em");
  when.textContent = entry.ts ? stamp(Date.parse(entry.ts)) : "";
  row.appendChild(dot); row.appendChild(text); row.appendChild(when);
  return row;
}

function heading(text) {
  const head = document.createElement("div");
  head.className = "p-head";
  head.textContent = text;
  return head;
}

function openPanel(node) {
  // Clicking during a replay pauses it. A paused graph with one node's story open is the shot
  // this page exists for: the narrator stops on a node and reads what the agent did about it.
  if (playing) stopPlaying();

  panelBody.textContent = "";
  const chip = document.createElement("div");
  chip.className = "p-chip";
  const swatch = document.createElement("i");
  swatch.style.background = colorOf(node);
  if (node.type === "person") swatch.appendChild(personMark(11));
  else swatch.textContent = glyphOf(node);
  chip.appendChild(swatch);
  const kind = document.createElement("span");
  kind.textContent = node.type === "meeting" ? "call" : node.type;
  chip.appendChild(kind);
  panelBody.appendChild(chip);

  const title = document.createElement("div");
  title.className = "p-title";
  title.textContent = node.label;
  panelBody.appendChild(title);

  const when = document.createElement("div");
  when.className = "p-when";
  when.textContent = node.ts ? stamp(Date.parse(node.ts)) : "\u2014";
  panelBody.appendChild(when);

  const facts = node.facts || {};
  const keys = Object.keys(facts);
  if (keys.length) {
    panelBody.appendChild(heading("Facts"));
    for (const key of keys) panelBody.appendChild(factRow(key, facts[key]));
  }

  panelBody.appendChild(heading("What I did"));
  const story = node.story || [];
  if (story.length) {
    for (const entry of story) panelBody.appendChild(storyRow(entry));
  } else {
    const none = document.createElement("div");
    none.className = "p-none";
    none.textContent = (node.type === "check" || node.type === "issue")
      ? "Nothing yet \u2014 I'm watching."
      : "\u2014";
    panelBody.appendChild(none);
  }

  if (node.url) {
    const open = document.createElement("a");
    open.className = "p-open";
    open.href = node.url;
    open.target = "_blank";
    open.rel = "noreferrer";
    open.textContent = "Open in Linear \u2197";
    panelBody.appendChild(open);
  }
  panel.classList.add("open");
}

function select(node) {
  if (selected && selected.el) selected.el.classList.remove("selected");
  selected = node;
  node.el.classList.add("selected");
  focus(node);
  hideTip();
  openPanel(node);
}

function deselect() {
  if (selected && selected.el) selected.el.classList.remove("selected");
  selected = null;
  panel.classList.remove("open");
  unfocus();
}

// --- drawing -----------------------------------------------------------------------------------------

function draw() {
  const now = performance.now();
  let visibleCount = 0;
  for (const node of nodes) {
    const g = element(node);
    markLive(node);
    if (!node.shown) { g.style.display = "none"; continue; }
    visibleCount++;
    g.style.display = "";
    const age = now - node.enteredAt;
    const scale = age < SIM.enterMs ? 0.2 + 0.8 * (age / SIM.enterMs) : 1;
    g.setAttribute("transform",
      `translate(${node.x.toFixed(1)},${node.y.toFixed(1)}) scale(${scale.toFixed(3)})`);
    g.style.opacity = age < SIM.enterMs ? String(Math.min(1, age / SIM.enterMs)) : "";
  }
  for (const edge of edges) {
    const path = edgeElement(edge);
    if (!edge.shown) { path.style.display = "none"; continue; }
    path.style.display = "";
    path.setAttribute("d", edgePath(edge));
    // The geometry moves every frame, so the dash is recomputed rather than transitioned: a CSS
    // transition would keep animating towards a length that has already changed.
    const age = now - edge.enteredAt;
    if (age < SIM.drawMs && path.getTotalLength) {
      const length = path.getTotalLength() || 0;
      path.style.strokeDasharray = String(length);
      path.style.strokeDashoffset = String(length * (1 - age / SIM.drawMs));
      edge.dashed = true;
    } else if (edge.dashed) {
      path.style.strokeDasharray = "";
      path.style.strokeDashoffset = "";
      edge.dashed = false;
    }
  }
  counter.textContent = visibleCount + " / " + nodes.length;
  clock.textContent = cursorStamp();
  showsThePast();
}

function frame(now) {
  if (playing) {
    const elapsed = now - lastFrame;
    lastFrame = now;
    cursor = Math.min(nodes.length, cursor + elapsed / stepMs);
    scrubber.value = String(cursor);
    if (cursor >= nodes.length) stopPlaying();
  }
  reveal(now);
  physics();
  draw();
  requestAnimationFrame(frame);
}

// --- the controls -------------------------------------------------------------------------------------

function setMode(replaying) {
  modeChip.textContent = replaying ? "REPLAY" : "LIVE";
  modeChip.classList.toggle("replay", replaying);
  clock.classList.toggle("playing", replaying);
}

function stopPlaying() {
  playing = false;
  playButton.textContent = "\\u25B6 Replay";
  setMode(cursor < nodes.length);
}

playButton.addEventListener("click", () => {
  if (playing) { stopPlaying(); return; }
  deselect();
  cursor = 0;
  scrubber.value = "0";
  for (const n of nodes) { n.shown = false; n.enteredAt = 0; }
  for (const e of edges) { e.shown = false; e.enteredAt = 0; }
  unfocus();
  hideTip();
  playing = true;
  lastFrame = performance.now();
  playButton.textContent = "\\u23F8 Pause";
  setMode(true);
});

scrubber.setAttribute("step", "0.01");
scrubber.addEventListener("input", () => {
  playing = false;
  playButton.textContent = "\\u25B6 Replay";
  cursor = Number(scrubber.value);
  setMode(cursor < nodes.length);
});

panelClose.addEventListener("click", deselect);
canvas.addEventListener("click", deselect);
window.addEventListener("keydown", (event) => { if (event.key === "Escape") deselect(); });

dockHead.addEventListener("click", () => dock.classList.toggle("shut"));

window.addEventListener("resize", () => {
  width = window.innerWidth; height = window.innerHeight;
});

fetch("/console/graph.json")
  .then((r) => r.json())
  .then((data) => {
    payload = data;
    build(data, null);
    requestAnimationFrame(frame);
    // A minute is slow enough to be free and fast enough that a page left open on a wall is
    // never more than a tick behind the agent.
    polling = window.setInterval(poll, 60000);
  })
  .catch(() => { document.getElementById("empty").style.display = "flex"; });
"""
