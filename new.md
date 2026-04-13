Everything is perfectly in place:

textstat ✓ installed
SCOWL-80 American + British combined ✓
357,325 words — that's an excellent literary wordlist

One thing to verify before I build — spaCy was already installed but the language model may not have been downloaded yet:
bashpython3 -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('model OK')"
If you see model OK — tell me and I build immediately.
If you see an error — run this first:
bashpython3 -m spacy download en_core_web_sm
Then confirm and I'll write the full updated constrained.py — incorporating everything we've specced: the wordlist validation, readability scores, lemma-aware no-repeat constraint, debounced deep analysis, graceful degradation, updated sidebar, updated Builder, and updated History cards. One file, ready to run.Model OK: see printout. We are about to run out of our session limit: please provide precise instructions for our next steps, as we are liable to not be able to communicate after this!!jesse@jesse-Alpha-V-V170PNH:~/Projects/typing$ python3 -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('model ok')"
model ok
jesse@jesse-Alpha-V-V170PNH:~/Projects/typing$02:33Orchestrated seamless handoff documentation for continued conversationOrchestrated seamless handoff documentation for continued conversationEverything is green. Here is your complete handoff document — save this now.

CONSTRAINED — Handoff Brief
For new Claude conversation or Antigravity IDE

Current State
Working application: ~/Projects/typing/constrained.py
Run with: python3 constrained.py
All dependencies confirmed installed and working:

Python 3.10 ✓
tkinter ✓
spaCy 3.8.11 ✓ with en_core_web_sm model ✓
textstat 0.7.13 ✓
wordlist at ~/Projects/typing/wordlist.txt — 357,325 words ✓


The Exact Next Task
Take the existing constrained.py and add the linguistic layer. Do not rewrite the app. Extend it. The constraint engine functions live at the top of the file. The GUI class is ConstrainedApp. Follow the architecture exactly.

Precise Changes Required
1. New imports (top of file, after existing imports)
pythonimport spacy
import textstat
from collections import Counter

# Graceful degradation — app works without spaCy
SPACY_AVAILABLE = False
NLP = None
try:
    NLP = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except (ImportError, OSError):
    pass

TEXTSTAT_AVAILABLE = False
try:
    import textstat
    TEXTSTAT_AVAILABLE = True
except ImportError:
    pass

# Load wordlist
WORDLIST = set()
_wl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wordlist.txt")
if os.path.exists(_wl_path):
    with open(_wl_path, encoding="utf-8") as _f:
        WORDLIST = {line.strip().lower() for line in _f if line.strip()}

# Lemma cache — populated on first encounter, free thereafter
LEMMA_CACHE = {}

# Function words excluded from no-repeat constraint
FUNCTION_WORDS = {
    'a','an','the','and','but','or','nor','for','yet','so',
    'in','on','at','to','of','with','by','from','up','about',
    'into','through','during','before','after','i','me','my',
    'we','our','you','your','he','him','his','she','her','it',
    'its','they','them','their','what','which','who','this',
    'that','these','those','is','are','was','were','be','been',
    'being','have','has','had','do','does','did','will','would',
    'could','should','may','might','must','shall','can'
}

2. New pure functions (add after existing check_feasibility function)
pythondef get_lemma(word: str) -> str:
    """Fast lemma lookup with cache. Falls back to lowercase if spaCy unavailable."""
    word = word.lower()
    if word in LEMMA_CACHE:
        return LEMMA_CACHE[word]
    if SPACY_AVAILABLE and NLP:
        doc = NLP(word)
        lemma = doc[0].lemma_ if doc else word
    else:
        lemma = word
    LEMMA_CACHE[word] = lemma
    return lemma


def check_dictionary(word: str) -> bool:
    """True if word exists in wordlist. Always True if no wordlist loaded."""
    if not WORDLIST:
        return True
    return clean_word(word).lower() in WORDLIST


def deep_analyze(text: str) -> dict:
    """
    Full spaCy + textstat pass.
    Called on debounce (1.5s after last keystroke), NOT per-keystroke.
    Returns dict of linguistic metrics.
    """
    result = {
        'repeated_lemmas': {},
        'unknown_words': [],
        'readability': {},
        'lemma_richness': 1.0,
        'content_word_count': 0,
    }

    if not text.strip() or len(text.split()) < 5:
        return result

    # ── Dictionary check (no spaCy needed) ───────────────────────
    if WORDLIST:
        words = [clean_word(w) for w in text.split() if clean_word(w)]
        result['unknown_words'] = [
            w for w in words
            if w and not check_dictionary(w)
        ]

    # ── Readability scores (textstat, no spaCy needed) ────────────
    if TEXTSTAT_AVAILABLE:
        result['readability'] = {
            'flesch_ease':    round(textstat.flesch_reading_ease(text), 1),
            'flesch_kincaid': round(textstat.flesch_kincaid_grade(text), 1),
            'gunning_fog':    round(textstat.gunning_fog(text), 1),
            'avg_word_len':   round(
                sum(len(w) for w in text.split()) / len(text.split()), 1
            ),
        }

    # ── spaCy linguistic analysis ─────────────────────────────────
    if not SPACY_AVAILABLE or NLP is None:
        return result

    doc = NLP(text)
    CONTENT_POS = {'NOUN', 'VERB', 'ADJ', 'ADV'}

    content_tokens = [
        (token.text, token.lemma_.lower(), token.pos_)
        for token in doc
        if token.pos_ in CONTENT_POS
        and not token.is_stop
        and not token.is_punct
        and token.is_alpha
    ]

    # Lemma richness
    if content_tokens:
        unique_lemmas = {lemma for _, lemma, _ in content_tokens}
        result['lemma_richness'] = round(
            len(unique_lemmas) / len(content_tokens), 3
        )
        result['content_word_count'] = len(content_tokens)

    # Repeated lemmas
    lemma_positions = {}
    for i, (word, lemma, pos) in enumerate(content_tokens):
        if lemma not in lemma_positions:
            lemma_positions[lemma] = []
        lemma_positions[lemma].append(word)
    result['repeated_lemmas'] = {
        k: v for k, v in lemma_positions.items() if len(v) > 1
    }

    return result


