# TETHER — GAME MODE SPEC
### Feature addition to Tether v0.3.2
### For implementation via Claude Code

---

## OVERVIEW

Add a Game Mode to Tether, toggled via a switch at the top of the Editor view. Game Mode transforms the sidebar into a game panel while keeping the editor unchanged. Two sub-modes: **Challenge Mode** (survive a structured challenge) and **Score Attack** (chase a high score). Both share a unified scoring engine.

The existing Write mode is untouched. Game Mode is purely additive.

---

## UI STRUCTURE

### Top-level toggle
- Write / Game switch at the top of the Editor view (tkinter toggle or pair of radio buttons)
- Switching to Game replaces the sidebar content with the game panel
- Switching back to Write restores the normal stats/violation/language panels

### Game panel (sidebar in Game mode)
- Sub-toggle: **Challenge** | **Score Attack**
- Difficulty selector: **Easy** | **Medium** | **Hard** (affects violation penalties)
- Constraint/preset picker (see below)
- Score display: large, prominent, updates in real time
- Streak counter: current streak + multiplier indicator (e.g., "×2.0 — 27 words")
- Violation penalty indicator: shows current difficulty's penalty behavior
- Timer (if timed session)
- Word count / progress bar (if word-goal session)

### Visual distinction
- Game mode should feel visually distinct but not jarring — consider a subtle color accent change in the sidebar (e.g., slightly different background), a more prominent score counter, and a streak indicator that pulses or changes color as the multiplier increases
- Streak milestones (hitting ×2, ×3, ×4) should have brief visual feedback — a flash, color change, or label update
- Star rating display on challenge completion
- Keep it tkinter-native — no external GUI deps

---

## SCORING ENGINE (shared by both modes)

### Formula
```
word_score = base_points × difficulty_multiplier × streak_multiplier × rarity_bonus
```

### Base points
- Equal to word length in characters
- "the" = 3 pts, "extraordinary" = 13 pts
- Rewards ambitious vocabulary

### Difficulty multiplier
- Derived from active constraints — more/harder constraints = higher multiplier
- Suggested starting values (tune during testing):
  - Single simple constraint (e.g., dictCheck): ×1.0
  - Single moderate constraint (e.g., wordLength 4): ×1.5
  - Single hard constraint (e.g., alphaCycle): ×2.0
  - Multiple constraints: multiply individual values (cap at ×5.0)
  - Gauntlet preset: ×4.0–5.0
- These values will need balancing — start here and adjust

### Streak multiplier
- Consecutive compliant words build the multiplier
- Thresholds:
  - 0–9 words: ×1.0
  - 10–24 words: ×1.5
  - 25–49 words: ×2.0
  - 50–99 words: ×3.0
  - 100+ words: ×4.0
- Violations reset streak to 0 and multiplier to ×1.0

### Rarity bonus
- SCOWL frequency tier file: `word_rarity.json` in app directory
- Three tiers:
  - Common (SCOWL levels 10–35): ×1.0
  - Uncommon (SCOWL levels 40–60): ×1.25
  - Rare (SCOWL levels 65–80): ×1.5
- Implementation: generate `word_rarity.json` from SCOWL source lists at build time, or ship a pre-built file. Structure: `{"word": tier}` where tier is 1, 1.25, or 1.5. Only uncommon and rare words need entries — absence = common (×1.0). This keeps the file small.

### Violation penalties (difficulty-dependent)
- **Easy:** streak reset only, no point deduction
- **Medium:** streak reset + flat deduction (e.g., −5 points per violation, floor at 0)
- **Hard:** streak reset + escalating deduction (−5, −10, −20, −40... doubling per consecutive violation in a short window; resets escalation after 30s of clean writing)

---

## CHALLENGE MODE

### Concept
Player receives a structured challenge: specific constraints + a completion goal. Complete it to earn a star rating.

### Challenge structure
Each challenge is defined as:
```json
{
  "id": "four-letter-sprint",
  "name": "Four-Letter Sprint",
  "description": "Write 150 words using only 4-letter words. You have 5 minutes.",
  "constraints": {"wordLength": 4, "dictCheck": true},
  "goal": {"type": "word_count", "target": 150},
  "time_limit_seconds": 300,
  "difficulty_multiplier": 1.5,
  "star_thresholds": {
    "one": {"compliance_min": 0.7},
    "two": {"compliance_min": 0.85, "time_remaining_min": 30},
    "three": {"compliance_min": 0.95, "time_remaining_min": 90, "score_min": 800}
  }
}
```

