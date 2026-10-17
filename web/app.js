const DRAFT_KEY = "puzzle-draft";
const IGNORE_KEY = "puzzle-ignore-baseline";
const DEFAULT_CODE = "a = [1, 2, 3]\na.append(4)\n";

const scoreEl = document.getElementById("score");
const outputEl = document.getElementById("output");
const runButton = document.getElementById("run");
const ignoreBaseline = document.getElementById("ignore-baseline");

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
let runHit = new Set();
let lineClass = [];
let lastStats = null;
let running = false;

ignoreBaseline.checked = localStorage.getItem(IGNORE_KEY) === "1";

editor.setValue(localStorage.getItem(DRAFT_KEY) ?? DEFAULT_CODE);
editor.on("change", () => localStorage.setItem(DRAFT_KEY, editor.getValue()));

function showOutput(text) {
  outputEl.textContent = text;
}

function formatScore(stats) {
  if (!stats) return "";
  const noun = ignoreBaseline.checked ? "lines" : "interesting";
  return `${stats.covered} / ${stats.interesting} ${noun} (${stats.coverage.toFixed(1)}%)`;
}

function countsBaseline(line) {
  return !ignoreBaseline.checked && baseline.has(line);
}

function computeStats() {
  let interesting = 0;
  let covered = 0;
  for (const line of targets) {
    if (countsBaseline(line)) continue;
    interesting++;
    if (runHit.has(line)) covered++;
  }
  const coverage = interesting ? (100 * covered) / interesting : 0;
  return { covered, interesting, coverage };
}

function uncoveredLines() {
  const lines = [];
  for (const line of targets) {
    if (!countsBaseline(line) && !runHit.has(line)) lines.push(line);
  }
  return lines;
}

function paint() {
  const count = view.lineCount();
  view.operation(() => {
    for (let i = 0; i < count; i++) {
      const lineNo = i + 1;
      let cls = "line-out";
      if (targetLookup.has(lineNo) && !countsBaseline(lineNo)) {
        cls = runHit.has(lineNo) ? "line-hit" : "line-miss";
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

function applyCoverage(hitLines) {
  runHit = new Set(hitLines);
  lastStats = computeStats();
  scoreEl.textContent = formatScore(lastStats);
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
  applyCoverage([]);
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
    if (response.ok) applyCoverage(data.hit ?? data.covered ?? []);
    else scoreEl.textContent = lastStats ? formatScore(lastStats) : "run failed";
  } catch (err) {
    showOutput(String(err));
    scoreEl.textContent = "run failed";
  } finally {
    running = false;
    runButton.disabled = false;
  }
}

ignoreBaseline.addEventListener("change", () => {
  localStorage.setItem(IGNORE_KEY, ignoreBaseline.checked ? "1" : "0");
  if (!targets.length) return;
  lastStats = computeStats();
  scoreEl.textContent = formatScore(lastStats);
  paint();
});

document.getElementById("run").addEventListener("click", run);
document.getElementById("prev").addEventListener("click", () => jump(-1));
document.getElementById("next").addEventListener("click", () => jump(1));

loadPuzzle().catch((err) => {
  scoreEl.textContent = "unavailable";
  showOutput(String(err));
});