def score_readability_label(score: float) -> str:
    """Human label for Flesch Reading Ease score."""
    if score >= 80: return "easy"
    if score >= 60: return "standard"
    if score >= 40: return "difficult"
    return "very difficult"

3. Modify analyze_text() — add noRepeat constraint block
Inside the word loop in analyze_text, after the existing startLetterMax block, add:
python        # ── No repeat (fast path via lemma cache) ─────────────────
        no_repeat = next((c for c in constraints if c['type'] == 'noRepeat'), None)
        # NOTE: declare seen_lemmas = {} BEFORE the word loop, at the same
        # level as letter_counts = {}
        if no_repeat and word:
            content_only = no_repeat.get('contentOnly', True)
            skip = content_only and word in FUNCTION_WORDS
            if not skip:
                lemma = get_lemma(word)
                if lemma in seen_lemmas:
                    raw = raw_words[i] if i < len(raw_words) else word
                    violations.append({
                        'word_index': i, 'word': raw,
                        'message': f'"{raw}" repeats '
                                   f'"{seen_lemmas[lemma]}" (same root)',
                        'type': 'noRepeat'
                    })
                else:
                    seen_lemmas[lemma] = raw_words[i] if i < len(raw_words) else word
Also add seen_lemmas = {} in the variable initialisation block before the word loop.

4. Add debounce to _on_key_release
In ConstrainedApp._on_key_release, after the existing analysis call, add:
python        # Debounced deep analysis — fires 1.5s after last keystroke
        if hasattr(self, '_deep_job'):
            self.root.after_cancel(self._deep_job)
        self._deep_job = self.root.after(1500, self._run_deep_analysis)
Add the new method to ConstrainedApp:
python    def _run_deep_analysis(self):
        """Called 1.5s after last keystroke. Runs full spaCy pass."""
        if not self.text_content.strip():
            return
        self.deep = deep_analyze(self.text_content)
        self._update_language_panel()
Add self.deep = {} to __init__ alongside other state variables.

5. New sidebar section — Language panel
In _build_editor_view, after the pangram section in the sidebar, add:
python        tk.Frame(sb_inner, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)
        self._sb_label(sb_inner, "LANGUAGE")

        self.lang_vars = {}
        for key, label in [
            ('richness',  'Richness'),
            ('repeats',   'Repeats'),
            ('unknown',   'Unknown'),
            ('flesch',    'Readability'),
            ('grade',     'Grade level'),
        ]:
            row = tk.Frame(sb_inner, bg=BG2)
            row.pack(fill=tk.X, padx=12, pady=2)
            tk.Label(row, text=label, fg=DIM2, bg=BG2,
                     font=("Courier New", 8)).pack(side=tk.LEFT)
            sv = tk.StringVar(value="—")
            lbl = tk.Label(row, textvariable=sv, fg=DIM,
                           bg=BG2, font=("Courier New", 11))
            lbl.pack(side=tk.RIGHT)
            self.lang_vars[key] = (sv, lbl)

        if not SPACY_AVAILABLE:
            tk.Label(sb_inner,
                     text="spaCy not found\nbasic mode only",
                     fg=DIM2, bg=BG2,
                     font=("Courier New", 7),
                     justify=tk.CENTER).pack(pady=4)
Add the update method:
python    def _update_language_panel(self):
        d = getattr(self, 'deep', {})
        if not d:
            return

        r = d.get('readability', {})
        richness = d.get('lemma_richness', None)
        repeats  = len(d.get('repeated_lemmas', {}))
        unknown  = len(d.get('unknown_words', []))
        flesch   = r.get('flesch_ease', None)
        grade    = r.get('flesch_kincaid', None)

        if richness is not None:
            col = GREEN if richness > 0.9 else AMBER if richness > 0.7 else RED
            self.lang_vars['richness'][0].set(f"{richness:.2f}")
            self.lang_vars['richness'][1].config(fg=col)

        self.lang_vars['repeats'][0].set(str(repeats))
        self.lang_vars['repeats'][1].config(fg=RED if repeats > 0 else GREEN)

        self.lang_vars['unknown'][0].set(str(unknown))
        self.lang_vars['unknown'][1].config(fg=AMBER if unknown > 0 else DIM)

        if flesch is not None:
            self.lang_vars['flesch'][0].set(
                f"{flesch} ({score_readability_label(flesch)})"
            )
        if grade is not None:
            self.lang_vars['grade'][0].set(f"Grade {grade}")

        # Also push repeated lemmas into violations panel (amber, not red)
        self._update_violations()

