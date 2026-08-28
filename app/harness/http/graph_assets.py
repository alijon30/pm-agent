"""The graph page's stylesheet and its force simulation, as strings.

They live apart from console.py for one reason: they are an asset, not logic. Nothing here is
imported by anything else, nothing here can be unit-tested by calling it, and mixing three
hundred lines of JavaScript into a module that assembles documents would make both harder to
read.

There is no library. A force-directed layout is a hundred lines of arithmetic — repulsion,
springs, damping — and at a few hundred nodes the naive O(n²) pass is far below one frame's
budget. A CDN would have cost the page its self-containment, which is the property that lets it
be served from a locked-down Cloud Run service and opened by a judge with no network trust."""

from __future__ import annotations

GRAPH_STYLE = """
:root { --bg:#0b0d12; --fg:#e6e8ec; --muted:#8892a4; --line:#222736; --panel:#12151d; }
* { box-sizing: border-box; }
html, body { margin:0; height:100%; overflow:hidden; background:var(--bg); color:var(--fg);
  font:14px/1.5 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif; }
#stage { position:fixed; inset:0; }
svg { width:100%; height:100%; display:block; cursor:grab; }
svg:active { cursor:grabbing; }

header { position:fixed; top:18px; left:20px; z-index:3; pointer-events:none; }
header h1 { margin:0; font-size:16px; font-weight:650; letter-spacing:.01em; }
header p { margin:2px 0 0; font-size:12.5px; color:var(--muted); }
header a { pointer-events:auto; color:var(--muted); text-decoration:none; border-bottom:1px
  solid var(--line); }
header a:hover { color:var(--fg); }

#legend { position:fixed; top:86px; left:20px; z-index:3; display:flex; flex-direction:column;
  gap:5px; font-size:12px; color:var(--muted); }
#legend span { display:flex; align-items:center; gap:7px; }
#legend i { width:9px; height:9px; border-radius:50%; display:inline-block; }

#controls { position:fixed; left:50%; transform:translateX(-50%); bottom:20px; z-index:3;
  display:flex; align-items:center; gap:14px; background:var(--panel);
  border:1px solid var(--line); border-radius:10px; padding:10px 14px;
  box-shadow:0 8px 30px rgba(0,0,0,.45); }
button { background:#1b2030; color:var(--fg); border:1px solid var(--line); border-radius:7px;
  padding:6px 13px; font:inherit; font-size:13px; cursor:pointer; }
button:hover { background:#232a3d; }
input[type=range] { width:min(46vw,440px); accent-color:#88c0d0; cursor:pointer; }
#clock { font-variant-numeric:tabular-nums; color:var(--muted); min-width:112px;
  font-size:12.5px; }
#count { color:var(--muted); font-size:12.5px; min-width:74px; text-align:right; }

.edge { stroke:#2a3142; stroke-width:1; }
.edge.watches { stroke-dasharray:3 3; }
.edge.learned { stroke:#4a3a2c; stroke-dasharray:2 4; }
.node { cursor:default; }
.node.link { cursor:pointer; }
.node circle { stroke:#0b0d12; stroke-width:1.5; }
.node.link:hover circle { stroke:#e6e8ec; }
.label { fill:#9aa3b5; font-size:10.5px; pointer-events:none; paint-order:stroke;
  stroke:#0b0d12; stroke-width:3px; stroke-linejoin:round; }
.label.strong { fill:#cbd2df; font-size:11px; }
.label.hidden { opacity:0; }
.early circle { animation:pulse 1.9s ease-in-out infinite; }
@keyframes pulse {
  0%,100% { filter:drop-shadow(0 0 0 rgba(163,190,140,0)); }
  50% { filter:drop-shadow(0 0 7px rgba(163,190,140,.95)); }
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
  enterBurst: 2.4,      // the kick a node gets as it appears, so arrivals feel alive
  enterMs: 320,         // how long a node takes to scale in
  replayMs: 20000,      // a full replay lands in about this long
  stepMaxMs: 1200,      // ...unless there are few enough events to give each one this
};

const COLORS = {
  meeting: "#b48ead", decision: "#ebcb8b", issue: "#5e81ac",
  person: "#a3be8c", check: "#4c566a", lesson: "#d08770",
};
const RADIUS = { meeting: 11, decision: 8, issue: 10, person: 9, check: 6, lesson: 7 };
const ALWAYS_LABELLED = new Set(["issue", "person"]);
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

const svg = document.getElementById("canvas");
const gEdges = document.getElementById("edges");
const gNodes = document.getElementById("nodes");
const scrubber = document.getElementById("scrubber");
const clock = document.getElementById("clock");
const counter = document.getElementById("count");
const playButton = document.getElementById("play");

// The replay advances over nodes, not over milliseconds. Everything a single call produces
// shares a timestamp to the second, so a clock-driven cursor would reveal the whole story in one
// frame and then crawl through the empty night that follows. One node per step always reads.
let nodes = [], edges = [], byId = new Map();
let cursor = 0, playing = false, lastFrame = 0, stepMs = 1200;
let width = window.innerWidth, height = window.innerHeight;

function stamp(ms) {
  if (!ms) return "—";
  const d = new Date(ms);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${hh}:${mm}`;
}

function colorOf(node) {
  if (node.type !== "check") return COLORS[node.type] || "#4c566a";
  if (node.status === "failed" || node.status === "cancelled") return "#bf616a";
  if (node.status === "done") return "#a3be8c";
  return COLORS.check;
}

function build(data) {
  // Nodes start on a ring rather than at random: the first frames of a replay look composed
  // instead of like an explosion, and the simulation still finds its own shape within a second.
  nodes = (data.nodes || []).map((n, i) => {
    const angle = (i / Math.max(1, data.nodes.length)) * Math.PI * 2;
    const spread = 140 + (i % 7) * 26;
    return {
      ...n,
      index: i,
      x: width / 2 + Math.cos(angle) * spread,
      y: height / 2 + Math.sin(angle) * spread,
      vx: 0, vy: 0,
      shown: false, enteredAt: 0,
      r: RADIUS[n.type] || 7,
    };
  });
  byId = new Map(nodes.map((n) => [n.id, n]));
  edges = (data.edges || [])
    .map((e) => ({ ...e, a: byId.get(e.source), b: byId.get(e.target) }))
    .filter((e) => e.a && e.b);

  scrubber.min = "0";
  scrubber.max = String(nodes.length);
  cursor = nodes.length;
  scrubber.value = String(cursor);
  stepMs = Math.min(SIM.stepMaxMs, SIM.replayMs / Math.max(1, nodes.length));

  if (!nodes.length) document.getElementById("empty").style.display = "flex";
  draw();
}

function visible(node) { return node.index < cursor; }

function cursorStamp() {
  // The clock shows the real time of the newest thing on screen, even though the cursor counts
  // nodes: the reader wants to know when this happened, not which node it is.
  let latest = "";
  for (const n of nodes) if (n.index < cursor && n.ts > latest) latest = n.ts;
  return latest ? stamp(Date.parse(latest)) : "—";
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
    } else if (!should && node.shown) {
      node.shown = false;
      node.enteredAt = 0;
    }
  }
}

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
      a.vx += (dx / d) * force; a.vy += (dy / d) * force;
      b.vx -= (dx / d) * force; b.vy -= (dy / d) * force;
    }
  }
  for (const e of edges) {
    if (!e.a.shown || !e.b.shown) continue;
    const dx = e.b.x - e.a.x, dy = e.b.y - e.a.y;
    const d = Math.sqrt(dx * dx + dy * dy) || 1;
    const pull = (d - SIM.restLength) * SIM.spring;
    e.a.vx += (dx / d) * pull; e.a.vy += (dy / d) * pull;
    e.b.vx -= (dx / d) * pull; e.b.vy -= (dy / d) * pull;
  }
  for (const n of live) {
    n.vx += (width / 2 - n.x) * SIM.centering;
    n.vy += (height / 2 - n.y) * SIM.centering;
    n.vx *= SIM.damping; n.vy *= SIM.damping;
    const speed = Math.hypot(n.vx, n.vy);
    if (speed > SIM.maxSpeed) { n.vx *= SIM.maxSpeed / speed; n.vy *= SIM.maxSpeed / speed; }
    n.x += n.vx; n.y += n.vy;
    const pad = n.r + 26;
    n.x = Math.max(pad, Math.min(width - pad, n.x));
    n.y = Math.max(pad, Math.min(height - pad, n.y));
  }
}

function element(node) {
  if (node.el) return node.el;
  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  g.setAttribute("class", "node" + (node.url ? " link" : "") + (node.early ? " early" : ""));
  const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  circle.setAttribute("r", String(node.r));
  circle.setAttribute("fill", colorOf(node));
  const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
  label.setAttribute("class",
    "label" + (ALWAYS_LABELLED.has(node.type) ? " strong" : " hidden"));
  label.setAttribute("x", String(node.r + 6));
  label.setAttribute("y", "3.5");
  label.textContent = node.label;
  g.appendChild(circle); g.appendChild(label);
  g.addEventListener("mouseenter", () => label.classList.remove("hidden"));
  g.addEventListener("mouseleave", () => {
    if (!ALWAYS_LABELLED.has(node.type)) label.classList.add("hidden");
  });
  if (node.url) g.addEventListener("click", () => window.open(node.url, "_blank"));
  gNodes.appendChild(g);
  node.el = g;
  return g;
}

function edgeElement(edge) {
  if (edge.el) return edge.el;
  const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
  const kind = edge.rel === "watches" ? " watches" : edge.rel === "learned from" ? " learned" : "";
  line.setAttribute("class", "edge" + kind);
  gEdges.appendChild(line);
  edge.el = line;
  return line;
}

function draw() {
  const now = performance.now();
  let visibleCount = 0;
  for (const node of nodes) {
    const g = element(node);
    if (!node.shown) { g.style.display = "none"; continue; }
    visibleCount++;
    g.style.display = "";
    const age = now - node.enteredAt;
    const scale = age < SIM.enterMs ? 0.2 + 0.8 * (age / SIM.enterMs) : 1;
    g.setAttribute("transform",
      `translate(${node.x.toFixed(1)},${node.y.toFixed(1)}) scale(${scale.toFixed(3)})`);
    g.style.opacity = age < SIM.enterMs ? String(Math.min(1, age / SIM.enterMs)) : "1";
  }
  for (const edge of edges) {
    const line = edgeElement(edge);
    if (!edge.a.shown || !edge.b.shown) { line.style.display = "none"; continue; }
    line.style.display = "";
    line.setAttribute("x1", edge.a.x.toFixed(1)); line.setAttribute("y1", edge.a.y.toFixed(1));
    line.setAttribute("x2", edge.b.x.toFixed(1)); line.setAttribute("y2", edge.b.y.toFixed(1));
  }
  counter.textContent = visibleCount + " / " + nodes.length;
  clock.textContent = cursorStamp();
}

function frame(now) {
  if (playing) {
    const elapsed = now - lastFrame;
    lastFrame = now;
    cursor = Math.min(nodes.length, cursor + elapsed / stepMs);
    scrubber.value = String(cursor);
    if (cursor >= nodes.length) { playing = false; playButton.textContent = "▶ Replay"; }
  }
  reveal(now);
  physics();
  draw();
  requestAnimationFrame(frame);
}

playButton.addEventListener("click", () => {
  if (playing) { playing = false; playButton.textContent = "▶ Replay"; return; }
  cursor = 0;
  scrubber.value = String(cursor);
  for (const n of nodes) { n.shown = false; n.enteredAt = 0; }
  playing = true;
  lastFrame = performance.now();
  playButton.textContent = "❚❚ Pause";
});

scrubber.setAttribute("step", "0.01");
scrubber.addEventListener("input", () => {
  playing = false;
  playButton.textContent = "▶ Replay";
  cursor = Number(scrubber.value);
});

window.addEventListener("resize", () => {
  width = window.innerWidth; height = window.innerHeight;
});

fetch("/console/graph.json")
  .then((r) => r.json())
  .then((data) => { build(data); requestAnimationFrame(frame); })
  .catch(() => { document.getElementById("empty").style.display = "flex"; });
"""
