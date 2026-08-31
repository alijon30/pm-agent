"""The graph page's stylesheet and script, kept out of console.py so that file stays about
data."""

GRAPH_STYLE = """
:root {
  --bg:#08090a; --surface:#141516; --surface-2:#1a1b1e; --border:#1f2023; --border-hi:#2a2b2f;
  --text:#f7f8f8; --text-2:#d0d6e0; --muted:#8a8f98; --faint:#5c5f66;
  --accent:#5e6ad2; --accent-hi:#6b76dd;
  /* Done is indigo, the way Linear draws it. Green means exactly one thing on this page —
     the agent finished ahead of its own schedule — so it appears nowhere else. */
  --done:#5e6ad2; --progress:#f2c94c; --failed:#eb5757; --spark:#4cb782;
  --stripe:rgba(255,255,255,.03); --stripe-2:rgba(255,255,255,.06);
  --gutter:7.08rem; --head:2.77rem; --bar:3.4rem; --top:2.75rem;
  --radius:0.46rem;
}
/* The same page in daylight: every color above, re-picked for a white ground. Dark stays the
   default; this block only applies when the toolbar toggle stamps the attribute. */
:root[data-theme="light"] {
  --bg:#f7f7f8; --surface:#ffffff; --surface-2:#f0f0f2; --border:#e2e3e6; --border-hi:#cdd0d5;
  --text:#1b1c1f; --text-2:#3d4048; --muted:#6b6f78; --faint:#9a9da5;
  --accent:#5e6ad2; --accent-hi:#4f5ac2;
  --done:#5e6ad2; --progress:#a07d0b; --failed:#d64545; --spark:#1f8a5b;
  --stripe:rgba(0,0,0,.04); --stripe-2:rgba(0,0,0,.08);
}
* { box-sizing:border-box; }
/* The page scales with the monitor. Linear ships 13px type because Linear fills its screen
   with rows; this one does not, so on a 27-inch panel everything grows a little rather than
   sitting in the top corner at phone size. */
html { font-size:clamp(13px, 0.66vw, 18px); }
html, body { margin:0; height:100%; overflow:hidden; background:var(--bg); color:var(--text);
  font:1rem/1.5 -apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Roboto,sans-serif;
  font-variant-numeric:tabular-nums; -webkit-font-smoothing:antialiased; }
button { font:inherit; cursor:pointer; border-radius:var(--radius); transition:all 120ms ease; }

/* --- toolbar ------------------------------------------------------------------------------- */
#top { position:fixed; top:0; left:0; right:0; height:var(--top); z-index:20;
  background:var(--surface); border-bottom:1px solid var(--border); display:flex;
  align-items:center; gap:14px; padding:0 14px; }
#title { font-size:1.15rem; font-weight:500; letter-spacing:-.01em; }
#tagline { font-size:0.92rem; color:var(--muted); }
#status { font-size:0.92rem; color:var(--muted); display:flex; align-items:center; gap:7px;
  margin-left:8px; min-width:0; }
#status b { font-weight:400; color:var(--text); overflow:hidden; text-overflow:ellipsis;
  white-space:nowrap; }
#status i { width:6px; height:6px; border-radius:50%; background:var(--faint); flex:none; }
#status i.busy { background:var(--accent); animation:soft 1.8s ease-in-out infinite; }
@keyframes soft { 0%,100% { opacity:1; } 50% { opacity:.4; } }
#tools { margin-left:auto; display:flex; align-items:center; gap:12px; }
.flat { background:transparent; color:var(--muted); border:1px solid var(--border);
  padding:5px 11px; font-size:0.92rem; }
.flat:hover { border-color:var(--border-hi); color:var(--text); }
#avatars { display:flex; align-items:center; }
#avatars .who { margin-left:-6px; cursor:pointer; transition:transform 120ms ease; }
#avatars .who:first-child { margin-left:0; }
#avatars .who:hover { transform:translateY(-1px); z-index:2; }
.disc { width:1.7rem; height:1.7rem; border-radius:50%; background:var(--border-hi);
  color:var(--text); font-size:0.77rem; font-weight:500; display:flex; align-items:center;
  justify-content:center; border:1.5px solid var(--surface); }
#link { color:var(--muted); font-size:0.92rem; text-decoration:none; }
#link:hover { color:var(--text); }
#nav { display:flex; gap:2px; background:var(--bg); border:1px solid var(--border);
  border-radius:var(--radius); padding:2px; }
#nav a { font-size:0.92rem; color:var(--muted); text-decoration:none; padding:3px 10px;
  border-radius:calc(var(--radius) - 2px); }
#nav a.on { background:var(--surface-2); color:var(--text); }
#nav a:hover { color:var(--text); }

/* --- the grid ------------------------------------------------------------------------------ */
#stage { position:fixed; top:var(--top); left:0; right:0; bottom:var(--bar); overflow:hidden;
  cursor:grab; }
#stage.dragging { cursor:grabbing; }
#world { position:absolute; top:0; left:0; height:100%; }
#canvas { position:absolute; top:0; left:0; overflow:visible; z-index:2; pointer-events:none; }
#layer { position:absolute; top:0; left:0; z-index:1; }
.n { z-index:3; }

/* Day columns: a real table, separated by hairlines. */
.col { position:absolute; top:0; border-left:1px solid var(--border); }
.col.future { background-image:repeating-linear-gradient(45deg,
  var(--stripe) 0 1px, transparent 1px 7px); }
.col-head { position:absolute; top:0; height:var(--head); display:flex; align-items:center;
  font-size:0.92rem; font-weight:500; color:var(--muted); white-space:nowrap; padding-left:12px;
  z-index:4; }
.col-head.today { color:var(--text); border-bottom:2px solid var(--accent); }
.col-sub { position:absolute; font-size:0.85rem; color:var(--faint); white-space:nowrap;
  padding-left:12px; z-index:4; }
#headband { position:absolute; top:0; left:0; height:var(--head); z-index:3;
  background:var(--surface); border-bottom:1px solid var(--border); }

/* Lane rows. */
.lane { position:absolute; left:0; border-top:1px solid var(--border); }
.lane-tag { position:absolute; left:12px; right:8px; }
.lane-name { font-size:0.85rem; color:var(--muted); }
.lane-about { font-size:0.77rem; color:var(--faint); line-height:1.3; margin-top:1px; }
.lane-none { position:absolute; font-size:0.85rem; color:var(--faint); padding-left:12px;
  white-space:nowrap; }
/* Conversations are divided at half the weight of a day, so the day stays the stronger line. */
.strip-rule { position:absolute; top:0; width:1px; background:var(--border); opacity:.5; }
.hair-label { position:absolute; font-size:0.77rem; color:var(--faint); white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis; }
#gutter { position:fixed; top:calc(var(--top) + var(--head)); left:0; width:var(--gutter);
  bottom:var(--bar); z-index:6; background:var(--bg);
  border-right:1px solid var(--border); pointer-events:none; }

#nowline { stroke:var(--accent); stroke-width:1; }
#nowtag { position:absolute; z-index:5; font-size:0.77rem; font-weight:500; color:#fff;
  background:var(--accent); border-radius:3px; padding:1px 6px; transform:translateX(-50%); }

/* --- nodes are rows and chips -------------------------------------------------------------- */
.n { position:absolute; transform:translate(-50%,-50%); cursor:pointer; }
.n.hidden { display:none; }
.n.enter { animation:fade 120ms ease both; }
@keyframes fade { from { opacity:0; } to { opacity:1; } }
.n.dim { opacity:.25; }

.chip { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
  transition:border-color 120ms ease; }
.n:hover .chip { border-color:var(--border-hi); background:var(--surface-2); }
.n.sel .chip { border-color:var(--accent); }
/* A selected row wears the accent rail Linear puts on the row you are looking at. */
.n.sel .issue { box-shadow:inset 2px 0 0 var(--accent); }

/* An issue reads like a row in a tracker. */
.issue { width:20rem; max-width:22rem; min-height:2.15rem; display:flex; align-items:flex-start;
  gap:0.54rem; padding:0.46rem 0.62rem; }
.issue .ico, .issue .bars, .issue .disc { margin-top:1px; }
.issue .key { font-size:0.92rem; font-weight:500; color:var(--text); flex:none; }
.issue .ttl { font-size:0.92rem; color:var(--muted); line-height:1.35; flex:1;
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
.ico { flex:none; display:block; }
.bars { flex:none; display:flex; align-items:flex-end; gap:1.5px; height:10px; }
.bars i { width:2.5px; background:var(--faint); border-radius:1px; }
.bars i.on { background:var(--muted); }

/* A call is the one thing with more to say than a row. */
.card { width:16.9rem; padding:9px 10px 8px; }
.card .ttl { font-size:1rem; font-weight:500; line-height:1.35;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.card .when { margin-top:2px; font-size:0.85rem; color:var(--muted); }
.strip { display:flex; gap:2px; margin-top:8px; }
.seg { flex:1; height:4px; border-radius:2px; background:var(--border); }
.seg.done { background:var(--done); }
/* In flight is the only thing on the page that moves. */
.seg.leased { background:var(--progress); animation:soft 1.8s ease-in-out infinite; }
.seg.failed { background:var(--failed); }
.seg.skipped { background-image:repeating-linear-gradient(45deg,
  var(--stripe-2) 0 1px, transparent 1px 4px); background-color:var(--border); }
.note { margin-top:6px; font-size:0.85rem; color:var(--muted); overflow:hidden;
  text-overflow:ellipsis; white-space:nowrap; }

/* A decision, a conflict and a check are all text chips with a leading mark. */
.text-chip { width:16.9rem; max-width:18rem; padding:0.54rem 0.7rem; display:flex;
  gap:0.54rem; align-items:flex-start; }
.chip-body { flex:1; min-width:0; }
.text-chip .from { margin-top:3px; font-size:0.77rem; color:var(--faint);
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.text-chip .up { color:var(--spark); }
.text-chip .g { font-size:0.77rem; line-height:1.5; color:var(--muted); flex:none; }
.text-chip .g.warn { color:var(--progress); }
.text-chip p { margin:0; font-size:0.92rem; line-height:1.35; color:var(--text);
  display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden; }
.check p { -webkit-line-clamp:2; }
.check { min-height:2rem; }

/* What the agent said sits on a hairline as dots. */
.hair { position:absolute; height:1px; background:var(--border); z-index:1; }
.dot { width:0.31rem; height:0.31rem; border-radius:50%; background:var(--muted); }
.n:hover .dot { background:var(--text); }

.edge { fill:none; stroke-width:1; opacity:0; transition:opacity 120ms ease; }
.edge.dep { opacity:.55; stroke:var(--muted); marker-end:url(#arrow); }
.edge.lit { opacity:.9; stroke:var(--accent); }

/* --- bottom bar ---------------------------------------------------------------------------- */
#controls { position:fixed; left:0; right:0; bottom:0; height:var(--bar); z-index:20;
  background:var(--surface); border-top:1px solid var(--border); display:flex;
  align-items:center; gap:14px; padding:0 14px; }
#play { background:var(--accent); color:#fff; border:none; padding:6px 14px; font-size:0.92rem;
  font-weight:500; }
#play:hover { background:var(--accent-hi); }
input[type=range] { -webkit-appearance:none; appearance:none; flex:1; height:16px;
  background:transparent; cursor:pointer; }
input[type=range]::-webkit-slider-runnable-track { height:2px; background:var(--border-hi); }
input[type=range]::-webkit-slider-thumb { -webkit-appearance:none; width:10px; height:10px;
  border-radius:50%; background:var(--text); margin-top:-4px; border:none; }
input[type=range]::-moz-range-track { height:2px; background:var(--border-hi); }
input[type=range]::-moz-range-thumb { width:10px; height:10px; border-radius:50%;
  background:var(--text); border:none; }
#clock { font-size:0.92rem; color:var(--muted); }
#mode { font-size:0.85rem; color:var(--muted); display:flex; align-items:center; gap:6px;
  border:1px solid var(--border); border-radius:999px; padding:3px 9px; }
#mode i { width:6px; height:6px; border-radius:50%; background:var(--accent); }
#count { font-size:0.92rem; color:var(--faint); }

/* --- the story panel, as an issue sidebar --------------------------------------------------- */
#panel { position:fixed; top:var(--top); right:0; bottom:0; width:clamp(24rem, 22vw, 26rem); z-index:19;
  background:var(--surface); border-left:1px solid var(--border); overflow-y:auto;
  padding:16px 18px 32px; transform:translateX(100%); transition:transform 120ms ease; }
#panel.open { transform:none; }
#panel-close { position:absolute; top:12px; right:14px; background:transparent;
  border:1px solid var(--border); color:var(--muted); padding:3px 8px; font-size:0.92rem; }
.p-key { display:flex; align-items:center; gap:8px; font-size:0.92rem; font-weight:500;
  color:var(--muted); }
/* The panel is where the whole title lives; nothing is cut here. */
.p-title { margin-top:8px; font-size:1rem; line-height:1.45; color:var(--text);
  overflow-wrap:anywhere; }
.p-sum { font-size:0.92rem; color:var(--muted); margin-bottom:8px; }
.p-link, .p-row { background:transparent; border:none; color:var(--accent); font-size:0.92rem;
  padding:0; text-align:left; }
.p-link:hover, .p-row:hover { text-decoration:underline; }
.p-row { display:block; width:100%; border:1px solid var(--border); border-radius:var(--radius);
  padding:7px 9px; margin-bottom:5px; color:var(--text); line-height:1.4; }
.p-row:hover { border-color:var(--border-hi); text-decoration:none; }
.p-head { margin:22px 0 9px; font-size:0.85rem; letter-spacing:.06em; text-transform:uppercase;
  color:var(--faint); }
.p-fact { display:grid; grid-template-columns:112px 1fr; gap:10px; padding:5px 0;
  font-size:0.92rem; align-items:center; }
.p-fact b { color:var(--muted); font-weight:400; }
.p-fact span { color:var(--text); display:flex; align-items:center; gap:6px; }
.p-story { position:relative; padding-left:16px; }
.p-story::before { content:""; position:absolute; left:3px; top:8px; bottom:8px; width:1px;
  background:var(--border); }
.p-line { position:relative; display:flex; gap:10px; align-items:baseline; padding:5px 0;
  font-size:0.92rem; line-height:1.45; }
.p-dot { position:absolute; left:-16px; top:10px; width:6px; height:6px; border-radius:50%;
  background:var(--faint); }
.p-line em { font-style:normal; color:var(--faint); font-size:0.85rem; margin-left:auto;
  white-space:nowrap; padding-left:10px; }
.p-none { color:var(--faint); font-size:0.92rem; }
.p-open { display:inline-block; margin-top:22px; background:var(--accent); color:#fff;
  font-size:0.92rem; font-weight:500; padding:7px 13px; border-radius:var(--radius);
  text-decoration:none; }
.p-open:hover { background:var(--accent-hi); }

#tooltip { position:fixed; z-index:30; background:var(--surface); border:1px solid var(--border);
  border-radius:var(--radius); padding:7px 10px; max-width:280px; font-size:0.92rem;
  pointer-events:none; opacity:0; transition:opacity 120ms ease;
  box-shadow:0 1px 2px rgba(0,0,0,.4); }
#tooltip.on { opacity:1; }
.t-kind { font-size:0.85rem; color:var(--muted); }
.t-label { margin-top:2px; line-height:1.4; }
.t-meta { margin-top:3px; color:var(--faint); font-size:0.85rem; }

#empty { position:fixed; inset:0; display:none; align-items:center; justify-content:center;
  color:var(--faint); font-size:1rem; z-index:6; }
"""