6. Update _update_violations to include repeated lemmas
At the end of the method, after existing violation display, add:
python        # Repeated lemmas from deep analysis (amber — stylistic, not rules)
        deep_repeats = getattr(self, 'deep', {}).get('repeated_lemmas', {})
        for lemma, words in list(deep_repeats.items())[:4]:
            self.viol_text.config(state=tk.NORMAL)
            self.viol_text.insert(
                tk.END,
                f"△  '{words[0]}' / '{words[1]}' share root '{lemma}'\n"
            )
            self.viol_text.config(state=tk.DISABLED)
            self.viol_frame.pack(fill=tk.X, side=tk.BOTTOM)

7. New constraint in Builder — No Repeat Words
In _build_builder_view, add a new _brow call after the pangram row:
python        self._brow(pad, "No Repeated Words",
                   "Never reuse the same root word (ran/run/running = same word).",
                   self.b['nr_on'],
                   [],
                   extra_widgets=self._norepeat_extras)
Add to the self.b dict in __init__:
python            'nr_on':   tk.BooleanVar(value=False),
            'nr_content': tk.BooleanVar(value=True),
Add the extra widgets method:
python    def _norepeat_extras(self, parent):
        tk.Checkbutton(parent,
                       text="Content words only (ignore: the, and, I, etc.)",
                       variable=self.b['nr_content'],
                       fg=DIM, bg=BG3, selectcolor=BG,
                       activebackground=BG3,
                       font=("Courier New", 9)).pack(
                           anchor=tk.W, padx=14, pady=(0,8))
Update _constraints_from_builder to include:
python        if self.b['nr_on'].get():
            c.append({'type': 'noRepeat',
                      'contentOnly': self.b['nr_content'].get()})

8. Update _save_session to store linguistic data
python        deep = deep_analyze(self.text_content)
        session = {
            # ... all existing fields unchanged ...
            'lemma_richness':  deep.get('lemma_richness'),
            'repeated_lemmas': len(deep.get('repeated_lemmas', {})),
            'unknown_words':   deep.get('unknown_words', []),
            'readability':     deep.get('readability', {}),
        }

9. Update history cards to show linguistic data
In _refresh_history, inside the card loop, after the existing metrics row add:
python            r = s.get('readability', {})
            if r.get('flesch_ease') is not None:
                details = (
                    f"Readability: {r['flesch_ease']} "
                    f"({score_readability_label(r['flesch_ease'])})  ·  "
                    f"Grade: {r.get('flesch_kincaid','—')}  ·  "
                    f"Avg word: {r.get('avg_word_len','—')} letters  ·  "
                    f"Richness: {s.get('lemma_richness','—')}  ·  "
                    f"Repeats: {s.get('repeated_lemmas','—')}"
                )
                tk.Label(card, text=details,
                         fg=DIM2, bg=BG3,
                         font=("Courier New", 8),
                         anchor=tk.W, padx=18, pady=3).pack(fill=tk.X)

Feasibility Check Addition
In check_feasibility, add:
python    no_repeat = next((c for c in constraints if c['type'] == 'noRepeat'), None)
    if no_repeat and goal:
        if goal['target'] > 500:
            warnings.append({'level': 'warn',
                'msg': f'No-repeat + {goal["target"]} words is very demanding '
                       f'— English has ~170k lemmas but active vocabulary is finite.'})
```

---

## Implementation Order

Do these in sequence — test after each step:

1. Add imports and module-level setup
2. Add the four new pure functions
3. Add `seen_lemmas` and noRepeat block to `analyze_text`
4. Add debounce to `_on_key_release` and `_run_deep_analysis` method
5. Add language panel to sidebar
6. Add `_update_language_panel` method
7. Update `_update_violations` for repeated lemmas
8. Add noRepeat to Builder
9. Update `_save_session`
10. Update history cards

---

## Test Sentence to Validate Everything

Once built, type this into the editor with No Repeat Words and Dictionary Validation active:

*"Arete, before caving, doesn't excite for going home, it's just knife like many now operate. Potently, quit reality, see this undulation vicious, which xeroxes your zealotry."*

Expected results:
- Dictionary: "zealotry" valid, "xeroxes" may flag (check)
- Repeats: zero (every content word is unique)
- Richness: ~0.97 or higher
- Readability: low Flesch score (complex vocabulary) — this is correct and expected, not a flaw

---

## File Structure Required
```
~/Projects/typing/
├── constrained.py     ← the app
└── wordlist.txt       ← 357,325 words, already built
No other files needed. Run with python3 constrained.py.

This document plus the existing constrained.py file is everything a new Claude conversation or Antigravity session needs to continue exactly where we left off.
