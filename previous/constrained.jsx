import { useState, useEffect, useRef } from "react";

// ═══════════════════════════════════════════════════════════════════
// DATA & CONSTRAINT DATABASE
// ═══════════════════════════════════════════════════════════════════

const ALPHABET = "abcdefghijklmnopqrstuvwxyz".split("");

// Approx % of common English words that START with each letter
// Source: analysis of ~100k word corpora
const START_FREQ = {
  a:11.6,b:4.5,c:9.7,d:5.5,e:5.0,f:4.8,g:3.5,h:4.9,
  i:4.4,j:0.8,k:1.1,l:4.2,m:5.5,n:2.8,o:3.8,p:9.0,
  q:0.4,r:4.9,s:12.4,t:8.5,u:2.4,v:2.1,w:4.0,x:0.1,y:0.5,z:0.3
};

// How many common English words exist per length
const WORDS_PER_LENGTH = {
  2: 80, 3: 900, 4: 3800, 5: 8000, 6: 15000, 7: 23000,
  8: 28000, 9: 24000, 10: 20000, 11: 15000, 12: 10000
};

const PRESETS = [
  {
    id: "free", name: "Free Write", icon: "∞", color: "#6b7280",
    desc: "No constraints. Just write.",
    constraints: [], feasibility: null
  },
  {
    id: "three_letter", name: "Three-Letter Words", icon: "③", color: "#fb923c",
    desc: "Every word must be exactly 3 letters.",
    constraints: [{ type: "wordLength", exact: 3 }],
    feasibility: "High — ~900 common 3-letter words available."
  },
  {
    id: "four_letter", name: "Four-Letter Words", icon: "④", color: "#f59e0b",
    desc: "Every word must be exactly 4 letters.",
    constraints: [{ type: "wordLength", exact: 4 }],
    feasibility: "High — ~3800 common 4-letter English words."
  },
  {
    id: "five_letter", name: "Five-Letter Words", icon: "⑤", color: "#eab308",
    desc: "Every word must be exactly 5 letters.",
    constraints: [{ type: "wordLength", exact: 5 }],
    feasibility: "High — the Wordle vocabulary. ~8000 words."
  },
  {
    id: "alpha_cycle", name: "Alphabet Cycle", icon: "⟳", color: "#10b981",
    desc: "Each new word must start with the next letter (A→B→C…→Z→A…). X turn is optional.",
    constraints: [{ type: "alphaCycle", skipX: false, xOptional: true, cycleMode: "advance" }],
    feasibility: "Medium — X is rare as a word-starter, so X turns are skippable."
  },
  {
    id: "sprint_500", name: "500-Word Sprint", icon: "⏱", color: "#3b82f6",
    desc: "Write 500 words in 10 minutes (~50 WPM).",
    constraints: [{ type: "wordGoal", target: 500 }, { type: "timeLimit", seconds: 600 }],
    feasibility: "High — 50 WPM is achievable for average typists."
  },
  {
    id: "sprint_1000", name: "1000-Word Sprint", icon: "⚡", color: "#6366f1",
    desc: "Write 1000 words in 15 minutes (~67 WPM).",
    constraints: [{ type: "wordGoal", target: 1000 }, { type: "timeLimit", seconds: 900 }],
    feasibility: "Medium — requires ~67 WPM. Fast but achievable."
  },
  {
    id: "pangram_100", name: "Pangram in 100", icon: "Ω", color: "#8b5cf6",
    desc: "Use every letter of the alphabet (anywhere in words) within 100 words.",
    constraints: [{ type: "pangram", withinWords: 100 }],
    feasibility: "High — letters need only appear anywhere in words, not as starters. Q, X, Z are easy to slip into words."
  },
  {
    id: "letter_budget", name: "Letter Budget", icon: "≤", color: "#ec4899",
    desc: "Each starting letter used max 30 times. (26×30 = 780 word ceiling; adjust goal accordingly.)",
    constraints: [{ type: "startLetterMax", max: 30 }],
    feasibility: "High — 30 uses per letter across 25 common letters = 750 words before X/Q/Z needed."
  },
  {
    id: "combined", name: "Gauntlet", icon: "⚔", color: "#ef4444",
    desc: "4-letter words only, alphabet cycle, 300 words in 15 minutes.",
    constraints: [
      { type: "wordLength", exact: 4 },
      { type: "alphaCycle", skipX: false, xOptional: true, cycleMode: "advance" },
      { type: "wordGoal", target: 300 },
      { type: "timeLimit", seconds: 900 }
    ],
    feasibility: "Hard — requires ~20 WPM average but within reach. Prepare a list of 4-letter words for every letter."
  }
];

// ═══════════════════════════════════════════════════════════════════
// CONSTRAINT ENGINE
// ═══════════════════════════════════════════════════════════════════

function cleanWord(w) {
  return w.replace(/[^a-zA-Z]/g, "").toLowerCase();
}

function getWords(text) {
  return text.trim().split(/\s+/).filter(w => w.length > 0);
}