GRAPH_SCRIPT = """
// The graph is a diagram, not a simulation. Every position is decided by the server (see
// graph_layout.py) and this file only reads it: x is the day, y is the lane, and the order
// inside a column is the order things happened. Nothing here moves on its own.
//
// Labels are issue titles and model output. The server escapes them and this page never uses
// innerHTML — every string reaches the document through textContent, so a title containing
// markup stays a title.

// These are taste, not truth: the numbers the look depends on. Nothing here is a fact about
// the data, and every one of them is safe to argue with.
const TUNING = {
  head: 36,             // the sticky day-header row
  gap: 24,              // the air between two things in a row
  gutter: 92,           // the left strip the lane names live in
  gutterTight: 80,      // ...and what it shrinks to when the week is close to fitting
  labelAt: 140,         // a strip narrower than this gets dots without a caption
  labelRoom: 96,        // the room a day label needs before it is worth drawing
  anchor: 0.65,         // where the now line sits when the week is wider than the screen
  laneMin: 64,          // a lane with something in it
  laneEmpty: 36,        // a lane with nothing in it yet
  lanePad: 16,          // the air under a lane's last row
  rowGap: 12,           // between the last primary row and the row of dots
  smallLine: 12,        // between wrapped lines of secondary dots
  minSlot: 244,         // a decision chip plus its gap
  issueSlot: 284,       // an issue row plus its gap
  cardSlot: 244,        // a call card plus its gap
  checkSlot: 224,       // a check pill plus its gap
  smallSlot: 14,        // a dot on the hairline
  rowPitch: 54,         // an issue row that may run to two lines
  chipPitch: 74,        // a text chip that may run to three
  cardPitch: 124,       // a call card with its stage strip
  stepMs: 700,          // replay: dwell per node
  edgeBow: 0.4,         // how much a cross-column thread bends
  tailColumns: 2,       // past columns kept in view when the timeline is too wide to fit
  longEdgeColumns: 2,   // a dependency reaching further than this is only drawn on demand
};

const LANES = ["heard", "understood", "did", "watching", "learned"];
const LANE_NAME = {
  heard: "Heard", understood: "Understood", did: "Did", watching: "Watching",
  learned: "Learned",
};
// A stranger has no idea what "Understood" is a row of. One line each, under the label.
const LANE_ABOUT = {
  heard: "calls and asks that came in",
  understood: "decisions and disagreements",
  did: "issues filed, messages sent",
  watching: "checks — past and scheduled",
  learned: "lessons from its own record",
};
const LANE_EMPTY_COPY = {
  learned: "Nothing yet — lessons come from the daily review",
  heard: "Nothing yet — no calls on this day",
  understood: "Nothing yet — no decisions recorded",
  did: "Nothing yet — nothing was filed",
  watching: "Nothing yet — nothing scheduled",
};
const NS = "http://www.w3.org/2000/svg";
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const DONE = "#5e6ad2", PROGRESS = "#f2c94c", FAILED = "#eb5757", MUTED = "#8a8f98";
// The only green on the page: work that came back early.
const SPARK = "#4cb782";

// Which of Linear's status marks each state wears. "early" is done with an arrow, because the
// agent finishing ahead of its own schedule is the thing worth pointing at.
const CHECK_ICON = {
  met: "done", early: "early", unmet: "cancelled", failed: "cancelled",
  leased: "progress", blocked: "blocked", queued: "backlog",
};
const CATEGORY_TINT = {
  filed: DONE, reported: DONE, early: SPARK, planned: "#5e6ad2", posted: "#5e6ad2",
  // Reading and reconciling are the quiet half of the loop, on both pages.
  nudged: PROGRESS, checked: MUTED, extracted: MUTED, reconciled: MUTED,
  deferred: PROGRESS, refused: FAILED, failed: FAILED, cancelled: FAILED,
  reverted: PROGRESS, pending: MUTED, done: MUTED,
};
const FACT_LABELS = {
  state: "Status", assignee: "Assignee", priority: "Priority", due: "Due date",
  filed_from_call: "From a call", reason: "Why", status: "Status", on_unmet: "If unmet",
  observed: "Last seen", early: "Resolved early", statement: "Decided", quote: "Said",
  source: "Source", role: "Role", owns: "Owns", pings_received: "Pings sent",
  title: "Call", when: "When", produced: "Produced", evidence: "Learned from",
};

// Every number in TUNING is expressed at a 13px root. The page scales with the viewport
// (html { font-size: clamp(...) }), so one measurement turns them all into today's pixels.
const BASE_REM = 13;
let rem = BASE_REM;

function measureRem() {
  const size = parseFloat(getComputedStyle(document.documentElement).fontSize);
  rem = Number.isFinite(size) && size > 0 ? size : BASE_REM;
}

function u(value) { return Math.round(value * (rem / BASE_REM)); }

// The share of a tall screen each lane takes when there is height to spare. Mirrors
// LANE_SHARE in graph_layout.py, which is where the rule is specified and tested.
const LANE_SHARE = {
  heard: 0.18, understood: 0.17, did: 0.30, watching: 0.22, learned: 0.13,
};
const FUTURE_STRETCH = 1.3;
const SQUEEZE_LIMIT = 1.2;
// A lane may take at most half again its content in spare height; past that it is padding.
const LANE_STRETCH_CAP = 1.5;

const stage = document.getElementById("stage");
const world = document.getElementById("world");
const canvas = document.getElementById("canvas");
const gEdges = document.getElementById("edges");
const gRules = document.getElementById("rules");
const layer = document.getElementById("layer");
const gutter = document.getElementById("gutter");
const nowTag = document.getElementById("nowtag");
const scrubber = document.getElementById("scrubber");
const clock = document.getElementById("clock");
const counter = document.getElementById("count");
const playButton = document.getElementById("play");
const modeChip = document.getElementById("mode");
const tooltip = document.getElementById("tooltip");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const avatars = document.getElementById("avatars");
const nowButton = document.getElementById("now-btn");
const panel = document.getElementById("panel");
const panelBody = document.getElementById("panel-body");
const panelClose = document.getElementById("panel-close");

let payload = null, nodes = [], edges = [], byId = new Map(), columns = [];
let cursor = 0, playing = false, lastFrame = 0, selected = null;
let laneTop = {}, laneHeight = {}, laneLines = {}, diagramHeight = 0, contentHeight = 0;
let strips = new Map();
let laneStretch = {}, laneNeed = {};
let layoutPlan = { mode: 'fit', scrollLeft: 0, total: 0 };
let panX = 0, worldWidth = 0, dragging = false, dragFrom = 0, dragPan = 0, moved = false;
let gutterWidth = 92;

function svgEl(tag) { return document.createElementNS(NS, tag); }

function stamp(ms) {
  if (!ms || Number.isNaN(ms)) return "";
  const d = new Date(ms);
  return `${MONTHS[d.getMonth()]} ${d.getDate()} ` +
         `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function initials(name) {
  return String(name || "").split(/\\s+/).filter(Boolean).slice(0, 2)
    .map((w) => w[0].toUpperCase()).join("");
}

// --- the status vocabulary ----------------------------------------------------------------------

function statusIcon(kind, size) {
  // Linear's own marks, drawn here rather than fetched: a ring for not-started, a half-filled
  // ring for underway, a tick for done, a cross for cancelled. Every one carries a <title> so
  // it is not a shape with no name to a screen reader.
  const s = size || 14;
  const svg = svgEl("svg");
  svg.setAttribute("class", "ico");
  svg.setAttribute("viewBox", "0 0 14 14");
  svg.setAttribute("width", s); svg.setAttribute("height", s);
  const label = svgEl("title");
  label.textContent = kind;
  svg.appendChild(label);

  const colour = { done: DONE, early: DONE, cancelled: FAILED, progress: PROGRESS }[kind]
    || MUTED;  // backlog, scheduled and blocked are all the quiet grey
  const ring = svgEl("circle");
  ring.setAttribute("cx", "7"); ring.setAttribute("cy", "7"); ring.setAttribute("r", "5.5");
  ring.setAttribute("fill", "none");
  ring.setAttribute("stroke", colour);
  ring.setAttribute("stroke-width", "1.5");
  if (kind === "blocked") ring.setAttribute("stroke-dasharray", "2.5 2");
  svg.appendChild(ring);

  if (kind === "progress") {
    const half = svgEl("path");
    half.setAttribute("d", "M7 3.2 A3.8 3.8 0 0 1 7 10.8 Z");
    half.setAttribute("fill", colour);
    svg.appendChild(half);
  }
  if (kind === "done" || kind === "early") {
    const tick = svgEl("path");
    tick.setAttribute("d", "M4.4 7.1 L6.2 8.9 L9.6 5.2");
    tick.setAttribute("fill", "none"); tick.setAttribute("stroke", colour);
    tick.setAttribute("stroke-width", "1.6"); tick.setAttribute("stroke-linecap", "round");
    svg.appendChild(tick);
  }
  if (kind === "cancelled") {
    const cross = svgEl("path");
    cross.setAttribute("d", "M4.8 4.8 L9.2 9.2 M9.2 4.8 L4.8 9.2");
    cross.setAttribute("stroke", colour); cross.setAttribute("stroke-width", "1.5");
    cross.setAttribute("stroke-linecap", "round");
    svg.appendChild(cross);
  }
  return svg;
}

function priorityBars(priority) {
  // Linear's three bars, filled by urgency. Nothing is drawn when nobody set a priority —
  // an empty glyph would read as "lowest", which is a claim the data does not make.
  if (!priority || priority < 1 || priority > 4) return null;
  const filled = Math.max(0, 4 - priority);
  const wrap = el("span", "bars");
  wrap.title = `Priority ${priority}`;
  for (let i = 0; i < 3; i++) {
    const bar = el("i");
    bar.style.height = (4 + i * 3) + "px";
    if (i < filled) bar.className = "on";
    wrap.appendChild(bar);
  }
  return wrap;
}

function avatar(name, size) {
  const disc = el("span", "disc", initials(name));
  disc.title = name;
  if (size) {
    disc.style.width = size + "px"; disc.style.height = size + "px";
    disc.style.fontSize = Math.round(size * 0.42) + "px";
  }
  return disc;
}

// --- geometry ------------------------------------------------------------------------------------

// The width algorithm. Specified and tested as `plan_widths` in graph_layout.py; this is the
// same three branches, and `data-layout` on <body> reports which one ran so the result can be
// checked without a screenshot.
const SPARE_CAP = 1.5;
const TODAY_AT = 0.45;

function planWidths(cols, viewport, gutter) {
  const mins = cols.map((c) => Math.max(0, c.min | 0));
  const total = gutter + mins.reduce((a, b) => a + b, 0);
  if (!cols.length) return { mode: "fit", widths: [], scrollLeft: 0, total: gutter };

  if (total <= viewport) return fitWidths(cols, mins, viewport, gutter, "fit");

  const tight = cols.map((c) => Math.max(0, (c.shrunk | 0) || (c.min | 0)));
  const tightTotal = gutter + tight.reduce((a, b) => a + b, 0);
  if (total <= viewport * SQUEEZE_LIMIT && tightTotal <= viewport) {
    // Shrinking is for getting on screen, not for filling it: nothing grows.
    return { mode: "shrink", widths: tight, scrollLeft: 0, total: tightTotal };
  }
  return { mode: "scroll", widths: mins, total, tightTotal, viewportUsed: viewport,
           scrollLeft: openingAt(cols, mins, viewport, gutter) };
}

function fitWidths(cols, mins, viewport, gutter, mode) {
  const widths = mins.slice();
  const spare = viewport - gutter - mins.reduce((a, b) => a + b, 0);
  // Only a past day holding real work grows; a scheduled column and a day of dots are the
  // size they are on purpose.
  const growable = cols.map((c, i) => i).filter(
    (i) => !cols[i].future && !cols[i].collapsed && (cols[i].primary | 0) > 0);
  const weight = growable.reduce((sum, i) => sum + (cols[i].primary | 0), 0);
  if (spare > 0 && weight) {
    for (const i of growable) {
      const share = spare * ((cols[i].primary | 0) / weight);
      widths[i] = Math.min(Math.floor(mins[i] * SPARE_CAP), mins[i] + Math.floor(share));
    }
  }
  return { mode, widths, scrollLeft: 0,
           total: gutter + widths.reduce((a, b) => a + b, 0) };
}

function openingAt(cols, mins, viewport, gutter) {
  const edges = [0];
  let at = gutter, todayLeft = 0;
  cols.forEach((c, i) => {
    if (c.today) todayLeft = at;
    const strips = (c.strips || []).filter((w) => w > 0);
    let span = at;
    for (const strip of (strips.length ? strips : [mins[i]])) {
      edges.push(Math.max(0, span - gutter));
      span += strip;
    }
    at += mins[i];
  });
  const want = todayLeft - Math.floor(viewport * TODAY_AT);
  const limit = Math.max(0, gutter + mins.reduce((a, b) => a + b, 0) - viewport);
  const reachable = [...new Set(edges)].sort((a, b) => a - b)
    .filter((e) => e <= Math.min(want, limit));
  return reachable.length ? reachable[reachable.length - 1] : 0;
}

function slotWidth(lane, row) {
  if (row === "secondary") return u(TUNING.smallSlot);
  if (lane === "heard") return u(TUNING.cardSlot);
  if (lane === "did") return u(TUNING.issueSlot);
  return u(lane === "watching" ? TUNING.checkSlot : TUNING.minSlot);
}

function slotsIn(width, lane, row) {
  return Math.max(1, Math.floor(width / slotWidth(lane, row)));
}

function pitchOf(lane, row) {
  if (row === "secondary") return u(TUNING.smallLine);
  if (lane === "heard") return u(TUNING.cardPitch);
  return u(lane === "did" ? TUNING.rowPitch : TUNING.chipPitch);
}

function fitRem(data) {
  // The ceiling is what the stylesheet wants, not what a previous pass left behind: measure
  // with the inline override cleared, or a second layout reads its own 13px as the ceiling,
  // decides nothing needs doing, clears the override, and the page snaps to 17px around a
  // plan drawn at 13.
  document.documentElement.style.fontSize = "";
  measureRem();
  const ceiling = rem;
  const days = data.days || [];
  const total = days.reduce((sum, d) => sum + ((data.widths || {})[d.key] || 212), 0);
  if (!total) return;
  const room = stage.clientWidth - TUNING.gutter - 20;
  const fits = room / total;
  const wanted = Math.max(BASE_REM, Math.min(ceiling, BASE_REM * fits));
  if (wanted < ceiling - 0.01) {
    document.documentElement.style.fontSize = wanted.toFixed(2) + "px";
    measureRem();
  } else if (document.documentElement.style.fontSize) {
    document.documentElement.style.fontSize = "";
    measureRem();
  }
}

function layout(data) {
  // The root font size is the page's unit. Sized to the week before anything is placed, and
  // again on resize, because the answer changes with the window.
  fitRem(data);
  // If the whole timeline fits the viewport it is stretched to fill it; only a timeline that
  // genuinely cannot fit is panned.
  const days = data.days || [];
  const spec = (data.columns || []).length === days.length
    ? data.columns
    : days.map((d) => ({ key: d.key, min: (data.widths || {})[d.key] || 212,
                         shrunk: (data.floors || data.widths || {})[d.key] || 212, future: Boolean(d.future),
                         collapsed: false, today: Boolean(d.today), primary: 1, strips: [] }));
  const scaled = spec.map((c) => ({
    ...c, min: u(c.min), shrunk: u(c.shrunk), strips: (c.strips || []).map(u),
  }));
  const rough = scaled.reduce((sum, c) => sum + c.min, 0);
  // The gutter gives up its width before the week gives up a column: the lane names are the
  // one thing on this page that can be read narrower without losing anything.
  gutterWidth = (rough + u(TUNING.gutter) + u(20) > stage.clientWidth)
    ? u(TUNING.gutterTight) : u(TUNING.gutter);
  document.documentElement.style.setProperty("--gutter", gutterWidth + "px");

  const plan = planWidths(scaled, stage.clientWidth - u(16), gutterWidth);
  layoutPlan = plan;

  columns = [];
  let x = gutterWidth;
  days.forEach((day, i) => {
    columns.push({ ...day, x, width: plan.widths[i] });
    x += plan.widths[i];
  });
  worldWidth = x + u(16);

  const byKey = new Map(columns.map((c) => [c.key, c]));

  // Each day is divided into one strip per conversation, in the order they happened, and a
  // node sits in its own call's strip. Provenance is then a matter of looking up the page
  // rather than of clicking anything.
  strips = new Map();
  for (const column of columns) {
    const here = (data.strips || {})[column.key] || [{ group: "day", width: column.width }];
    const total = here.reduce((sum, s) => sum + s.width, 0) || 1;
    let at = column.x;
    for (const strip of here) {
      const width = Math.round(column.width * (strip.width / total));
      strips.set(`${column.key}|${strip.group}`, { x: at, width, day: column.key,
                                                   group: strip.group });
      at += width;
    }
  }

  const groups = new Map();
  for (const node of nodes) {
    const key = `${node.day}|${node.group || "day"}|${node.lane}|${node.row}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(node);
  }

  laneLines = {};
  for (const lane of LANES) laneLines[lane] = { primary: 0, secondary: 0 };
  for (const [key, members] of groups) {
    const [day, group, lane, row] = key.split("|");
    const strip = strips.get(`${day}|${group}`);
    if (!strip || !laneLines[lane]) continue;
    const lines = Math.ceil(members.length / slotsIn(strip.width, lane, row));
    laneLines[lane][row] = Math.max(laneLines[lane][row] || 0, lines);
  }

  laneNeed = {};
  const need = laneNeed;
  for (const lane of LANES) {
    const p = laneLines[lane].primary, sec = laneLines[lane].secondary;
    need[lane] = (!p && !sec)
      ? u(TUNING.laneEmpty)
      : p * pitchOf(lane, "primary")
        + (sec ? u(TUNING.rowGap) + sec * u(TUNING.smallLine) : 0) + u(TUNING.lanePad);
  }
  const headroom = stage.clientHeight - u(TUNING.head);
  // An empty lane keeps its band and donates its share to the lanes doing the work.
  const sharing = LANES.filter((lane) => need[lane] > u(TUNING.laneEmpty));
  const shareTotal = sharing.reduce((sum, lane) => sum + LANE_SHARE[lane], 0) || 1;
  const spare = Math.max(0, headroom - LANES.reduce((sum, lane) => sum + need[lane], 0));

  laneTop = {}; laneHeight = {};
  let y = u(TUNING.head);
  for (const lane of LANES) {
    laneTop[lane] = y;
    const share = sharing.includes(lane)
      ? Math.round(spare * (LANE_SHARE[lane] / shareTotal)) : 0;
    laneHeight[lane] = Math.min(need[lane] + share,
                                Math.round(need[lane] * LANE_STRETCH_CAP));
    y += laneHeight[lane];
  }
  laneStretch = {};
  for (const lane of LANES) {
    const rows = laneLines[lane].primary || 1;
    const room = laneHeight[lane] - u(TUNING.lanePad);
    laneStretch[lane] = Math.min(1.25, Math.max(1, room / (rows * pitchOf(lane, "primary"))));
  }
  contentHeight = Math.max(y, stage.clientHeight - u(4));
  diagramHeight = Math.max(contentHeight, stage.clientHeight);

  for (const [key, members] of groups) {
    const [day, group, lane, row] = key.split("|");
    const strip = strips.get(`${day}|${group}`);
    const width = strip ? strip.width : TUNING.minSlot;
    const slots = slotsIn(width, lane, row);
    const pitch = pitchOf(lane, row);
    for (const node of members) {
      const line = Math.floor(node.seq / slots);
      const slot = node.seq % slots;
      const step = width / slots;
      node.x = (strip ? strip.x : gutterWidth) + step * (slot + 0.5);
      node.slotWidth = Math.max(u(120), Math.round(step) - u(20));
      const grown = pitchOf(lane, "primary") * (laneStretch[lane] || 1);
      // Measured from the last row rather than from the lane's floor: the dots belong to the
      // work above them, not to the bottom of whatever space the lane was given.
      const below = laneTop[lane] + u(TUNING.lanePad)
        + (laneLines[lane].primary || 0) * grown;
      node.y = row === "secondary"
        ? below + u(TUNING.rowGap) + line * u(TUNING.smallLine)
        : laneTop[lane] + u(TUNING.lanePad) + line * grown + grown / 2;
    }
  }
}

// --- the grid --------------------------------------------------------------------------------------

function drawFrame() {
  gRules.textContent = "";
  layer.textContent = "";
  gutter.textContent = "";
  canvas.setAttribute("width", worldWidth);
  canvas.setAttribute("height", diagramHeight);
  world.style.width = worldWidth + "px";

  const band = el("div");
  band.id = "headband";
  band.style.width = worldWidth + "px";
  layer.appendChild(band);

  for (const column of columns) {
    const ground = el("div", "col" + (column.future ? " future" : ""));
    ground.style.left = column.x + "px";
    ground.style.width = column.width + "px";
    ground.style.height = contentHeight + "px";
    layer.appendChild(ground);

    const head = el("div", "col-head" + (column.today ? " today" : ""), column.label);
    head.style.width = column.width + "px";
    column.head = head;
    layer.appendChild(head);
    if (column.future) {
      const sub = el("div", "col-sub", "Scheduled");
      sub.style.top = (u(TUNING.head) + u(6)) + "px";
      column.sub = sub;
      layer.appendChild(sub);
    }
  }

  // A hairline between conversations, at half the weight of a day boundary so the day still
  // reads as the stronger division.
  for (const strip of strips.values()) {
    const column = columns.find((c) => c.key === strip.day);
    if (!column || Math.abs(strip.x - column.x) < 2) continue;
    const rule = el("div", "strip-rule");
    rule.style.left = strip.x + "px";
    rule.style.height = contentHeight + "px";
    layer.appendChild(rule);
  }

  for (const lane of LANES) {
    const bare = !laneLines[lane].primary && !laneLines[lane].secondary;
    const row = el("div", "lane");
    row.style.top = laneTop[lane] + "px";
    row.style.height = laneHeight[lane] + "px";
    row.style.width = worldWidth + "px";
    layer.appendChild(row);

    const tag = el("div", "lane-tag");
    tag.style.top = (laneTop[lane] - u(TUNING.head) + u(9)) + "px";
    tag.title = LANE_ABOUT[lane];
    tag.appendChild(el("div", "lane-name", LANE_NAME[lane]));
    tag.appendChild(el("div", "lane-about", LANE_ABOUT[lane]));
    gutter.appendChild(tag);

    if (bare) {
      const none = el("div", "lane-none", LANE_EMPTY_COPY[lane] || "Nothing yet");
      none.style.left = gutterWidth + "px";
      none.style.top = (laneTop[lane] + u(10)) + "px";
      layer.appendChild(none);
    } else if (laneLines[lane].secondary) {
      // The dots hang on a hairline so a row of them reads as one thing.
      const below = laneTop[lane] + u(TUNING.lanePad)
        + laneLines[lane].primary * pitchOf(lane, "primary") * (laneStretch[lane] || 1);
      const hair = el("div", "hair");
      hair.style.top = (below + u(TUNING.rowGap)) + "px";
      hair.style.left = gutterWidth + "px";
      hair.style.width = (worldWidth - gutterWidth) + "px";
      layer.appendChild(hair);
      // A row of anonymous dots is undiscoverable, so each strip's row says what it is.
      const counts = new Map();
      for (const node of nodes) {
        if (node.lane !== lane || node.row !== "secondary") continue;
        const key = `${node.day}|${node.group || "day"}`;
        counts.set(key, (counts.get(key) || 0) + 1);
      }
      for (const [key, count] of counts) {
        const strip = strips.get(key);
        // A caption wider than its strip runs into its neighbour's, so a narrow strip gets
        // dots alone — they still name themselves on hover.
        if (!strip || strip.width < u(TUNING.labelAt)) continue;
        const mark = el("div", "hair-label",
          `Slack \u00b7 ${count} post${count === 1 ? "" : "s"}`);
        mark.style.left = (strip.x + u(6)) + "px";
        mark.style.top = (below + u(TUNING.rowGap) - u(13)) + "px";
        mark.style.maxWidth = (strip.width - u(12)) + "px";
        layer.appendChild(mark);
      }
    }
  }
  drawNowLine();
  stickHeaders();
}

function stickHeaders() {
  // A half-scrolled day used to lose its date entirely, because the label was pinned to the
  // column's left edge and that edge was off screen. The label slides along instead, staying
  // just inside whichever of the column or the viewport starts later.
  const leftEdge = -panX + gutterWidth;
  for (const column of columns) {
    if (!column.head) continue;
    const right = column.x + column.width;
    // A column scrolled down to a sliver has no room for its date. Clamping the label into
    // that sliver used to push it off the left edge entirely, which is worse than no label.
    const sliver = right - leftEdge < u(TUNING.labelRoom);
    column.head.style.display = sliver ? "none" : "";
    if (column.sub) column.sub.style.display = sliver ? "none" : "";
    if (sliver) continue;
    const at = Math.max(column.x, leftEdge);
    column.head.style.left = at + "px";
    column.head.style.width = (right - at) + "px";
    if (column.sub) column.sub.style.left = at + "px";
  }
}

function nowX() {
  const today = columns.find((c) => c.today);
  const settled = nodes.filter((n) => !n.future_node);
  const last = settled.length ? Math.max(...settled.map((n) => n.x)) : 0;
  if (!today) return last + u(60);
  return Math.max(today.x + u(16),
                  Math.min(last + u(60), today.x + today.width - u(6)));
}

function drawNowLine() {
  const x = nowX();
  const line = svgEl("line");
  line.setAttribute("id", "nowline");
  line.setAttribute("x1", x); line.setAttribute("x2", x);
  line.setAttribute("y1", u(TUNING.head)); line.setAttribute("y2", contentHeight);
  gRules.appendChild(line);
  nowTag.textContent = "Now";
  nowTag.style.left = x + "px";
  nowTag.style.top = (u(TUNING.head) + u(4)) + "px";
}

// --- what each thing looks like ---------------------------------------------------------------------

function issueRow(node) {
  const chip = el("div", "chip issue");
  const facts = node.facts || {};
  chip.appendChild(statusIcon(facts.state === "Done" ? "done" : "backlog", 14));
  const bars = priorityBars(facts.priority);
  if (bars) chip.appendChild(bars);
  chip.appendChild(el("span", "key", node.identifier || ""));
  chip.appendChild(el("span", "ttl", node.label));
  if (facts.assignee) chip.appendChild(avatar(facts.assignee, 18));
  return chip;
}

function callCard(node) {
  const card = el("div", "chip card");
  card.appendChild(el("div", "ttl", node.label));
  card.appendChild(el("div", "when",
    node.type === "intake" ? (node.who || "asked") : stamp(Date.parse(node.ts))));

  if (node.stages && node.stages.length) {
    const strip = el("div", "strip");
    const settled = node.stages.filter((s) => s.note);
    const note = el("div", "note", settled.length
      ? `${settled[settled.length - 1].name} — ${settled[settled.length - 1].note}` : "");
    for (const segment of node.stages) {
      const seg = el("div", "seg " + segment.state);
      seg.title = segment.note ? `${segment.name} — ${segment.note}`
                               : `${segment.name} — ${segment.state}`;
      seg.addEventListener("mouseenter", () => { note.textContent = seg.title; });
      seg.addEventListener("click", (e) => { e.stopPropagation(); openStage(node, segment); });
      strip.appendChild(seg);
    }
    card.appendChild(strip);
    card.appendChild(note);
  }
  return card;
}

function textChip(node) {
  const chip = el("div", "chip text-chip" + (node.type === "check" ? " check" : ""));
  if (node.type === "check") {
    chip.appendChild(statusIcon(CHECK_ICON[node.state] || "backlog", 14));
  } else {
    const glyph = el("span", "g" + (node.type === "conflict" ? " warn" : ""),
                     node.type === "conflict" ? "\\u25B2" : "\\u25C6");
    chip.appendChild(glyph);
  }
  const body = el("div", "chip-body");
  body.appendChild(el("p", null, node.label));
  // A check due next week sits in next week's column, so it has to say which conversation
  // asked for it — the alignment cannot.
  if (node.type === "check" && node.from_call) {
    body.appendChild(el("div", "from", "from: " + node.from_call));
  }
  chip.appendChild(body);
  if (node.state === "early") {
    const up = el("span", "g up", "\\u2197");
    up.title = node.when_note || "resolved early";
    up.style.color = SPARK;
    chip.appendChild(up);
  }
  // Whose check it is, drawn the same way an issue row draws its assignee. Omitted rather
  // than guessed when no owner is on record.
  const owner = (node.facts || {}).assignee;
  if (node.type === "check" && owner) chip.appendChild(avatar(String(owner), 18));
  return chip;
}

function element(node) {
  if (node.el) return node.el;
  const box = el("div", "n " + node.lane);
  box.style.left = node.x + "px";
  box.style.top = node.y + "px";

  if (node.type === "meeting" || node.type === "intake") box.appendChild(callCard(node));
  else if (node.type === "issue") box.appendChild(issueRow(node));
  else if (node.row === "secondary") box.appendChild(el("div", "dot"));
  else box.appendChild(textChip(node));
  // A chip fits the column it is in. A narrow scheduled day gets a narrower pill rather than
  // one that overflows into the next day.
  const chip = box.firstChild;
  if (node.row !== "secondary" && node.slotWidth) {
    chip.style.width = node.slotWidth + "px";
  }

  box.addEventListener("mouseenter", (e) => {
    showTip(node, e);
    if (!selected) light(node);
  });
  box.addEventListener("mousemove", moveTip);
  box.addEventListener("mouseleave", () => { hideTip(); if (!selected) unlight(); });
  box.addEventListener("click", (e) => { e.stopPropagation(); select(node); });
  layer.appendChild(box);
  node.el = box;
  return box;
}

// --- threads ------------------------------------------------------------------------------------------

function halfOf(node) {
  if (node.type === "meeting" || node.type === "intake") return 48;
  if (node.type === "issue") return 15;
  if (node.row === "secondary") return 4;
  return 20;
}

function edgePath(edge) {
  const a = byId.get(edge.source), b = byId.get(edge.target);
  if (!a || !b) return "";
  if (a.day === b.day) {
    const down = b.y > a.y;
    const from = a.y + (down ? halfOf(a) : -halfOf(a));
    const to = b.y + (down ? -halfOf(b) : halfOf(b));
    const mid = (from + to) / 2;
    return `M${a.x},${from} C${a.x},${mid} ${b.x},${mid} ${b.x},${to}`;
  }
  const right = b.x > a.x;
  const from = a.x + (right ? 110 : -110);
  const to = b.x + (right ? -110 : 110);
  const bow = Math.abs(to - from) * TUNING.edgeBow;
  return `M${from},${a.y} C${from + (right ? bow : -bow)},${a.y} ` +
         `${to - (right ? bow : -bow)},${b.y} ${to},${b.y}`;
}

function columnsApart(a, b) {
  const at = columns.findIndex((c) => c.key === a.day);
  const bt = columns.findIndex((c) => c.key === b.day);
  return at < 0 || bt < 0 ? 0 : Math.abs(at - bt);
}

function drawEdges() {
  gEdges.textContent = "";
  for (const edge of edges) {
    const a = byId.get(edge.source), b = byId.get(edge.target);
    if (!a || !b) continue;
    // Only two relationships are allowed to cross columns; everything else drawn across the
    // diagram would turn it back into the hairball this replaced.
    if (a.day !== b.day && edge.rel !== "waits on" && edge.rel !== "led to") continue;
    // Structure is carried by alignment, so nothing is drawn at rest except a dependency
    // between checks — and not even that when it reaches across most of the week.
    const far = columnsApart(a, b) > TUNING.longEdgeColumns;
    const dep = edge.rel === "waits on" && !far;
    const path = svgEl("path");
    path.setAttribute("class", "edge" + (dep ? " dep" : ""));
    path.setAttribute("d", edgePath(edge));
    edge.el = path;
    edge.dep = dep;
    gEdges.appendChild(path);
  }
}

function light(node) {
  const near = new Set([node.id]);
  // Selecting a call lights everything that call produced — the strip is the story, so the
  // strip is what comes forward.
  if (node.type === "meeting" || node.type === "intake") {
    for (const other of nodes) if (other.group === node.id || other.origin === node.id) near.add(other.id);
  }
  for (const edge of edges) {
    if (edge.source === node.id) near.add(edge.target);
    if (edge.target === node.id) near.add(edge.source);
  }
  for (const id of node.waits_on || []) near.add(id);
  for (const other of nodes) {
    if (other.el) other.el.classList.toggle("dim", !near.has(other.id));
  }
  for (const edge of edges) {
    if (!edge.el) continue;
    const on = edge.source === node.id || edge.target === node.id;
    edge.el.classList.toggle("lit", on);
  }
}

function lightOwned(owned) {
  for (const other of nodes) {
    if (other.el) other.el.classList.toggle("dim", !owned.has(other.id));
  }
}

function unlight() {
  for (const node of nodes) if (node.el) node.el.classList.remove("dim");
  for (const edge of edges) if (edge.el) edge.el.classList.remove("lit");
}

// --- the tooltip ----------------------------------------------------------------------------------------

function showTip(node, event) {
  tooltip.textContent = "";
  tooltip.appendChild(el("div", "t-kind", node.type === "meeting" ? "call" : node.type));
  tooltip.appendChild(el("div", "t-label", node.label));
  const bits = [];
  const facts = node.facts || {};
  if (node.type === "check") {
    // A check the work overtook is met, but for a reason worth naming.
    if (node.moot) bits.push("done before the check was due");
    else if (node.due_human) bits.push(node.due_human);
    if (facts.assignee) bits.push(`${facts.assignee} owns ${facts.issue || "it"}`);
    if (facts.on_unmet) bits.push(facts.on_unmet);
  }
  if (!bits.length) {
    if (node.when_note) bits.push(node.when_note);
    else if (node.ts) bits.push(stamp(Date.parse(node.ts)));
    if (node.state) bits.push(node.state);
  }
  if (bits.length) tooltip.appendChild(el("div", "t-meta", bits.join(" \\u00B7 ")));
  tooltip.classList.add("on");
  moveTip(event);
}

function moveTip(event) {
  const pad = 14;
  tooltip.style.left =
    Math.min(event.clientX + pad, window.innerWidth - tooltip.offsetWidth - pad) + "px";
  tooltip.style.top =
    Math.min(event.clientY + pad, window.innerHeight - tooltip.offsetHeight - pad) + "px";
}

function hideTip() { tooltip.classList.remove("on"); }

// --- what the agent is doing right now ---------------------------------------------------------------------

function renderStatus(now) {
  if (!now) return;
  const doing = ((now.working || {}).items || [])[0];
  const next = ((now.up_next || {}).items || [])[0];
  statusDot.classList.toggle("busy", Boolean(doing));
  if (doing) {
    statusText.textContent = doing.phrase;
  } else if (next) {
    // Idle is only worth saying next to what it is waiting for.
    statusText.textContent =
      `idle \u2014 next: ${next.phrase}${next.due_human ? ", " + next.due_human : ""}`;
  } else {
    statusText.textContent = "idle \u2014 nothing scheduled";
  }
}

function renderRoster(roster) {
  avatars.textContent = "";
  for (const person of roster || []) {
    const pill = el("span", "who");
    pill.appendChild(avatar(person.name, 22));
    const owned = new Set(person.owns || []);
    pill.addEventListener("mouseenter", () => { if (!selected) lightOwned(owned); });
    pill.addEventListener("mouseleave", () => { if (!selected) unlight(); });
    pill.addEventListener("click", (e) => { e.stopPropagation(); openPerson(person, owned); });
    avatars.appendChild(pill);
  }
}

// --- the story panel, as an issue sidebar ---------------------------------------------------------------

function factValue(key, value) {
  if (Array.isArray(value)) return value.length ? value.join(", ") : "None";
  if (value === true) return "Yes";
  if (value === false) return "No";
  if (value === null || value === undefined || value === "") return "\\u2014";
  if (key === "produced" && typeof value === "object") {
    return `${value.decisions} decision(s), ${value.issues} issue(s)`;
  }
  return String(value);
}

function factRow(key, value) {
  const row = el("div", "p-fact");
  row.appendChild(el("b", null, FACT_LABELS[key] || key));
  const cell = el("span");
  if (key === "assignee" && value) cell.appendChild(avatar(String(value), 18));
  if (key === "priority") {
    const bars = priorityBars(value);
    if (bars) cell.appendChild(bars);
  }
  cell.appendChild(el("span", null, factValue(key, value)));
  row.appendChild(cell);
  return row;
}

function storyRow(entry) {
  const row = el("div", "p-line");
  const dot = el("span", "p-dot");
  dot.style.background = CATEGORY_TINT[entry.category] || MUTED;
  row.appendChild(dot);
  row.appendChild(el("span", null, entry.text));
  row.appendChild(el("em", null, entry.ts ? stamp(Date.parse(entry.ts)) : ""));
  return row;
}

function panelHead(icon, key, title) {
  if (playing) stopPlaying();
  panelBody.textContent = "";
  const line = el("div", "p-key");
  if (icon) line.appendChild(icon);
  line.appendChild(el("span", null, key));
  panelBody.appendChild(line);
  panelBody.appendChild(el("div", "p-title", title));
  panel.classList.add("open");
}

function storySection(story, emptyText) {
  panelBody.appendChild(el("div", "p-head", "Activity"));
  if (story && story.length) {
    const rail = el("div", "p-story");
    for (const entry of story) rail.appendChild(storyRow(entry));
    panelBody.appendChild(rail);
  } else {
    panelBody.appendChild(el("div", "p-none", emptyText));
  }
}

function linkRow(label, target) {
  // A property that names another thing on the page should take you to it.
  const row = el("div", "p-fact");
  row.appendChild(el("b", null, label));
  const link = el("button", "p-link", target.identifier || target.label);
  link.addEventListener("click", () => select(target));
  const cell = el("span");
  cell.appendChild(link);
  row.appendChild(cell);
  return row;
}

function producedRows(call) {
  const mine = nodes.filter((n) => (n.group === call.id || n.origin === call.id) && n.id !== call.id);
  const kinds = [["issue", "issues"], ["decision", "decisions"], ["check", "checks"]];
  const counts = kinds
    .map(([kind, plural]) => [mine.filter((n) => n.type === kind).length, plural])
    .filter(([count]) => count);
  if (!counts.length) return;
  panelBody.appendChild(el("div", "p-head", "Produced"));
  panelBody.appendChild(el("div", "p-sum",
    counts.map(([count, plural]) => `${count} ${plural}`).join(" \u00b7 ")));
  for (const item of mine) {
    if (item.type === "post" || item.type === "conflict") continue;
    const row = el("button", "p-row", item.identifier
      ? `${item.identifier} — ${item.label}` : item.label);
    row.addEventListener("click", () => select(item));
    panelBody.appendChild(row);
  }
}

function openPanel(node) {
  const icon = node.type === "issue" ? statusIcon("backlog", 14)
    : (node.type === "check" ? statusIcon(CHECK_ICON[node.state] || "backlog", 14) : null);
  panelHead(icon, node.identifier || (node.type === "meeting" ? "Call" : node.type), node.label);

  const facts = node.facts || {};
  const keys = Object.keys(facts).filter((k) => k !== "filed_from_call");
  const originId = node.origin || node.group;
  const origin = originId && originId !== "day" ? byId.get(originId) : null;
  if (keys.length || node.when_note || origin) {
    panelBody.appendChild(el("div", "p-head", "Properties"));
    if (node.when_note) panelBody.appendChild(factRow("when", node.when_note));
    if (origin && node.type !== "meeting") {
      panelBody.appendChild(linkRow("From", origin));
    }
    for (const key of keys) panelBody.appendChild(factRow(key, facts[key]));
    for (const id of node.waits_on || []) {
      const on = byId.get(id);
      if (on) panelBody.appendChild(linkRow("Depends on", on));
    }
  }
  if (node.type === "meeting" && node.stages) {
    panelBody.appendChild(el("div", "p-head", "Stages"));
    for (const segment of node.stages) {
      const row = el("div", "p-fact");
      row.appendChild(el("b", null, segment.name));
      row.appendChild(el("span", null, segment.note || segment.state));
      panelBody.appendChild(row);
    }
    producedRows(node);
  }
  storySection(node.story, (node.type === "check" || node.type === "issue")
    ? "Nothing yet — I'm watching." : "\\u2014");

  if (node.url) {
    const open = el("a", "p-open", "Open in Linear");
    open.href = node.url; open.target = "_blank"; open.rel = "noreferrer";
    panelBody.appendChild(open);
  }
}

function openStage(node, segment) {
  panelHead(null, "Stage", `${segment.name} — ${node.label}`);
  panelBody.appendChild(el("div", "p-head", "Properties"));
  panelBody.appendChild(factRow("status", segment.state));
  if (segment.note) panelBody.appendChild(factRow("produced", segment.note));
  const lines = (node.story || []).filter((e) => e.category === segment.name);
  storySection(lines.length ? lines : node.story, "\\u2014");
}

function openPerson(person, owned) {
  panelHead(avatar(person.name, 18), person.role || "Person", person.name);
  panelBody.appendChild(el("div", "p-head", "Properties"));
  panelBody.appendChild(factRow("role", person.role));
  panelBody.appendChild(factRow("owns", (person.owns || []).map(
    (id) => (byId.get(id) || {}).identifier || id.replace("issue:", ""))));
  panelBody.appendChild(factRow("pings_received", person.pings));
  const story = [];
  for (const id of person.owns || []) {
    for (const entry of (byId.get(id) || {}).story || []) story.push(entry);
  }
  storySection(story, "\\u2014");
  lightOwned(owned);
}

function select(node) {
  if (selected && selected.el) selected.el.classList.remove("sel");
  selected = node;
  if (node.el) node.el.classList.add("sel");
  light(node);
  hideTip();
  openPanel(node);
}

function deselect() {
  if (selected && selected.el) selected.el.classList.remove("sel");
  selected = null;
  panel.classList.remove("open");
  unlight();
}

// --- replay ------------------------------------------------------------------------------------------------

function visible(node) { return node.index < cursor; }
function atLive() { return nodes.length === 0 || cursor >= nodes.length; }

function reveal() {
  let shown = 0;
  for (const node of nodes) {
    const on = visible(node);
    const box = element(node);
    if (on) shown++;
    if (on === !box.classList.contains("hidden")) continue;
    box.classList.toggle("hidden", !on);
    if (on) { box.classList.remove("enter"); void box.offsetWidth; box.classList.add("enter"); }
  }
  for (const edge of edges) {
    if (!edge.el) continue;
    const a = byId.get(edge.source), b = byId.get(edge.target);
    edge.el.style.display = (a && b && visible(a) && visible(b)) ? "" : "none";
  }
  counter.textContent = `${shown} / ${nodes.length}`;
  const at = nodes[Math.max(0, cursor - 1)];
  clock.textContent = at ? stamp(Date.parse(at.ts)) : "\\u2014";
  modeChip.textContent = "";
  modeChip.appendChild(el("i"));
  modeChip.appendChild(el("span", null, atLive() ? "Live" : "Replay"));
  scrubber.value = String(cursor);
}

function stopPlaying() { playing = false; playButton.textContent = "\u25B6 Replay the story"; }

function frame(now) {
  if (playing && now - lastFrame > TUNING.stepMs) {
    lastFrame = now;
    cursor = Math.min(nodes.length, cursor + 1);
    const at = nodes[cursor - 1];
    if (at) centreOn(at.x);
    reveal();
    if (cursor >= nodes.length) stopPlaying();
  }
  requestAnimationFrame(frame);
}

// --- panning -------------------------------------------------------------------------------------------------

function setPan(value) {
  const limit = Math.min(0, stage.clientWidth - worldWidth);
  const next = Math.max(limit, Math.min(0, value));
  panX = next;
  world.style.transform = `translateX(${panX}px)`;
  stickHeaders();
  if (layoutPlan.mode) report();
}

function centreOn(x) { setPan(stage.clientWidth * TUNING.anchor - x); }

function openingView() {
  // Where the plan said to open. A fitting week starts at nought; a scrolling one starts on a
  // sub-column boundary chosen so today sits around the middle with its history to the left.
  setPan(-(layoutPlan.scrollLeft || 0));
  report();
}

function report() {
  // The numbers, on the document, so the layout can be checked with a DOM dump instead of an
  // eye. Anything that moves the view rewrites this.
  document.body.setAttribute("data-layout", [
    `mode=${layoutPlan.mode}`, `tight=${Math.round(layoutPlan.tightTotal || 0)}`, `vp=${Math.round(layoutPlan.viewportUsed || 0)}`,
    `total=${Math.round(layoutPlan.total || 0)}`,
    `viewport=${stage.clientWidth}`,
    `scrollLeft=${Math.round(-panX)}`,
    `lanes=${LANES.map((l) => Math.round(laneHeight[l] || 0)).join(",")}`,
  ].join(";"));
}

stage.addEventListener("wheel", (event) => {
  // A trackpad swipe arrives as deltaX, a mouse wheel with shift as deltaY. Either scrolls the
  // week; a plain vertical wheel is left alone.
  if (worldWidth <= stage.clientWidth) return;
  const amount = event.shiftKey ? (event.deltaY || event.deltaX) : event.deltaX;
  if (!amount) return;
  event.preventDefault();
  setPan(panX - amount);
}, { passive: false });

stage.addEventListener("mousedown", (event) => {
  dragging = true; moved = false; dragFrom = event.clientX; dragPan = panX;
  stage.classList.add("dragging");
});
window.addEventListener("mousemove", (event) => {
  if (!dragging) return;
  if (Math.abs(event.clientX - dragFrom) > 3) moved = true;
  setPan(dragPan + (event.clientX - dragFrom));
});
window.addEventListener("mouseup", () => {
  dragging = false; stage.classList.remove("dragging");
});

// --- building --------------------------------------------------------------------------------------------------

function build(data) {
  payload = data;
  nodes = (data.nodes || []).map((n, index) => ({ ...n, index, el: null }));
  for (const node of nodes) {
    node.future_node = Boolean((data.days || []).find((d) => d.key === node.day && d.future));
  }
  edges = (data.edges || []).map((e) => ({ ...e, el: null }));
  byId = new Map(nodes.map((n) => [n.id, n]));

  layout(data);
  drawFrame();
  for (const node of nodes) element(node);
  drawEdges();

  scrubber.max = String(nodes.length);
  cursor = nodes.length;
  reveal();
  renderStatus(data.now);
  renderRoster(data.roster);
  if (!nodes.length) document.getElementById("empty").style.display = "flex";
  openingView();
}

function fingerprint(data) {
  return `${(data.nodes || []).length}:${(data.edges || []).length}:${data.generated_at}`;
}

async function poll() {
  try {
    const fresh = await (await fetch("/console/graph.json")).json();
    if (!payload || fingerprint(fresh) === fingerprint(payload)) {
      if (payload) renderStatus(fresh.now);
      return;
    }
    if (!atLive() || playing) return;
    build(fresh);
  } catch (err) { /* a poll that fails changes nothing on screen */ }
}

playButton.addEventListener("click", () => {
  if (playing) { stopPlaying(); return; }
  if (atLive()) cursor = 0;
  playing = true;
  lastFrame = performance.now();
  playButton.textContent = "\u23F8 Pause";
  deselect();
  reveal();
});

scrubber.addEventListener("input", () => {
  stopPlaying();
  cursor = Number(scrubber.value);
  reveal();
});

nowButton.addEventListener("click", openingView);
nowButton.title = "Scroll to the present";
playButton.title = "Rebuilds the page from the first event, in order";
// Esc is the way out of anything on this page.
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") { deselect(); hideTip(); }
});
panelClose.addEventListener("click", deselect);
stage.addEventListener("click", () => { if (!moved) deselect(); });
window.addEventListener("resize", () => {
  // Whether the timeline fits is a question about the viewport, so the answer changes when
  // the window does.
  if (!payload) return;
  for (const node of nodes) node.el = null;
  layout(payload);
  drawFrame();
  for (const node of nodes) element(node);
  drawEdges();
  reveal();
  openingView();
});

fetch("/console/graph.json")
  .then((r) => r.json())
  .then((data) => {
    build(data);
    requestAnimationFrame(frame);
    window.setInterval(poll, 60000);
  })
  .catch(() => { document.getElementById("empty").style.display = "flex"; });
"""