### Goal types
- `word_count` — write N compliant words
- `time_survive` — keep writing compliantly for N seconds
- `score_target` — reach N points

### Star rating (★ to ★★★)
- ★: completed the goal with minimum compliance
- ★★: completed with good compliance + time/score bonus
- ★★★: completed with excellent compliance, speed, and score
- Specific thresholds per challenge (see structure above)

### 15 curated challenges (v1)
Design these to cover the constraint space and ramp difficulty. Suggested set:

1. **First Steps** — dictCheck only, 50 words, 3 min (tutorial)
2. **Four-Letter Sprint** — wordLength 4, 150 words, 5 min
3. **Three's Company** — wordLength 3, 100 words, 5 min
4. **Five Alive** — wordLength 5, 120 words, 6 min
5. **Alphabet Run** — alphaCycle, 26 words (one full cycle), 3 min
6. **Double Alphabet** — alphaCycle, 52 words (two cycles), 5 min
7. **No Repeats** — noRepeat, 200 words, 8 min
8. **Pangram Dash** — pangram in 50 words, 100 words total, 4 min
9. **Letter Budget** — startLetterMax 3, 150 words, 6 min
10. **Short and Sweet** — wordLength 3 + dictCheck, 80 words, 4 min
11. **Verbose** — wordLength 7+ (min length constraint), 60 words, 5 min
12. **Marathon** — noRepeat + dictCheck, 300 words, 12 min
13. **Tight Alphabet** — alphaCycle + dictCheck, 52 words, 4 min
14. **The Gauntlet Lite** — wordLength 4 + noRepeat + dictCheck, 100 words, 6 min
15. **The Gauntlet** — full Gauntlet preset constraints, 150 words, 10 min

### Random challenge generation
- "Random Challenge" button assembles a challenge from:
  - Pick 1–3 constraints randomly (weighted by compatibility)
  - Generate appropriate word goal and time limit based on constraint difficulty
  - Set star thresholds algorithmically
- Constraints must be feasibility-checked (the Builder already does this)
- Store generated challenges temporarily — don't persist

### Challenge flow
1. Player selects challenge (from curated list or hits Random)
2. Challenge info screen: name, description, constraints, goal, time limit
3. Player selects difficulty (Easy/Medium/Hard) — affects violation penalties only, not the challenge itself
4. Countdown 3-2-1, then editor is live
5. Sidebar shows: score, streak, timer (counting down), word progress bar, compliance %
6. On goal completion OR time expiry: results screen with star rating, final score, stats breakdown
7. Score saved to leaderboard

---

## SCORE ATTACK MODE

### Concept
No fixed goal. Write under chosen constraints, chase the highest score.

### Session types
- **Timed:** player picks duration — 2 min, 5 min, 10 min, or custom
- **Endless:** no timer, session ends when player stops (button or shortcut)

### Constraint selection
- Player picks from: existing presets (all 11 built-in + user custom presets), game-specific presets (see below), or custom constraint combo via the Builder
- Each selection has a difficulty multiplier shown before starting

### Game-specific presets (in addition to existing 11)
These are tuned for Score Attack balance:

1. **Blitz** — wordLength 4, timed 2 min (fast and focused)
2. **Endurance** — noRepeat + dictCheck, endless (how far can you go?)
3. **Alphabet Grind** — alphaCycle + dictCheck, endless (cycle after cycle)
4. **Word Hoarder** — wordLength 5+, pangram in 100, timed 5 min
5. **Chaos** — random 3-constraint combo, timed 3 min

### Score Attack flow
1. Player picks preset/constraints + session type (timed/endless) + duration if timed
2. Player selects difficulty (Easy/Medium/Hard)
3. Countdown 3-2-1, go
4. Sidebar shows: score (large), streak + multiplier, timer (counting up for endless, down for timed), words written, compliance %, best streak this session
5. On session end: results screen with final score, peak streak, compliance %, word count
6. Score saved to leaderboard (per-preset)

---

## PERSISTENCE & LEADERBOARDS