function getAlphabet(skipX) {
  return skipX ? ALPHABET.filter(l => l !== "x") : ALPHABET;
}

function analyzeText(text, constraints, elapsed) {
  const rawWords = getWords(text);
  const words = rawWords.map(cleanWord).filter(w => w.length > 0);
  const wordCount = words.length;
  const minutes = elapsed / 60;
  const wpm = minutes > 0.1 ? Math.round(wordCount / minutes) : 0;

  const violations = [];
  const letterCounts = {};
  const usedLetters = new Set();

  // Build pangram window tracker
  const pangram = constraints.find(c => c.type === "pangram");
  const cycle = constraints.find(c => c.type === "alphaCycle");
  const wl = constraints.find(c => c.type === "wordLength");
  const slMax = constraints.find(c => c.type === "startLetterMax");

  const cycleAlpha = cycle ? getAlphabet(cycle.skipX) : [];

  words.forEach((word, i) => {
    const first = word[0];
    if (!first) return;

    // Count starting letters
    letterCounts[first] = (letterCounts[first] || 0) + 1;

    // Track all used letters
    word.split("").forEach(l => usedLetters.add(l));

    // Word length check
    if (wl) {
      if (wl.exact && word.length !== wl.exact) {
        violations.push({
          wordIndex: i, word: rawWords[i],
          message: `"${rawWords[i]}" is ${word.length} letters (need exactly ${wl.exact})`,
          type: "wordLength"
        });
      }
    }

    // Alphabet cycle check
    if (cycle) {
      const expected = cycleAlpha[i % cycleAlpha.length];
      const isXSlot = expected === "x";
      if (isXSlot && cycle.xOptional) {
        // X slot is optional — any letter accepted
      } else if (first !== expected) {
        violations.push({
          wordIndex: i, word: rawWords[i],
          message: `Word ${i+1}: expected '${expected.toUpperCase()}', got '${first.toUpperCase()}'`,
          type: "alphaCycle"
        });
      }
    }

    // Starting letter max
    if (slMax && letterCounts[first] > slMax.max) {
      violations.push({
        wordIndex: i, word: rawWords[i],
        message: `'${first.toUpperCase()}' used ${letterCounts[first]}× (max ${slMax.max})`,
        type: "startLetterMax"
      });
    }
  });

  // Pangram progress (within window)
  let pangProgress = null;
  if (pangram) {
    const windowWords = words.slice(0, pangram.withinWords);
    const windowUsed = new Set();
    windowWords.forEach(w => w.split("").forEach(l => windowUsed.add(l)));
    const windowMissing = ALPHABET.filter(l => !windowUsed.has(l));
    const allMissing = ALPHABET.filter(l => !usedLetters.has(l));
    pangProgress = { windowMissing, allMissing, target: pangram.withinWords };
  }

  // Goal progress
  const goalC = constraints.find(c => c.type === "wordGoal");
  const goalProgress = goalC ? { current: wordCount, target: goalC.target } : null;

  // Next expected letter in cycle
  let nextExpected = null;
  if (cycle) {
    const nextIdx = wordCount % cycleAlpha.length;
    nextExpected = cycleAlpha[nextIdx];
    if (nextExpected === "x" && cycle.xOptional) nextExpected = `x*`;
  }

  const totalChecked = violations.filter(v =>
    v.type === "wordLength" || v.type === "alphaCycle" || v.type === "startLetterMax"
  ).length;
  const compliance = wordCount > 0
    ? Math.max(0, Math.round(((wordCount - totalChecked) / wordCount) * 100))
    : 100;

  return { wordCount, wpm, violations, compliance, letterCounts, usedLetters, pangProgress, goalProgress, nextExpected };
}

// ─── Feasibility checker ─────────────────────────────────────────
function checkFeasibility(constraints) {
  const warnings = [];
  const wl = constraints.find(c => c.type === "wordLength");
  const goal = constraints.find(c => c.type === "wordGoal");
  const time = constraints.find(c => c.type === "timeLimit");
  const slMax = constraints.find(c => c.type === "startLetterMax");
  const cycle = constraints.find(c => c.type === "alphaCycle");

  if (wl?.exact) {
    const available = WORDS_PER_LENGTH[wl.exact] || 0;
    if (available === 0) warnings.push({ level: "error", msg: `No known English words of exactly ${wl.exact} letters.` });
    else if (available < 200) warnings.push({ level: "warn", msg: `Only ~${available} words of length ${wl.exact} — very limited vocabulary.` });
  }

  if (goal && slMax) {
    const maxPossible = slMax.max * 26;
    if (goal.target > maxPossible) warnings.push({
      level: "error",
      msg: `Impossible: ${goal.target} words at max ${slMax.max} per letter = ceiling of ${maxPossible} words.`
    });
  }

  if (goal && time) {
    const requiredWPM = Math.round(goal.target / (time.seconds / 60));
    if (requiredWPM > 120) warnings.push({ level: "error", msg: `Requires ${requiredWPM} WPM — near-impossible for most typists.` });
    else if (requiredWPM > 80) warnings.push({ level: "warn", msg: `Requires ${requiredWPM} WPM — fast typist territory.` });
  }

  if (cycle && !cycle.skipX && !cycle.xOptional) {
    warnings.push({ level: "warn", msg: "X is very rare as a word-starter (~0.1% of vocab). Consider making X optional." });
  }

  if (cycle && wl?.exact === 3) {
    warnings.push({ level: "warn", msg: "Alphabet cycle + 3-letter words: some letters have very few 3-letter options (esp. X, Q, Z)." });
  }

  return warnings;
}

