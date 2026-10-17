const DRAFT_KEY = "puzzle-draft";
const DEFAULT_CODE = "a = [1, 2, 3]\na.append(4)\n";

const scoreEl = document.getElementById("score");
const outputEl = document.getElementById("output");
const runButton = document.getElementById("run");

const editor = CodeMirror.fromTextArea(document.getElementById("editor"), {
  mode: "python",
  theme: "nord",
  lineNumbers: true,
  indentUnit: 4,
  extraKeys: {
    "Ctrl-Enter": () => run(),
    "Cmd-Enter": () => run(),
  },
});

const view = CodeMirror.fromTextArea(document.getElementById("source"), {
  mode: "text/x-csrc",
  theme: "nord",
  lineNumbers: true,
  readOnly: true,
});

let targets = [];
let targetLookup = new Set();
let baseline = new Set();
let covered = new Set();
let lineClass = [];
let lastStats = null;
let running = false;

editor.setValue(localStorage.getItem(DRAFT_KEY) ?? DEFAULT_CODE);
editor.on("change", () => localStorage.setItem(DRAFT_KEY, editor.getValue()));

function showOutput(text) {
  outputEl.textContent = text;
}

function formatScore(stats) {
  if (!stats) return "";
  return `${stats.covered} / ${stats.interesting} interesting (${stats.coverage.toFixed(1)}%)`;
}

function uncoveredLines() {
  const lines = [];
  for (const line of targets) {
    if (!baseline.has(line) && !covered.has(line)) lines.push(line);
  }
  return lines;
}

function paint() {
  const count = view.lineCount();
  view.operation(() => {
    for (let i = 0; i < count; i++) {
      const lineNo = i + 1;
      let cls = "line-out";
      if (targetLookup.has(lineNo) && !baseline.has(lineNo)) {
        cls = covered.has(lineNo) ? "line-hit" : "line-miss";
      }
      if (lineClass[i] === cls) continue;
      for (const where of ["background", "text", "gutter"]) {
        if (lineClass[i]) view.removeLineClass(i, where, lineClass[i]);
        view.addLineClass(i, where, cls);
      }
      lineClass[i] = cls;
    }
  });
}

function applyCoverage(nextCovered, stats) {
  covered = new Set(nextCovered);
  lastStats = stats;
  scoreEl.textContent = formatScore(stats);
  paint();
}

function jump(direction) {
  const lines = uncoveredLines();
  if (!lines.length) return;
  const current = view.getCursor().line + 1;
  let next = null;
  if (direction > 0) {
    next = lines.find((line) => line > current) ?? lines[0];
  } else {
    for (let i = lines.length - 1; i >= 0; i--) {
      if (lines[i] < current) {
        next = lines[i];
        break;
      }
    }
    if (next == null) next = lines[lines.length - 1];
  }
  view.setCursor({ line: next - 1, ch: 0 });
  view.focus();
}

async function loadPuzzle() {
  const response = await fetch("/api/puzzle");
  const data = await response.json();
  if (!response.ok) {
    scoreEl.textContent = "unavailable";
    showOutput(data.error || "failed to load puzzle");
    return;
  }
  view.setValue(data.source.replace(/\n$/, ""));
  targets = data.targets;
  targetLookup = new Set(targets);
  baseline = new Set(data.baseline_hit);
  lineClass = [];
  applyCoverage(data.covered, data.stats);
  showOutput("Grey lines are not gcov code, or already hit by baselines/. Red lines are the puzzle.");
}

async function run() {
  if (running) return;
  running = true;
  runButton.disabled = true;
  scoreEl.textContent = "running…";
  showOutput("running…");
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: editor.getValue() }),
    });
    const data = await response.json();
    const parts = [];
    if (data.error) parts.push(data.error);
    if (data.stdout) parts.push(data.stdout.replace(/\s+$/, ""));
    if (data.stderr) parts.push(data.stderr.replace(/\s+$/, ""));
    showOutput(parts.filter(Boolean).join("\n\n") || "(no output)");
    if (response.ok) applyCoverage(data.covered, data.stats);
    else scoreEl.textContent = lastStats ? formatScore(lastStats) : "run failed";
  } catch (err) {
    showOutput(String(err));
    scoreEl.textContent = "run failed";
  } finally {
    running = false;
    runButton.disabled = false;
  }
}

document.getElementById("run").addEventListener("click", run);
document.getElementById("prev").addEventListener("click", () => jump(-1));
document.getElementById("next").addEventListener("click", () => jump(1));

loadPuzzle().catch((err) => {
  scoreEl.textContent = "unavailable";
  showOutput(String(err));
});