### Storage
- File: `~/.tether/scores.json`
- Structure:
```json
{
  "challenges": {
    "four-letter-sprint": {
      "easy": [
        {"score": 1240, "stars": 3, "compliance": 0.97, "date": "2026-04-11T10:30:00", "words": 152, "time_seconds": 198}
      ],
      "medium": [],
      "hard": []
    }
  },
  "score_attack": {
    "preset:Four-Letter Words": {
      "easy": [
        {"score": 3400, "duration": 300, "words": 210, "compliance": 0.94, "peak_streak": 47, "date": "2026-04-11T11:00:00"}
      ]
    },
    "preset:Blitz": {},
    "custom:wordLength4+noRepeat": {}
  }
}
```

### Leaderboard display
- Accessible from the game panel — small "Scores" button
- Shows top 10 per challenge (per difficulty) and per Score Attack preset (per difficulty)
- Sortable by score, date, compliance
- Simple tkinter Treeview table — nothing fancy

### Data management
- Scores append-only (never overwrite)
- Cap at 100 entries per category, oldest pruned
- No export for v1 (could add later)

---

## GAME-SPECIFIC PRESETS STORAGE

- Game presets stored alongside user presets in `~/.tether/presets.json`
- Distinguished by a `"source": "game"` field (vs `"source": "user"` or `"source": "builtin"`)
- Or: ship game presets as built-in alongside the existing 11, tagged for game mode visibility

---

## IMPLEMENTATION NOTES FOR CLAUDE CODE

### File structure
- All in `tether.py` — single file stays single file
- `word_rarity.json` as a new data file alongside `wordlist.txt`
- `challenges.json` embedded as a Python dict constant in tether.py, or as a separate JSON file (developer preference — Jesse prefers single file, so embed it)
- `~/.tether/scores.json` created on first game session

### Key integration points
- The Game Mode toggle lives in the Editor view's top bar
- Game sidebar replaces (not overlays) the existing sidebar panels
- Scoring engine can be a `GameScorer` class with methods: `score_word(word, constraints, streak, difficulty)`, `check_streak(compliant)`, `get_multiplier(constraints)`
- Challenge manager: `ChallengeManager` class that loads challenges, tracks progress, evaluates star ratings
- Leaderboard: `ScoreBoard` class that reads/writes `scores.json`
- Constraint checking already exists — Game Mode hooks into the same compliance engine, just adds scoring on top

### What NOT to change
- Write mode — completely untouched
- History view — unchanged
- Builder view — unchanged (though game mode can invoke the Builder for custom constraint selection)
- Existing presets — unchanged, just also available in game mode
- Violation panel logic — reused, game mode reads from same violation state

### Build pipeline
- `word_rarity.json` needs to be included in Nuitka build: `--include-data-file=word_rarity.json=word_rarity.json`
- No new Python dependencies
- If challenges are in a separate JSON: also include in build

### Testing priorities
1. Scoring math is correct (unit-testable even without GUI)
2. Streak reset works properly
3. Challenge completion detection triggers at right moment
4. Star rating thresholds feel right (will need manual tuning)
5. Scores persist correctly between sessions
6. Mode toggle doesn't corrupt editor state
7. Timer accuracy (use `time.monotonic()`, not `time.time()`)

---

## CONTEXT FOR CLAUDE CODE SESSION

Start the CC session with:
1. This spec file
2. `tether_tldr.txt`
3. Point CC at `~/Projects/typing/tether.py`

CC should read tether.py first to understand the existing sidebar structure, constraint engine, and preset system before making any changes. The game mode should follow the same patterns and coding style already in the file.

---

## GENERATING word_rarity.json

This needs to happen before or during implementation. Approach:

1. Download individual SCOWL level wordlists (levels 10–80)
2. For each word, record its lowest SCOWL level (= most common usage)
3. Map to tiers:
   - Levels 10–35 → common (×1.0) — omit from file
   - Levels 40–60 → uncommon (×1.25)
   - Levels 65–80 → rare (×1.5)
4. Output JSON: `{"word": multiplier}` for uncommon and rare only
5. Expected file size: ~1–2MB

CC can generate this from SCOWL source data, or Jesse can provide a pre-built file. If SCOWL level data isn't readily available in the right format, a simpler fallback: use word frequency from a corpus (e.g., Google Ngrams unigram frequencies) bucketed into three tiers. But SCOWL tiers are preferred since the wordlist is already SCOWL-sourced.