// ═══════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════

export default function Constrained() {
  const [view, setView] = useState("editor");
  const [text, setText] = useState("");
  const [activePreset, setActivePreset] = useState(PRESETS[0]);
  const [customConstraints, setCustomConstraints] = useState(null);
  const [timer, setTimer] = useState({ running: false, elapsed: 0, target: null });
  const [sessionStarted, setSessionStarted] = useState(false);
  const [history, setHistory] = useState([]);
  const [analysis, setAnalysis] = useState({
    wordCount: 0, wpm: 0, violations: [], compliance: 100,
    letterCounts: {}, usedLetters: new Set(),
    pangProgress: null, goalProgress: null, nextExpected: null
  });
  const [builder, setBuilder] = useState({
    wordLengthOn: false, wordLengthExact: 4,
    alphaCycleOn: false, alphaCycleSkipX: false, alphaCycleXOptional: true,
    wordGoalOn: false, wordGoalTarget: 500,
    timeLimitOn: false, timeLimitMinutes: 10,
    startLetterMaxOn: false, startLetterMaxN: 30,
    pangramOn: false, pangramWithin: 100,
  });
  const [builderFeasibility, setBuilderFeasibility] = useState([]);

  const timerRef = useRef(null);
  const textRef = useRef(null);
  const timerDone = timer.target && timer.elapsed >= timer.target;

  const activeConstraints = customConstraints ?? activePreset.constraints;

  // Timer tick
  useEffect(() => {
    if (timer.running && !timerDone) {
      timerRef.current = setInterval(() => {
        setTimer(t => ({ ...t, elapsed: t.elapsed + 1 }));
      }, 1000);
    }
    return () => clearInterval(timerRef.current);
  }, [timer.running, timerDone]);

  // Analyze on text/constraints change
  useEffect(() => {
    setAnalysis(analyzeText(text, activeConstraints, timer.elapsed));
  }, [text, activeConstraints, timer.elapsed]);

  // Builder feasibility preview
  useEffect(() => {
    const c = buildConstraintsFromForm();
    setBuilderFeasibility(checkFeasibility(c));
  }, [builder]);

  function buildConstraintsFromForm() {
    const c = [];
    if (builder.wordLengthOn) c.push({ type: "wordLength", exact: builder.wordLengthExact });
    if (builder.alphaCycleOn) c.push({ type: "alphaCycle", skipX: builder.alphaCycleSkipX, xOptional: builder.alphaCycleXOptional, cycleMode: "advance" });
    if (builder.wordGoalOn) c.push({ type: "wordGoal", target: builder.wordGoalTarget });
    if (builder.timeLimitOn) c.push({ type: "timeLimit", seconds: builder.timeLimitMinutes * 60 });
    if (builder.startLetterMaxOn) c.push({ type: "startLetterMax", max: builder.startLetterMaxN });
    if (builder.pangramOn) c.push({ type: "pangram", withinWords: builder.pangramWithin });
    return c;
  }

  function startSession(preset, constraints) {
    setText("");
    setSessionStarted(false);
    setTimer({ running: false, elapsed: 0, target: null });
    if (preset) setActivePreset(preset);
    if (constraints !== undefined) setCustomConstraints(constraints);
    setView("editor");
    setTimeout(() => textRef.current?.focus(), 50);
  }

  function handleTextChange(e) {
    const val = e.target.value;
    if (timerDone) return;
    setText(val);
    if (!sessionStarted && val.length > 0) {
      setSessionStarted(true);
      const tl = activeConstraints.find(c => c.type === "timeLimit");
      setTimer({ running: true, elapsed: 0, target: tl ? tl.seconds : null });
    }
  }

  function endSession() {
    if (text.trim().length === 0) return;
    clearInterval(timerRef.current);
    setTimer(t => ({ ...t, running: false }));
    const session = {
      id: Date.now(),
      date: new Date().toLocaleString(),
      presetName: customConstraints ? "Custom" : activePreset.name,
      isCustom: !!customConstraints,
      constraints: [...activeConstraints],
      excerpt: text.slice(0, 200),
      wordCount: analysis.wordCount,
      wpm: analysis.wpm,
      compliance: analysis.compliance,
      violations: analysis.violations.length,
      duration: timer.elapsed,
    };
    setHistory(h => [session, ...h]);
    setView("history");
  }

  function exportTxt() {
    const lines = [
      "╔══════════════════════════════════════╗",
      "║       CONSTRAINED SESSION EXPORT     ║",
      "╚══════════════════════════════════════╝",
      "",
      `Date      : ${new Date().toLocaleString()}`,
      `Mode      : ${customConstraints ? "Custom" : activePreset.name}`,
      `Duration  : ${fmtTime(timer.elapsed)}`,
      `Words     : ${analysis.wordCount}`,
      `WPM       : ${analysis.wpm}`,
      `Compliance: ${analysis.compliance}%`,
      `Violations: ${analysis.violations.length}`,
      "",
      "Constraints:",
      ...activeConstraints.map(c => `  · ${JSON.stringify(c)}`),
      "",
      "── TEXT ──────────────────────────────",
      "",
      text
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `constrained-${Date.now()}.txt`; a.click();
    URL.revokeObjectURL(url);
  }

  function applyBuilderConstraints() {
    const c = buildConstraintsFromForm();
    setCustomConstraints(c);
    startSession(null, c);
  }

  function fmtTime(s) {
    const m = Math.floor(s / 60);
    return `${m}:${(s % 60).toString().padStart(2, "0")}`;
  }

  const feasWarnings = checkFeasibility(activeConstraints);
  const progressPct = analysis.goalProgress
    ? Math.min(100, (analysis.goalProgress.current / analysis.goalProgress.target) * 100)
    : null;
  const timerPct = timer.target
    ? Math.min(100, (timer.elapsed / timer.target) * 100)
    : null;

  // ─── RENDER ─────────────────────────────────────────────────────

  return (
    <div style={S.root}>
      {/* HEADER */}
      <header style={S.header}>
        <div>
          <div style={S.title}>CONSTRAINED</div>
          <div style={S.subtitle}>typing constraint engine</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          {/* Timer display */}
          {timer.elapsed > 0 && (
            <div style={{
              fontFamily: "monospace", fontSize: 22,
              color: timerDone ? "#ef4444" : timer.target ? "#f0a500" : "#6b7280",
              letterSpacing: "0.05em",
            }}>
              {timer.target && !timerDone
                ? fmtTime(timer.target - timer.elapsed)
                : fmtTime(timer.elapsed)}
            </div>
          )}
          <nav style={{ display: "flex", gap: 4 }}>
            {["editor", "history", "builder"].map(v => (
              <button key={v} onClick={() => setView(v)} style={{
                ...S.navBtn,
                background: view === v ? "#f0a500" : "transparent",
                color: view === v ? "#000" : "#666",
                borderColor: view === v ? "#f0a500" : "#2a2a2e",
              }}>
                {v === "editor" ? "✎ Editor" : v === "history" ? "◷ History" : "⊞ Builder"}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <div style={{ display: "flex", flex: 1, overflow: "hidden", minHeight: 0 }}>

        {/* ═══ EDITOR VIEW ═══════════════════════════════════════════ */}
        {view === "editor" && (
          <>
            {/* Sidebar */}
            <aside style={S.sidebar}>
              <div style={S.sideSection}>MODES</div>
              {PRESETS.map(p => (
                <button key={p.id}
                  onClick={() => startSession(p, null)}
                  style={{
                    ...S.presetBtn,
                    background: activePreset.id === p.id && !customConstraints ? "#13131a" : "transparent",
                    borderLeft: `2px solid ${activePreset.id === p.id && !customConstraints ? p.color : "transparent"}`,
                    color: activePreset.id === p.id && !customConstraints ? "#e2ddd5" : "#555",
                  }}>
                  <span style={{ color: p.color, marginRight: 6, fontSize: 12 }}>{p.icon}</span>
                  <span>{p.name}</span>
                </button>
              ))}
              {customConstraints && (
                <button style={{ ...S.presetBtn, background: "#13131a", borderLeft: "2px solid #f0a500", color: "#e2ddd5" }}>
                  <span style={{ color: "#f0a500", marginRight: 6, fontSize: 12 }}>✦</span>
                  <span>Custom</span>
                </button>
              )}

              {/* Live stats */}
              <div style={{ ...S.sideSection, marginTop: 20 }}>STATS</div>
              <StatRow label="Words" val={analysis.wordCount} />
              <StatRow label="WPM" val={timer.elapsed > 5 ? analysis.wpm : "—"} />
              <StatRow label="Compliance" val={`${analysis.compliance}%`}
                color={analysis.compliance < 80 ? "#ef4444" : analysis.compliance < 95 ? "#f59e0b" : "#10b981"} />
              <StatRow label="Violations" val={analysis.violations.length}
                color={analysis.violations.length > 0 ? "#ef4444" : "#555"} />
              <StatRow label="Time" val={fmtTime(timer.elapsed)}
                color={timerDone ? "#ef4444" : "#6b7280"} />

              {/* Progress bars */}
              {progressPct !== null && (
                <div style={{ marginTop: 12, padding: "0 16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={S.statLabel}>Word goal</span>
                    <span style={{ ...S.statVal, color: progressPct >= 100 ? "#10b981" : "#f0a500" }}>
                      {analysis.goalProgress.current}/{analysis.goalProgress.target}
                    </span>
                  </div>
                  <ProgressBar pct={progressPct} color="#f0a500" />
                </div>
              )}
              {timerPct !== null && (
                <div style={{ marginTop: 10, padding: "0 16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={S.statLabel}>Time</span>
                    <span style={{ ...S.statVal, color: timerDone ? "#ef4444" : "#6b7280" }}>
                      {timerDone ? "DONE" : fmtTime(timer.target - timer.elapsed) + " left"}
                    </span>
                  </div>
                  <ProgressBar pct={timerPct} color={timerDone ? "#ef4444" : "#3b82f6"} />
                </div>
              )}

              {/* Letter coverage (pangram) */}
              {analysis.pangProgress && (
                <div style={{ padding: "12px 16px", marginTop: 8 }}>
                  <div style={S.statLabel}>Missing letters</div>
                  <div style={{ fontFamily: "monospace", fontSize: 11, color: "#f59e0b", marginTop: 4, letterSpacing: "0.15em" }}>
                    {analysis.pangProgress.windowMissing.join("").toUpperCase() || "✓ DONE"}
                  </div>
                </div>
              )}
            </aside>

            {/* Editor main */}
            <main style={S.editorMain}>
              {/* Constraint context bar */}
              <div style={S.contextBar}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ width: 7, height: 7, borderRadius: "50%", background: (customConstraints ? "#f0a500" : activePreset.color), flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: "#888", fontStyle: "italic" }}>
                    {customConstraints ? "Custom constraints" : activePreset.desc}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  {analysis.nextExpected && (
                    <div style={{ fontSize: 12, color: "#666" }}>
                      Next starts with:{" "}
                      <span style={{ color: "#f0a500", fontFamily: "monospace", fontWeight: 700, fontSize: 14 }}>
                        {analysis.nextExpected.replace("*", "").toUpperCase()}
                        {analysis.nextExpected.includes("*") && (
                          <span style={{ color: "#555", fontSize: 10, fontWeight: 400 }}> (optional)</span>
                        )}
                      </span>
                    </div>
                  )}
                  <div style={{ display: "flex", gap: 6 }}>
                    <Btn onClick={() => startSession(activePreset, customConstraints)} style={{ borderColor: "#333", color: "#666" }}>↺ Reset</Btn>
                    <Btn onClick={endSession} style={{ borderColor: "#10b981", color: "#10b981" }}>◼ Save</Btn>
                    <Btn onClick={exportTxt} style={{ borderColor: "#3b82f6", color: "#3b82f6" }}>↓ Export</Btn>
                  </div>
                </div>
              </div>

              {/* Feasibility warnings */}
              {feasWarnings.map((w, i) => (
                <div key={i} style={{
                  padding: "7px 24px",
                  background: w.level === "error" ? "#1a0808" : "#18140a",
                  borderBottom: "1px solid " + (w.level === "error" ? "#3b1010" : "#3a2a10"),
                  fontSize: 11, color: w.level === "error" ? "#ef4444" : "#f59e0b",
                  display: "flex", gap: 8, alignItems: "center",
                }}>
                  <span>{w.level === "error" ? "⚠ IMPOSSIBLE:" : "⚡"}</span>
                  <span>{w.msg}</span>
                </div>
              ))}

              {/* Timer done banner */}
              {timerDone && (
                <div style={{ padding: "12px 24px", background: "#1a0808", borderBottom: "1px solid #3b1010", textAlign: "center" }}>
                  <span style={{ color: "#ef4444", fontSize: 13, letterSpacing: "0.1em" }}>
                    ⏱ TIME'S UP — {analysis.wordCount} words · {analysis.wpm} WPM · {analysis.compliance}% compliant
                  </span>
                  <Btn onClick={endSession} style={{ borderColor: "#ef4444", color: "#ef4444", marginLeft: 16 }}>Save Session</Btn>
                </div>
              )}

              {/* Textarea */}
              <textarea
                ref={textRef}
                value={text}
                onChange={handleTextChange}
                disabled={timerDone}
                placeholder={`${activePreset.name}\n\n${activePreset.desc}\n\n—\n\nBegin typing to start...`}
                style={{
                  flex: 1,
                  background: "transparent",
                  border: "none",
                  outline: "none",
                  resize: "none",
                  padding: "36px 56px",
                  fontSize: 17,
                  lineHeight: 1.85,
                  fontFamily: "'Courier New', 'Courier', monospace",
                  color: timerDone ? "#444" : "#ddd9d0",
                  caretColor: "#f0a500",
                  letterSpacing: "0.01em",
                }}
              />

              {/* Violations panel */}
              {analysis.violations.length > 0 && (
                <div style={S.violationsPanel}>
                  <div style={S.sideSection}>VIOLATIONS — last 6</div>
                  <div style={{ padding: "0 16px 10px" }}>
                    {analysis.violations.slice(-6).map((v, i) => (
                      <div key={i} style={{ fontSize: 11, color: "#ef4444", fontFamily: "monospace", marginBottom: 3 }}>
                        ✗ {v.message}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </main>
          </>
        )}

        {/* ═══ HISTORY VIEW ══════════════════════════════════════════ */}
        {view === "history" && (
          <main style={S.fullPane}>
            <div style={{ maxWidth: 720, margin: "0 auto", width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
                <div style={{ fontSize: 12, letterSpacing: "0.15em", color: "#555" }}>SESSION HISTORY</div>
                <Btn onClick={() => startSession(activePreset, customConstraints)} style={{ borderColor: "#f0a500", color: "#f0a500" }}>
                  + New Session
                </Btn>
              </div>
              {history.length === 0 ? (
                <div style={{ color: "#333", textAlign: "center", padding: "80px 0", fontSize: 14, fontStyle: "italic" }}>
                  No sessions saved yet.
                </div>
              ) : history.map(s => (
                <div key={s.id} style={S.historyCard}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <span style={{ fontSize: 13, color: "#e2ddd5" }}>{s.presetName}</span>
                        {s.isCustom && <span style={{ fontSize: 9, color: "#f0a500", border: "1px solid #f0a500", borderRadius: 2, padding: "1px 5px", letterSpacing: "0.1em" }}>CUSTOM</span>}
                      </div>
                      <div style={{ fontSize: 11, color: "#444" }}>{s.date} · {fmtTime(s.duration)}</div>
                      <div style={{ marginTop: 8, fontSize: 11, color: "#383838", fontFamily: "monospace", lineHeight: 1.5 }}>
                        {s.excerpt.slice(0, 140)}{s.excerpt.length > 140 ? "…" : ""}
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 16, flexShrink: 0, textAlign: "right" }}>
                      <Metric n={s.wordCount} label="words" color="#f0a500" />
                      <Metric n={s.wpm} label="wpm" color="#6b9fff" />
                      <Metric n={`${s.compliance}%`} label="comply" color={s.compliance < 80 ? "#ef4444" : s.compliance < 95 ? "#f59e0b" : "#10b981"} />
                    </div>
                  </div>
                  {/* Suggestion based on past performance */}
                  {s.compliance < 90 && (
                    <div style={{ marginTop: 10, borderTop: "1px solid #1a1a1e", paddingTop: 8, fontSize: 11, color: "#555", fontStyle: "italic" }}>
                      ↳ Compliance was below 90%. Try the same mode again, or switch to a simpler preset.
                    </div>
                  )}
                  {s.compliance >= 98 && s.wpm > 0 && (
                    <div style={{ marginTop: 10, borderTop: "1px solid #1a1a1e", paddingTop: 8, fontSize: 11, color: "#10b981", fontStyle: "italic" }}>
                      ↳ Near-perfect. Consider combining this constraint with a time limit or word goal.
                    </div>
                  )}
                </div>
              ))}
            </div>
          </main>
        )}

        {/* ═══ BUILDER VIEW ══════════════════════════════════════════ */}
        {view === "builder" && (
          <main style={S.fullPane}>
            <div style={{ maxWidth: 620, margin: "0 auto", width: "100%" }}>
              <div style={{ fontSize: 12, letterSpacing: "0.15em", color: "#555", marginBottom: 24 }}>CONSTRAINT BUILDER</div>

              <BuildRow label="Exact Word Length" desc="Every word must be exactly N letters long."
                on={builder.wordLengthOn} onToggle={v => setBuilder(b => ({ ...b, wordLengthOn: v }))}>
                <Label>Letters:
                  <NumInput val={builder.wordLengthExact} min={2} max={15}
                    onChange={v => setBuilder(b => ({ ...b, wordLengthExact: v }))} />
                </Label>
                {WORDS_PER_LENGTH[builder.wordLengthExact] && (
                  <span style={{ fontSize: 10, color: "#555" }}>
                    ~{(WORDS_PER_LENGTH[builder.wordLengthExact] || 0).toLocaleString()} words available
                  </span>
                )}
              </BuildRow>

              <BuildRow label="Alphabet Cycle" desc="Each word must start with the next letter (A→B→C…→Z→A…)."
                on={builder.alphaCycleOn} onToggle={v => setBuilder(b => ({ ...b, alphaCycleOn: v }))}>
                <label style={S.chk}>
                  <input type="checkbox" checked={builder.alphaCycleSkipX}
                    onChange={e => setBuilder(b => ({ ...b, alphaCycleSkipX: e.target.checked }))} />
                  &nbsp;Skip X entirely (25-letter cycle)
                </label>
                {!builder.alphaCycleSkipX && (
                  <label style={S.chk}>
                    <input type="checkbox" checked={builder.alphaCycleXOptional}
                      onChange={e => setBuilder(b => ({ ...b, alphaCycleXOptional: e.target.checked }))} />
                    &nbsp;X turn is optional (any letter accepted)
                  </label>
                )}
              </BuildRow>

              <BuildRow label="Word Goal" desc="Session target: write N words."
                on={builder.wordGoalOn} onToggle={v => setBuilder(b => ({ ...b, wordGoalOn: v }))}>
                <Label>Target:
                  <NumInput val={builder.wordGoalTarget} min={10} max={100000}
                    onChange={v => setBuilder(b => ({ ...b, wordGoalTarget: v }))} wide />
                </Label>
              </BuildRow>

              <BuildRow label="Time Limit" desc="Countdown timer. Typing begins when you type the first character."
                on={builder.timeLimitOn} onToggle={v => setBuilder(b => ({ ...b, timeLimitOn: v }))}>
                <Label>Minutes:
                  <NumInput val={builder.timeLimitMinutes} min={1} max={180}
                    onChange={v => setBuilder(b => ({ ...b, timeLimitMinutes: v }))} />
                </Label>
              </BuildRow>

              <BuildRow label="Starting Letter Max" desc="Each letter of the alphabet can only start N words total."
                on={builder.startLetterMaxOn} onToggle={v => setBuilder(b => ({ ...b, startLetterMaxOn: v }))}>
                <Label>Max per letter:
                  <NumInput val={builder.startLetterMaxN} min={1} max={10000}
                    onChange={v => setBuilder(b => ({ ...b, startLetterMaxN: v }))} />
                </Label>
                {builder.wordGoalOn && (
                  <span style={{ fontSize: 10, color: "#555" }}>
                    Ceiling: {builder.startLetterMaxN * 26} words
                  </span>
                )}
              </BuildRow>

              <BuildRow label="Pangram Challenge" desc="Use every letter of the alphabet (anywhere in words) within N words."
                on={builder.pangramOn} onToggle={v => setBuilder(b => ({ ...b, pangramOn: v }))}>
                <Label>Within N words:
                  <NumInput val={builder.pangramWithin} min={26} max={1000}
                    onChange={v => setBuilder(b => ({ ...b, pangramWithin: v }))} />
                </Label>
              </BuildRow>

              {/* Feasibility */}
              {builderFeasibility.length > 0 ? (
                <div style={{ margin: "16px 0", padding: "12px 16px", background: "#0e0e11", border: "1px solid #2a1a1a", borderRadius: 3 }}>
                  <div style={{ fontSize: 10, color: "#555", letterSpacing: "0.1em", marginBottom: 8 }}>FEASIBILITY CHECK</div>
                  {builderFeasibility.map((w, i) => (
                    <div key={i} style={{ fontSize: 12, color: w.level === "error" ? "#ef4444" : "#f59e0b", marginBottom: 4 }}>
                      {w.level === "error" ? "⚠ " : "⚡ "}{w.msg}
                    </div>
                  ))}
                </div>
              ) : buildConstraintsFromForm().length > 0 && (
                <div style={{ margin: "16px 0", padding: "10px 16px", background: "#0a120a", border: "1px solid #1a2e1a", borderRadius: 3 }}>
                  <div style={{ fontSize: 12, color: "#10b981" }}>✓ Constraints look feasible.</div>
                </div>
              )}

              <button onClick={applyBuilderConstraints} style={{
                marginTop: 8, background: "#f0a500", color: "#000",
                border: "none", borderRadius: 3, padding: "11px 28px",
                fontSize: 12, letterSpacing: "0.12em", cursor: "pointer",
                fontFamily: "monospace", fontWeight: 700,
              }}>
                APPLY & START SESSION
              </button>

              {/* Letter frequency reference */}
              <div style={{ marginTop: 40, padding: "20px 0", borderTop: "1px solid #1a1a1e" }}>
                <div style={{ fontSize: 10, color: "#444", letterSpacing: "0.12em", marginBottom: 14 }}>LETTER FREQUENCY REFERENCE — % of words starting with each letter</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {ALPHABET.map(l => (
                    <div key={l} style={{ textAlign: "center", width: 38 }}>
                      <div style={{
                        height: Math.max(4, (START_FREQ[l] / 12.4) * 32),
                        background: l === "x" || l === "q" || l === "z" ? "#3a1a1a" : "#1e2a1e",
                        borderTop: `2px solid ${l === "x" || l === "q" || l === "z" ? "#ef4444" : "#10b981"}`,
                        marginBottom: 3,
                      }} />
                      <div style={{ fontSize: 9, color: "#444", fontFamily: "monospace" }}>{l.toUpperCase()}</div>
                      <div style={{ fontSize: 8, color: "#333", fontFamily: "monospace" }}>{START_FREQ[l]}%</div>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: 8, fontSize: 10, color: "#333", fontStyle: "italic" }}>
                  Red bars (X, Q, Z) are rare word-starters — plan constraints accordingly.
                </div>
              </div>
            </div>
          </main>
        )}

      </div>
    </div>
  );
}

// ─── SUB-COMPONENTS ──────────────────────────────────────────────

function StatRow({ label, val, color }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 16px" }}>
      <span style={S.statLabel}>{label}</span>
      <span style={{ ...S.statVal, color: color || "#9a9590" }}>{val}</span>
    </div>
  );
}

function ProgressBar({ pct, color }) {
  return (
    <div style={{ background: "#1a1a1e", borderRadius: 2, height: 3 }}>
      <div style={{ background: color, height: 3, borderRadius: 2, width: `${pct}%`, transition: "width 0.5s ease" }} />
    </div>
  );
}

function Btn({ onClick, children, style = {} }) {
  return (
    <button onClick={onClick} style={{
      background: "transparent", border: "1px solid #333", borderRadius: 3,
      padding: "4px 12px", fontSize: 10, letterSpacing: "0.1em",
      cursor: "pointer", fontFamily: "monospace", color: "#666", ...style
    }}>
      {children}
    </button>
  );
}

function Metric({ n, label, color }) {
  return (
    <div>
      <div style={{ fontSize: 22, color, fontFamily: "monospace", textAlign: "right" }}>{n}</div>
      <div style={{ fontSize: 9, color: "#444", letterSpacing: "0.08em" }}>{label}</div>
    </div>
  );
}

function BuildRow({ label, desc, on, onToggle, children }) {
  return (
    <div style={{
      background: "#0c0c10", border: `1px solid ${on ? "#252516" : "#161618"}`,
      borderRadius: 3, padding: "13px 16px", marginBottom: 10
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: 13, color: on ? "#e2ddd5" : "#555", marginBottom: 2 }}>{label}</div>
          <div style={{ fontSize: 11, color: "#3a3a3a" }}>{desc}</div>
        </div>
        <button onClick={() => onToggle(!on)} style={{
          background: on ? "#f0a500" : "#13131a",
          color: on ? "#000" : "#444",
          border: `1px solid ${on ? "#f0a500" : "#222"}`,
          borderRadius: 2, padding: "3px 10px",
          fontSize: 10, letterSpacing: "0.1em",
          cursor: "pointer", fontFamily: "monospace",
          flexShrink: 0, marginLeft: 12,
        }}>
          {on ? "ON" : "OFF"}
        </button>
      </div>
      {on && <div style={{ marginTop: 12, display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>{children}</div>}
    </div>
  );
}

function Label({ children }) {
  return <label style={{ fontSize: 12, color: "#666", display: "flex", alignItems: "center", gap: 6 }}>{children}</label>;
}

function NumInput({ val, min, max, onChange, wide }) {
  return (
    <input type="number" value={val} min={min} max={max}
      onChange={e => onChange(+e.target.value)}
      style={{
        background: "#0a0a0d", border: "1px solid #222",
        color: "#e2ddd5", borderRadius: 3, padding: "3px 8px",
        fontSize: 13, fontFamily: "monospace", width: wide ? 80 : 60,
        marginLeft: 4, outline: "none",
      }} />
  );
}

// ─── STYLES ──────────────────────────────────────────────────────

const S = {
  root: {
    fontFamily: "'Georgia', 'Times New Roman', serif",
    background: "#0d0d11",
    color: "#e2ddd5",
    height: "100vh",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  header: {
    borderBottom: "1px solid #18181e",
    padding: "14px 24px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    background: "#090910",
    flexShrink: 0,
  },
  title: { fontSize: 16, letterSpacing: "0.2em", fontFamily: "monospace", color: "#f0a500" },
  subtitle: { fontSize: 9, color: "#3a3a3a", letterSpacing: "0.15em", marginTop: 2 },
  navBtn: {
    border: "1px solid", borderRadius: 3, padding: "5px 14px",
    fontSize: 10, letterSpacing: "0.1em", cursor: "pointer",
    fontFamily: "monospace",
  },
  sidebar: {
    width: 210, borderRight: "1px solid #14141a", overflowY: "auto",
    background: "#090910", flexShrink: 0, paddingTop: 8,
  },
  sideSection: {
    fontSize: 9, color: "#3a3a3a", letterSpacing: "0.12em",
    padding: "0 16px", marginBottom: 6, marginTop: 4,
  },
  presetBtn: {
    display: "flex", alignItems: "center", width: "100%",
    border: "none", borderLeft: "2px solid transparent",
    padding: "8px 14px", cursor: "pointer", fontSize: 12,
    fontFamily: "'Georgia', serif", textAlign: "left",
  },
  editorMain: {
    flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0,
  },
  contextBar: {
    background: "#0a0a0e", borderBottom: "1px solid #14141a",
    padding: "8px 20px", display: "flex", alignItems: "center",
    justifyContent: "space-between", flexShrink: 0, flexWrap: "wrap", gap: 8,
  },
  violationsPanel: {
    borderTop: "1px solid #16161a", background: "#0a0a0e", flexShrink: 0,
    paddingTop: 8,
  },
  fullPane: {
    flex: 1, padding: "28px 32px", overflowY: "auto",
  },
  historyCard: {
    background: "#0c0c10", border: "1px solid #18181e",
    borderRadius: 3, padding: "16px 18px", marginBottom: 10,
  },
  statLabel: { fontSize: 10, color: "#444", letterSpacing: "0.06em" },
  statVal: { fontSize: 13, fontFamily: "monospace" },
  chk: { fontSize: 12, color: "#666", display: "flex", alignItems: "center", cursor: "pointer" },
};
