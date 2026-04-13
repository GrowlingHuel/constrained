#!/usr/bin/env python3
"""
CONSTRAINED — typing constraint engine
Pure CPython + tkinter. No external dependencies.
Run: python3 constrained.py
"""

import tkinter as tk
from tkinter import messagebox
import re
import time
import json
import os
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════
# PALETTE
# ═══════════════════════════════════════════════════════════════════

BG      = "#0d0d11"   # root background
BG2     = "#090910"   # header, sidebar
BG3     = "#0c0c10"   # cards, builder rows
BORDER  = "#18181e"
ACCENT  = "#f0a500"   # gold
TEXT    = "#e2ddd5"
DIM     = "#666666"
DIM2    = "#3a3a3a"
RED     = "#ef4444"
GREEN   = "#10b981"
BLUE    = "#3b82f6"
AMBER   = "#f59e0b"

MONO    = ("Courier New", 10)
MONO_LG = ("Courier New", 15)
SERIF   = ("Georgia", 10)
SERIF_SM= ("Georgia", 9)

# ═══════════════════════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════════════════════

ALPHABET = list("abcdefghijklmnopqrstuvwxyz")

# % of common English words that START with each letter (~100k word corpus)
START_FREQ = {
    'a':11.6,'b':4.5,'c':9.7,'d':5.5,'e':5.0,'f':4.8,'g':3.5,'h':4.9,
    'i':4.4,'j':0.8,'k':1.1,'l':4.2,'m':5.5,'n':2.8,'o':3.8,'p':9.0,
    'q':0.4,'r':4.9,'s':12.4,'t':8.5,'u':2.4,'v':2.1,'w':4.0,'x':0.1,
    'y':0.5,'z':0.3
}

# Approximate count of common English words at each length
WORDS_PER_LENGTH = {
    2:80, 3:900, 4:3800, 5:8000, 6:15000, 7:23000,
    8:28000, 9:24000, 10:20000, 11:15000, 12:10000
}

PRESETS = [
    {
        "id":"free","name":"Free Write","color":"#6b7280",
        "desc":"No constraints. Just write.",
        "constraints":[]
    },
    {
        "id":"three_letter","name":"Three-Letter Words","color":"#fb923c",
        "desc":"Every word must be exactly 3 letters.",
        "constraints":[{"type":"wordLength","exact":3}]
    },
    {
        "id":"four_letter","name":"Four-Letter Words","color":"#f59e0b",
        "desc":"Every word must be exactly 4 letters.",
        "constraints":[{"type":"wordLength","exact":4}]
    },
    {
        "id":"five_letter","name":"Five-Letter Words","color":"#eab308",
        "desc":"Every word must be exactly 5 letters.",
        "constraints":[{"type":"wordLength","exact":5}]
    },
    {
        "id":"alpha_cycle","name":"Alphabet Cycle","color":"#10b981",
        "desc":"Each word starts with next letter (A→B→C…→Z→A…). X optional.",
        "constraints":[{"type":"alphaCycle","skipX":False,"xOptional":True}]
    },
    {
        "id":"sprint_500","name":"500-Word Sprint","color":"#3b82f6",
        "desc":"Write 500 words in 10 minutes (~50 WPM).",
        "constraints":[{"type":"wordGoal","target":500},{"type":"timeLimit","seconds":600}]
    },
    {
        "id":"sprint_1000","name":"1000-Word Sprint","color":"#6366f1",
        "desc":"Write 1000 words in 15 minutes (~67 WPM).",
        "constraints":[{"type":"wordGoal","target":1000},{"type":"timeLimit","seconds":900}]
    },
    {
        "id":"pangram_100","name":"Pangram in 100","color":"#8b5cf6",
        "desc":"Use every letter of the alphabet within 100 words.",
        "constraints":[{"type":"pangram","withinWords":100}]
    },
    {
        "id":"letter_budget","name":"Letter Budget","color":"#ec4899",
        "desc":"Each starting letter used max 30 times.",
        "constraints":[{"type":"startLetterMax","max":30}]
    },
    {
        "id":"gauntlet","name":"Gauntlet","color":"#ef4444",
        "desc":"4-letter words, alphabet cycle, 300 words in 15 min.",
        "constraints":[
            {"type":"wordLength","exact":4},
            {"type":"alphaCycle","skipX":False,"xOptional":True},
            {"type":"wordGoal","target":300},
            {"type":"timeLimit","seconds":900}
        ]
    },
]

# ═══════════════════════════════════════════════════════════════════
# CONSTRAINT ENGINE  (pure functions — no GUI dependencies)
# ═══════════════════════════════════════════════════════════════════

def clean_word(w: str) -> str:
    return re.sub(r'[^a-zA-Z]', '', w).lower()

def get_words(text: str) -> list:
    return [w for w in text.strip().split() if w]

def cycle_alpha(skip_x: bool) -> list:
    return [l for l in ALPHABET if not (skip_x and l == 'x')]

def analyze_text(text: str, constraints: list, elapsed: int) -> dict:
    raw_words  = get_words(text)
    words      = [clean_word(w) for w in raw_words]
    words      = [w for w in words if w]
    word_count = len(words)
    minutes    = elapsed / 60
    wpm        = round(word_count / minutes) if minutes > 0.1 else 0

    violations    = []
    letter_counts = {}
    used_letters  = set()

    # Pull constraint objects
    wl     = next((c for c in constraints if c['type'] == 'wordLength'),     None)
    cyc    = next((c for c in constraints if c['type'] == 'alphaCycle'),     None)
    sl_max = next((c for c in constraints if c['type'] == 'startLetterMax'), None)
    pangram= next((c for c in constraints if c['type'] == 'pangram'),        None)
    goal_c = next((c for c in constraints if c['type'] == 'wordGoal'),       None)

    alpha = cycle_alpha(cyc.get('skipX', False)) if cyc else []

    for i, word in enumerate(words):
        if not word:
            continue
        first = word[0]
        letter_counts[first] = letter_counts.get(first, 0) + 1
        for ch in word:
            used_letters.add(ch)

        # ── Word length ───────────────────────────────────────────
        if wl and wl.get('exact') and len(word) != wl['exact']:
            raw = raw_words[i] if i < len(raw_words) else word
            violations.append({
                'word_index': i, 'word': raw,
                'message': f'"{raw}" is {len(word)} letters (need {wl["exact"]})',
                'type': 'wordLength'
            })

        # ── Alphabet cycle ────────────────────────────────────────
        if cyc and alpha:
            expected  = alpha[i % len(alpha)]
            x_slot    = (expected == 'x')
            x_optional= cyc.get('xOptional', True)
            if not (x_slot and x_optional) and first != expected:
                raw = raw_words[i] if i < len(raw_words) else word
                violations.append({
                    'word_index': i, 'word': raw,
                    'message': f"Word {i+1}: expected '{expected.upper()}', got '{first.upper()}'",
                    'type': 'alphaCycle'
                })

        # ── Starting letter max ───────────────────────────────────
        if sl_max and letter_counts[first] > sl_max['max']:
            raw = raw_words[i] if i < len(raw_words) else word
            violations.append({
                'word_index': i, 'word': raw,
                'message': f"'{first.upper()}' used {letter_counts[first]}x (max {sl_max['max']})",
                'type': 'startLetterMax'
            })

    # ── Pangram progress ──────────────────────────────────────────
    pang_progress = None
    if pangram:
        window      = words[:pangram['withinWords']]
        window_used = {ch for w in window for ch in w}
        pang_progress = {
            'window_missing': [l for l in ALPHABET if l not in window_used],
            'all_missing':    [l for l in ALPHABET if l not in used_letters],
            'target':          pangram['withinWords']
        }

    # ── Goal progress ─────────────────────────────────────────────
    goal_progress = (
        {'current': word_count, 'target': goal_c['target']} if goal_c else None
    )

    # ── Next expected letter ──────────────────────────────────────
    next_expected = None
    if cyc and alpha:
        nxt = alpha[word_count % len(alpha)]
        if nxt == 'x' and cyc.get('xOptional', True):
            next_expected = 'X*'
        else:
            next_expected = nxt.upper()

    # ── Compliance % ─────────────────────────────────────────────
    structural_viols = [v for v in violations
                        if v['type'] in ('wordLength','alphaCycle','startLetterMax')]
    compliance = (
        max(0, round(((word_count - len(structural_viols)) / word_count) * 100))
        if word_count > 0 else 100
    )

    return {
        'word_count':    word_count,
        'wpm':           wpm,
        'violations':    violations,
        'compliance':    compliance,
        'letter_counts': letter_counts,
        'used_letters':  used_letters,
        'pang_progress': pang_progress,
        'goal_progress': goal_progress,
        'next_expected': next_expected,
    }


def check_feasibility(constraints: list) -> list:
    """Returns a list of {'level': 'warn'|'error', 'msg': str}."""
    warnings = []
    wl     = next((c for c in constraints if c['type'] == 'wordLength'),     None)
    goal   = next((c for c in constraints if c['type'] == 'wordGoal'),       None)
    time_c = next((c for c in constraints if c['type'] == 'timeLimit'),      None)
    sl_max = next((c for c in constraints if c['type'] == 'startLetterMax'), None)
    cyc    = next((c for c in constraints if c['type'] == 'alphaCycle'),     None)

    if wl and wl.get('exact'):
        n = wl['exact']
        avail = WORDS_PER_LENGTH.get(n, 0)
        if avail == 0:
            warnings.append({'level':'error','msg':f'No common English words of exactly {n} letters.'})
        elif avail < 200:
            warnings.append({'level':'warn','msg':f'Only ~{avail} words of length {n} — very limited vocabulary.'})

    if goal and sl_max:
        ceiling = sl_max['max'] * 26
        if goal['target'] > ceiling:
            warnings.append({'level':'error',
                'msg':f'Impossible: {goal["target"]} words at max {sl_max["max"]} per letter = ceiling {ceiling}.'})

    if goal and time_c:
        req_wpm = round(goal['target'] / (time_c['seconds'] / 60))
        if req_wpm > 120:
            warnings.append({'level':'error','msg':f'Requires {req_wpm} WPM — near-impossible for most typists.'})
        elif req_wpm > 80:
            warnings.append({'level':'warn','msg':f'Requires {req_wpm} WPM — fast typist territory.'})

    if cyc and not cyc.get('skipX') and not cyc.get('xOptional'):
        warnings.append({'level':'warn',
            'msg':'X is very rare as a word-starter (~0.1%). Consider making X optional.'})

    if cyc and wl and wl.get('exact') == 3:
        warnings.append({'level':'warn',
            'msg':'Alphabet cycle + 3-letter words: Q, X, Z have very few 3-letter options.'})

    return warnings


def fmt_time(s: int) -> str:
    return f"{s // 60}:{s % 60:02d}"


# ═══════════════════════════════════════════════════════════════════
# APPLICATION
# ═══════════════════════════════════════════════════════════════════

class ConstrainedApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CONSTRAINED")
        self.root.configure(bg=BG)
        self.root.geometry("1120x720")
        self.root.minsize(820, 520)

        # ── App state ─────────────────────────────────────────────
        self.active_preset    : dict       = PRESETS[0]
        self.custom_constraints            = None   # list | None
        self.text_content     : str        = ""
        self.session_started  : bool       = False
        self.elapsed          : int        = 0
        self.timer_target     : int | None = None
        self.timer_running    : bool       = False
        self.history          : list       = []
        self.analysis         : dict       = self._empty_analysis()
        self.current_view     : str        = "editor"

        # ── Builder tk vars ───────────────────────────────────────
        self.b = {
            'wl_on':   tk.BooleanVar(value=False),
            'wl_n':    tk.IntVar(value=4),
            'ac_on':   tk.BooleanVar(value=False),
            'ac_skipx':tk.BooleanVar(value=False),
            'ac_xopt': tk.BooleanVar(value=True),
            'wg_on':   tk.BooleanVar(value=False),
            'wg_n':    tk.IntVar(value=500),
            'tl_on':   tk.BooleanVar(value=False),
            'tl_mins': tk.IntVar(value=10),
            'sl_on':   tk.BooleanVar(value=False),
            'sl_n':    tk.IntVar(value=30),
            'pg_on':   tk.BooleanVar(value=False),
            'pg_n':    tk.IntVar(value=100),
        }
        for v in self.b.values():
            v.trace_add('write', self._on_builder_change)

        self._build_ui()
        self._show_view("editor")

    # ─────────────────────────────────────────────────────────────
    # UI CONSTRUCTION
    # ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=BG2, height=52)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        tk.Label(hdr, text="CONSTRAINED", fg=ACCENT, bg=BG2,
                 font=("Courier New", 14, "bold")).pack(side=tk.LEFT, padx=20)
        tk.Label(hdr, text="typing constraint engine", fg=DIM2, bg=BG2,
                 font=SERIF_SM).pack(side=tk.LEFT, padx=(0, 24))

        self.hdr_timer = tk.Label(hdr, text="", fg=DIM, bg=BG2,
                                   font=("Courier New", 20))
        self.hdr_timer.pack(side=tk.LEFT)

        # Nav
        nav = tk.Frame(hdr, bg=BG2)
        nav.pack(side=tk.RIGHT, padx=16)
        self.nav_btns = {}
        for v, label in [("editor","✎ Editor"),("history","◷ History"),("builder","⊞ Builder")]:
            b = tk.Button(nav, text=label, bg=BG2, fg=DIM, relief=tk.FLAT,
                          font=("Courier New", 9), padx=12, pady=7, cursor="hand2",
                          activebackground=BG2, bd=0,
                          command=lambda v=v: self._show_view(v))
            b.pack(side=tk.LEFT, padx=2)
            self.nav_btns[v] = b

        # ── Body container ────────────────────────────────────────
        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill=tk.BOTH, expand=True)

        self._build_editor_view()
        self._build_history_view()
        self._build_builder_view()

    # ── EDITOR ────────────────────────────────────────────────────

    def _build_editor_view(self):
        self.editor_frame = tk.Frame(self.body, bg=BG)

        # ── Sidebar ───────────────────────────────────────────────
        sb = tk.Frame(self.editor_frame, bg=BG2, width=204)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        sb.pack_propagate(False)

        # Scrollable sidebar content
        sb_canvas = tk.Canvas(sb, bg=BG2, highlightthickness=0)
        sb_canvas.pack(fill=tk.BOTH, expand=True)
        sb_inner = tk.Frame(sb_canvas, bg=BG2)
        sb_canvas.create_window((0, 0), window=sb_inner, anchor=tk.NW)
        sb_inner.bind("<Configure>",
            lambda e: sb_canvas.configure(scrollregion=sb_canvas.bbox("all")))

        # Modes label
        self._sb_label(sb_inner, "MODES")

        # Preset buttons
        self.preset_rows = {}
        for p in PRESETS:
            row = tk.Frame(sb_inner, bg=BG2, cursor="hand2")
            row.pack(fill=tk.X)
            dot = tk.Label(row, text="▪", fg=p['color'], bg=BG2,
                           font=("Courier New", 9), width=2)
            dot.pack(side=tk.LEFT, padx=(8,0))
            lbl = tk.Label(row, text=p['name'], fg=DIM, bg=BG2,
                           font=SERIF_SM, anchor=tk.W, cursor="hand2")
            lbl.pack(side=tk.LEFT, padx=4, pady=6)
            for w in (row, dot, lbl):
                w.bind("<Button-1>", lambda e, pid=p['id']: self._select_preset(pid))
            self.preset_rows[p['id']] = (row, lbl, dot)

        # Stats section
        tk.Frame(sb_inner, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)
        self._sb_label(sb_inner, "STATS")

        self.stat_vars = {}
        for key, label in [
            ('word_count','Words'),('wpm','WPM'),
            ('compliance','Comply'),('violations','Violations'),('time','Time')
        ]:
            row = tk.Frame(sb_inner, bg=BG2)
            row.pack(fill=tk.X, padx=12, pady=2)
            tk.Label(row, text=label, fg=DIM2, bg=BG2,
                     font=("Courier New", 8)).pack(side=tk.LEFT)
            sv = tk.StringVar(value="0")
            lbl = tk.Label(row, textvariable=sv, fg=DIM, bg=BG2,
                           font=("Courier New", 12))
            lbl.pack(side=tk.RIGHT)
            self.stat_vars[key] = (sv, lbl)

        # Progress bars (drawn as Canvas items)
        self.goal_bar_frame  = self._sb_bar_section(sb_inner, "Word goal")
        self.timer_bar_frame = self._sb_bar_section(sb_inner, "Time")

        # Next letter indicator
        tk.Frame(sb_inner, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)
        self._sb_label(sb_inner, "NEXT LETTER")
        self.next_ltr_var = tk.StringVar(value="")
        self.next_ltr_lbl = tk.Label(sb_inner, textvariable=self.next_ltr_var,
                                      fg=ACCENT, bg=BG2, font=("Courier New", 32, "bold"))
        self.next_ltr_lbl.pack(pady=(2,0))
        self.next_ltr_sub = tk.Label(sb_inner, text="", fg=DIM2, bg=BG2,
                                      font=("Courier New", 8))
        self.next_ltr_sub.pack()

        # Pangram missing
        tk.Frame(sb_inner, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)
        self._sb_label(sb_inner, "PANGRAM — MISSING")
        self.pang_var = tk.StringVar(value="")
        self.pang_lbl = tk.Label(sb_inner, textvariable=self.pang_var,
                                  fg=AMBER, bg=BG2, font=("Courier New", 10),
                                  wraplength=180, justify=tk.LEFT)
        self.pang_lbl.pack(anchor=tk.W, padx=12, pady=(0,8))

        # ── Right-hand editor column ──────────────────────────────
        main = tk.Frame(self.editor_frame, bg=BG)
        main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Context bar
        ctx = tk.Frame(main, bg=BG2)
        ctx.pack(fill=tk.X)
        self.ctx_lbl = tk.Label(ctx, text="", fg="#888", bg=BG2,
                                 font=SERIF_SM, anchor=tk.W)
        self.ctx_lbl.pack(side=tk.LEFT, padx=16, pady=7)
        btn_row = tk.Frame(ctx, bg=BG2)
        btn_row.pack(side=tk.RIGHT, padx=8)
        for txt, cmd, col in [
            ("↺ Reset", self._reset_session, DIM),
            ("◼ Save",  self._save_session,  GREEN),
            ("↓ Export",self._export_txt,    BLUE),
        ]:
            tk.Button(btn_row, text=txt, fg=col, bg=BG2, relief=tk.FLAT,
                      font=("Courier New", 8), padx=10, pady=5, cursor="hand2",
                      bd=0, activebackground=BG2, command=cmd).pack(side=tk.LEFT, padx=2)

        # Feasibility warning bar
        self.warn_frame = tk.Frame(main, bg=BG)
        self.warn_frame.pack(fill=tk.X)
        self.warn_widgets = []

        # Text area
        self.text_widget = tk.Text(
            main, bg=BG, fg=TEXT, insertbackground=ACCENT,
            relief=tk.FLAT, font=("Courier New", 15), padx=48, pady=36,
            wrap=tk.WORD, spacing1=3, spacing3=3,
            selectbackground="#252530", selectforeground=TEXT,
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        self.text_widget.bind('<KeyRelease>', self._on_key_release)
        self.text_widget.bind('<KeyPress>',   self._on_key_press)

        # Violations panel (bottom of editor)
        self.viol_frame = tk.Frame(main, bg=BG2)
        # pack_forget initially; shown when violations exist
        self.viol_text = tk.Text(
            self.viol_frame, bg=BG2, fg=RED, font=("Courier New", 9),
            height=4, relief=tk.FLAT, padx=14, pady=6, state=tk.DISABLED
        )
        self.viol_text.pack(fill=tk.X)

    def _sb_label(self, parent, text):
        tk.Label(parent, text=text, fg=DIM2, bg=BG2,
                 font=("Courier New", 8)).pack(anchor=tk.W, padx=12, pady=(6,2))

    def _sb_bar_section(self, parent, label):
        """Returns a frame containing label + progress canvas."""
        f = tk.Frame(parent, bg=BG2)
        f.pack(fill=tk.X, padx=12, pady=3)
        row = tk.Frame(f, bg=BG2)
        row.pack(fill=tk.X)
        tk.Label(row, text=label, fg=DIM2, bg=BG2, font=("Courier New", 8)).pack(side=tk.LEFT)
        sv = tk.StringVar(value="")
        tk.Label(row, textvariable=sv, fg=DIM, bg=BG2,
                 font=("Courier New", 9)).pack(side=tk.RIGHT)
        bar = tk.Canvas(f, bg=BORDER, height=3, highlightthickness=0)
        bar.pack(fill=tk.X, pady=(2,0))
        fill = bar.create_rectangle(0, 0, 0, 3, fill=ACCENT, outline="")
        f._sv   = sv
        f._bar  = bar
        f._fill = fill
        f.pack_forget()   # hidden until needed
        return f

    def _update_bar(self, frame, pct: float, label: str, color: str):
        frame._sv.set(label)
        frame._bar.after_idle(lambda: (
            frame._bar.delete("all"),
            frame._bar.create_rectangle(
                0, 0,
                max(0, int(frame._bar.winfo_width() * min(1, pct / 100))), 3,
                fill=color, outline=""
            )
        ))
        frame.pack(fill=tk.X, padx=12, pady=3)

    # ── HISTORY ───────────────────────────────────────────────────

    def _build_history_view(self):
        self.history_frame = tk.Frame(self.body, bg=BG)

        hdr_row = tk.Frame(self.history_frame, bg=BG)
        hdr_row.pack(fill=tk.X, padx=32, pady=(24, 12))
        tk.Label(hdr_row, text="SESSION HISTORY", fg=DIM2, bg=BG,
                 font=("Courier New", 9)).pack(side=tk.LEFT)
        tk.Button(hdr_row, text="+ New Session", fg=ACCENT, bg=BG,
                  relief=tk.FLAT, font=("Courier New", 9), cursor="hand2",
                  bd=0, activebackground=BG,
                  command=lambda: self._show_view("editor")).pack(side=tk.RIGHT)

        # Scrollable canvas for cards
        canvas = tk.Canvas(self.history_frame, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.history_frame, orient=tk.VERTICAL,
                                  command=canvas.yview, bg=BG2, troughcolor=BG)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True, padx=32)

        self.hist_inner  = tk.Frame(canvas, bg=BG)
        self.hist_window = canvas.create_window((0, 0), window=self.hist_inner, anchor=tk.NW)
        self.hist_canvas = canvas
        self.hist_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(self.hist_window, width=e.width))

    # ── BUILDER ───────────────────────────────────────────────────

    def _build_builder_view(self):
        self.builder_frame = tk.Frame(self.body, bg=BG)

        canvas = tk.Canvas(self.builder_frame, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.builder_frame, orient=tk.VERTICAL,
                                  command=canvas.yview, bg=BG2, troughcolor=BG)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=BG)
        win = canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))

        pad = tk.Frame(inner, bg=BG)
        pad.pack(fill=tk.BOTH, expand=True, padx=48, pady=28)

        tk.Label(pad, text="CONSTRAINT BUILDER", fg=DIM2, bg=BG,
                 font=("Courier New", 9)).pack(anchor=tk.W, pady=(0, 16))

        # ── Constraint toggle rows ────────────────────────────────
        self._brow(pad, "Exact Word Length",
                   "Every word must be exactly N letters long.",
                   self.b['wl_on'],
                   [("Letters:", self.b['wl_n'], 2, 15)])

        alpha_extra = pad
        self._brow(pad, "Alphabet Cycle",
                   "Each word starts with the next letter (A→B→C…→Z→A…).",
                   self.b['ac_on'],
                   [],
                   extra_widgets=self._alpha_extras)

        self._brow(pad, "Word Goal",
                   "Session target: write N words.",
                   self.b['wg_on'],
                   [("Target:", self.b['wg_n'], 10, 50000)])

        self._brow(pad, "Time Limit",
                   "Countdown begins on your first keystroke.",
                   self.b['tl_on'],
                   [("Minutes:", self.b['tl_mins'], 1, 180)])

        self._brow(pad, "Starting Letter Max",
                   "Each letter of the alphabet may start at most N words.",
                   self.b['sl_on'],
                   [("Max:", self.b['sl_n'], 1, 10000)])

        self._brow(pad, "Pangram Challenge",
                   "Use every letter of the alphabet (anywhere in words) within N words.",
                   self.b['pg_on'],
                   [("Within words:", self.b['pg_n'], 26, 1000)])

        # ── Feasibility display ───────────────────────────────────
        self.feas_frame = tk.Frame(pad, bg=BG3)
        self.feas_frame.pack(fill=tk.X, pady=8)
        self.feas_inner = tk.Frame(self.feas_frame, bg=BG3)
        self.feas_inner.pack(fill=tk.X, padx=14, pady=10)
        tk.Label(self.feas_inner,
                 text="Enable constraints above to check feasibility.",
                 fg=DIM2, bg=BG3, font=SERIF_SM).pack(anchor=tk.W)

        # Apply button
        tk.Button(pad, text="APPLY & START SESSION",
                  fg="#000", bg=ACCENT, relief=tk.FLAT,
                  font=("Courier New", 10, "bold"), padx=20, pady=10,
                  cursor="hand2", bd=0, activeforeground="#000", activebackground="#d4920a",
                  command=self._apply_builder).pack(anchor=tk.W, pady=(4, 16))

        # ── Frequency chart ───────────────────────────────────────
        tk.Frame(pad, bg=BORDER, height=1).pack(fill=tk.X, pady=12)
        tk.Label(pad, text="LETTER FREQUENCY  —  % of common English words starting with each letter",
                 fg=DIM2, bg=BG, font=("Courier New", 8)).pack(anchor=tk.W, pady=(0, 8))

        chart = tk.Canvas(pad, bg=BG, height=90, highlightthickness=0)
        chart.pack(fill=tk.X)

        def draw_chart(e=None):
            chart.delete("all")
            w = chart.winfo_width()
            if w < 10:
                return
            bar_w = w / 26
            for i, l in enumerate(ALPHABET):
                freq   = START_FREQ[l]
                bar_h  = max(4, (freq / 12.4) * 58)
                x0, x1 = i * bar_w + 1, (i + 1) * bar_w - 2
                y0, y1 = 65 - bar_h, 65
                rare   = l in ('x', 'q', 'z')
                chart.create_rectangle(x0, y0, x1, y1,
                    fill="#3a1a1a" if rare else "#1e2a1e", outline="")
                chart.create_rectangle(x0, y0, x1, y0 + 2,
                    fill=RED if rare else GREEN, outline="")
                chart.create_text(x0 + bar_w / 2 - 1, 75,
                    text=l.upper(), font=("Courier New", 7), fill=DIM2)

        chart.bind("<Configure>", draw_chart)
        pad.after(120, draw_chart)

        tk.Label(pad, text="Red bars (X, Q, Z) are rare word-starters — plan constraints accordingly.",
                 fg=DIM2, bg=BG, font=("Courier New", 8), pady=4).pack(anchor=tk.W)

    def _brow(self, parent, label, desc, var, spinners, extra_widgets=None):
        """Build one toggle row in the constraint builder."""
        card = tk.Frame(parent, bg=BG3)
        card.pack(fill=tk.X, pady=3)

        top = tk.Frame(card, bg=BG3)
        top.pack(fill=tk.X, padx=14, pady=(10, 4))

        left = tk.Frame(top, bg=BG3)
        left.pack(side=tk.LEFT)
        tk.Label(left, text=label, fg=DIM, bg=BG3,
                 font=("Georgia", 12)).pack(anchor=tk.W)
        tk.Label(left, text=desc, fg=DIM2, bg=BG3,
                 font=("Courier New", 8)).pack(anchor=tk.W)

        tog = tk.Label(top, text="OFF", fg=DIM2, bg=BG3,
                       font=("Courier New", 9, "bold"), cursor="hand2",
                       padx=9, pady=3)
        tog.pack(side=tk.RIGHT, padx=(8, 0))

        # Body shown/hidden on toggle
        body = tk.Frame(card, bg=BG3)

        if spinners:
            row = tk.Frame(body, bg=BG3)
            row.pack(anchor=tk.W, padx=14, pady=(0, 8))
            for lbl_txt, ivar, lo, hi in spinners:
                tk.Label(row, text=lbl_txt, fg=DIM, bg=BG3,
                         font=("Courier New", 10)).pack(side=tk.LEFT)
                tk.Spinbox(row, from_=lo, to=hi, textvariable=ivar,
                           width=8, bg="#0a0a0d", fg=TEXT, insertbackground=ACCENT,
                           relief=tk.FLAT, font=("Courier New", 12),
                           buttonbackground=BG2).pack(side=tk.LEFT, padx=(6, 16))

        if extra_widgets:
            extra_widgets(body)

        def toggle(e=None):
            var.set(not var.get())
            if var.get():
                tog.config(text="ON", fg="#000", bg=ACCENT)
                body.pack(fill=tk.X)
            else:
                tog.config(text="OFF", fg=DIM2, bg=BG3)
                body.pack_forget()

        tog.bind("<Button-1>", toggle)

    def _alpha_extras(self, parent):
        """Extra checkboxes specific to the alphabet cycle row."""
        tk.Checkbutton(parent, text="Skip X entirely (25-letter cycle)",
                       variable=self.b['ac_skipx'], fg=DIM, bg=BG3,
                       selectcolor=BG, activebackground=BG3,
                       font=("Courier New", 9)).pack(anchor=tk.W, padx=14)
        tk.Checkbutton(parent, text="X turn is optional (any letter accepted)",
                       variable=self.b['ac_xopt'], fg=DIM, bg=BG3,
                       selectcolor=BG, activebackground=BG3,
                       font=("Courier New", 9)).pack(anchor=tk.W, padx=14, pady=(0, 8))

    # ─────────────────────────────────────────────────────────────
    # VIEW SWITCHING
    # ─────────────────────────────────────────────────────────────

    def _show_view(self, view: str):
        self.current_view = view
        for f in (self.editor_frame, self.history_frame, self.builder_frame):
            f.pack_forget()
        {
            "editor":  self.editor_frame,
            "history": self.history_frame,
            "builder": self.builder_frame,
        }[view].pack(fill=tk.BOTH, expand=True)

        for v, btn in self.nav_btns.items():
            if v == view:
                btn.config(fg="#000", bg=ACCENT,
                           activeforeground="#000", activebackground=ACCENT)
            else:
                btn.config(fg=DIM, bg=BG2,
                           activeforeground=DIM, activebackground=BG2)

        if view == "history":
            self._refresh_history()
        if view == "editor":
            self.text_widget.focus_set()

    # ─────────────────────────────────────────────────────────────
    # SESSION CONTROL
    # ─────────────────────────────────────────────────────────────

    def _select_preset(self, preset_id: str):
        self.active_preset     = next(p for p in PRESETS if p['id'] == preset_id)
        self.custom_constraints = None
        self._reset_session()

    def _reset_session(self):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_content  = ""
        self.session_started = False
        self.elapsed       = 0
        self.timer_target  = None
        self.timer_running = False
        self.analysis      = self._empty_analysis()
        self._update_all()
        self._show_view("editor")
        self.text_widget.focus_set()

    def _constraints(self) -> list:
        return (self.custom_constraints
                if self.custom_constraints is not None
                else self.active_preset['constraints'])

    # ─────────────────────────────────────────────────────────────
    # INPUT HANDLERS
    # ─────────────────────────────────────────────────────────────

    def _on_key_press(self, event):
        """Block input when timer has expired."""
        if self.timer_target and self.elapsed >= self.timer_target:
            return "break"

    def _on_key_release(self, event):
        """Called after every keystroke in the text area."""
        if self.timer_target and self.elapsed >= self.timer_target:
            return

        self.text_content = self.text_widget.get("1.0", tk.END)

        if not self.session_started and self.text_content.strip():
            self.session_started = True
            tl = next((c for c in self._constraints() if c['type'] == 'timeLimit'), None)
            self.timer_target = tl['seconds'] if tl else None
            self.timer_running = True
            self._tick()

        self.analysis = analyze_text(self.text_content, self._constraints(), self.elapsed)
        self._update_all()

    # ─────────────────────────────────────────────────────────────
    # TIMER
    # ─────────────────────────────────────────────────────────────

    def _tick(self):
        if not self.timer_running:
            return
        if self.timer_target and self.elapsed >= self.timer_target:
            self.timer_running = False
            self._update_timer_label()
            self.root.after(100, self._on_timer_done)
            return
        self.elapsed += 1
        self._update_timer_label()
        # Re-analyse (WPM changes with elapsed time)
        self.analysis = analyze_text(self.text_content, self._constraints(), self.elapsed)
        self._update_stats()
        self.root.after(1000, self._tick)

    def _update_timer_label(self):
        done = self.timer_target and self.elapsed >= self.timer_target
        if self.elapsed == 0:
            self.hdr_timer.config(text="", fg=DIM)
        elif self.timer_target and not done:
            remaining = self.timer_target - self.elapsed
            self.hdr_timer.config(text=fmt_time(remaining), fg=ACCENT)
        else:
            self.hdr_timer.config(text=fmt_time(self.elapsed),
                                   fg=RED if done else DIM)

    def _on_timer_done(self):
        messagebox.showinfo(
            "Time's Up!",
            f"Time's up!\n\n"
            f"Words     : {self.analysis['word_count']}\n"
            f"WPM       : {self.analysis['wpm']}\n"
            f"Compliance: {self.analysis['compliance']}%\n"
            f"Violations: {len(self.analysis['violations'])}\n\n"
            "Use ◼ Save to record this session."
        )

    # ─────────────────────────────────────────────────────────────
    # SAVE / EXPORT
    # ─────────────────────────────────────────────────────────────

    def _save_session(self):
        if not self.text_content.strip():
            messagebox.showinfo("Nothing to save", "Write something first.")
            return
        self.timer_running = False
        session = {
            'id':           int(time.time()),
            'date':         datetime.now().strftime("%Y-%m-%d %H:%M"),
            'preset_name':  "Custom" if self.custom_constraints
                            else self.active_preset['name'],
            'is_custom':    bool(self.custom_constraints),
            'constraints':  list(self._constraints()),
            'excerpt':      self.text_content[:200],
            'word_count':   self.analysis['word_count'],
            'wpm':          self.analysis['wpm'],
            'compliance':   self.analysis['compliance'],
            'violations':   len(self.analysis['violations']),
            'duration':     self.elapsed,
        }
        self.history.insert(0, session)
        self._show_view("history")

    def _export_txt(self):
        content = self.text_widget.get("1.0", tk.END)
        lines = [
            "╔══════════════════════════════════════════╗",
            "║       CONSTRAINED — SESSION EXPORT       ║",
            "╚══════════════════════════════════════════╝",
            "",
            f"Date      : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Mode      : {'Custom' if self.custom_constraints else self.active_preset['name']}",
            f"Duration  : {fmt_time(self.elapsed)}",
            f"Words     : {self.analysis['word_count']}",
            f"WPM       : {self.analysis['wpm']}",
            f"Compliance: {self.analysis['compliance']}%",
            f"Violations: {len(self.analysis['violations'])}",
            "",
            "Constraints applied:",
        ]
        for c in self._constraints():
            lines.append(f"  · {json.dumps(c)}")
        lines += ["", "─" * 44, "", content]

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        os.makedirs(desktop, exist_ok=True)
        path = os.path.join(desktop, f"constrained-{int(time.time())}.txt")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            messagebox.showinfo("Exported", f"Saved to your Desktop:\n{path}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    # ─────────────────────────────────────────────────────────────
    # UI UPDATE METHODS
    # ─────────────────────────────────────────────────────────────

    def _update_all(self):
        self._update_stats()
        self._update_warnings()
        self._update_violations()
        self._update_context_bar()
        self._update_preset_highlight()
        self._update_next_letter()
        self._update_pangram()

    def _update_stats(self):
        a = self.analysis
        vc = len(a['violations'])
        co = a['compliance']

        self.stat_vars['word_count'][0].set(str(a['word_count']))
        self.stat_vars['wpm'][0].set(str(a['wpm']) if self.elapsed > 5 else "—")
        self.stat_vars['compliance'][0].set(f"{co}%")
        self.stat_vars['violations'][0].set(str(vc))
        self.stat_vars['time'][0].set(fmt_time(self.elapsed))

        self.stat_vars['compliance'][1].config(
            fg=RED if co < 80 else AMBER if co < 95 else GREEN)
        self.stat_vars['violations'][1].config(fg=RED if vc > 0 else DIM)

        # Progress bars
        gp = a.get('goal_progress')
        if gp:
            pct = min(100, (gp['current'] / gp['target']) * 100)
            col = GREEN if pct >= 100 else ACCENT
            self._update_bar(self.goal_bar_frame, pct,
                             f"{gp['current']}/{gp['target']}", col)
        else:
            self.goal_bar_frame.pack_forget()

        if self.timer_target:
            pct = min(100, (self.elapsed / self.timer_target) * 100)
            done = self.elapsed >= self.timer_target
            self._update_bar(self.timer_bar_frame,
                             pct,
                             "DONE" if done else fmt_time(self.timer_target - self.elapsed) + " left",
                             RED if done else BLUE)
        else:
            self.timer_bar_frame.pack_forget()

        self._update_timer_label()

    def _update_warnings(self):
        for w in self.warn_widgets:
            w.destroy()
        self.warn_widgets.clear()
        for w in check_feasibility(self._constraints()):
            is_err = w['level'] == 'error'
            lbl = tk.Label(
                self.warn_frame,
                text=f"{'⚠ IMPOSSIBLE:' if is_err else '⚡'} {w['msg']}",
                fg=RED if is_err else AMBER,
                bg="#1a0808" if is_err else "#18140a",
                font=("Courier New", 9), anchor=tk.W, padx=16, pady=5
            )
            lbl.pack(fill=tk.X)
            self.warn_widgets.append(lbl)

    def _update_violations(self):
        recent = self.analysis['violations'][-6:]
        self.viol_text.config(state=tk.NORMAL)
        self.viol_text.delete("1.0", tk.END)
        if recent:
            self.viol_frame.pack(fill=tk.X, side=tk.BOTTOM)
            for v in recent:
                self.viol_text.insert(tk.END, f"✗  {v['message']}\n")
        else:
            self.viol_frame.pack_forget()
        self.viol_text.config(state=tk.DISABLED)

    def _update_context_bar(self):
        name = "Custom" if self.custom_constraints else self.active_preset['name']
        desc = "Custom constraints" if self.custom_constraints else self.active_preset['desc']
        self.ctx_lbl.config(text=f"{name}  —  {desc}")

    def _update_preset_highlight(self):
        for pid, (row, lbl, dot) in self.preset_rows.items():
            active = (pid == self.active_preset['id'] and not self.custom_constraints)
            bg = "#13131a" if active else BG2
            fg = TEXT if active else DIM
            row.config(bg=bg); lbl.config(bg=bg, fg=fg); dot.config(bg=bg)

    def _update_next_letter(self):
        ne = self.analysis.get('next_expected')
        if ne:
            self.next_ltr_var.set(ne.replace('*', ''))
            self.next_ltr_sub.config(
                text="(optional)" if ne.endswith('*') else "next start letter")
        else:
            self.next_ltr_var.set('')
            self.next_ltr_sub.config(text='')

    def _update_pangram(self):
        pp = self.analysis.get('pang_progress')
        if pp:
            missing = ''.join(pp['window_missing']).upper()
            self.pang_var.set(missing if missing else '✓ ALL LETTERS USED')
        else:
            self.pang_var.set('')

    # ─────────────────────────────────────────────────────────────
    # HISTORY VIEW
    # ─────────────────────────────────────────────────────────────

    def _refresh_history(self):
        for w in self.hist_inner.winfo_children():
            w.destroy()

        if not self.history:
            tk.Label(self.hist_inner,
                     text="No sessions saved yet.",
                     fg=DIM2, bg=BG, font=("Georgia", 13, "italic"),
                     pady=60).pack()
            return

        for s in self.history:
            card = tk.Frame(self.hist_inner, bg=BG3)
            card.pack(fill=tk.X, pady=4)

            body = tk.Frame(card, bg=BG3)
            body.pack(fill=tk.X, padx=18, pady=(12, 8))

            # Left: text info
            left = tk.Frame(body, bg=BG3)
            left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            name_row = tk.Frame(left, bg=BG3)
            name_row.pack(anchor=tk.W)
            tk.Label(name_row, text=s['preset_name'], fg=TEXT, bg=BG3,
                     font=("Georgia", 12)).pack(side=tk.LEFT)
            if s['is_custom']:
                tk.Label(name_row, text=" CUSTOM", fg=ACCENT, bg=BG3,
                         font=("Courier New", 8)).pack(side=tk.LEFT, padx=4)

            tk.Label(left, text=f"{s['date']}  ·  {fmt_time(s['duration'])}",
                     fg=DIM2, bg=BG3, font=("Courier New", 8)).pack(anchor=tk.W)

            excerpt = s['excerpt'][:140] + ("…" if len(s['excerpt']) > 140 else "")
            tk.Label(left, text=excerpt, fg="#3a3a3a", bg=BG3,
                     font=("Courier New", 9), wraplength=520,
                     justify=tk.LEFT).pack(anchor=tk.W, pady=(5, 0))

            # Right: metrics
            right = tk.Frame(body, bg=BG3)
            right.pack(side=tk.RIGHT, padx=(12, 0))
            co = s['compliance']
            co_col = RED if co < 80 else AMBER if co < 95 else GREEN
            for val, lbl, col in [
                (s['word_count'], "words", ACCENT),
                (s['wpm'],        "wpm",   BLUE),
                (f"{co}%",        "comply",co_col),
            ]:
                m = tk.Frame(right, bg=BG3)
                m.pack(side=tk.LEFT, padx=10)
                tk.Label(m, text=str(val), fg=col, bg=BG3,
                         font=("Courier New", 18)).pack()
                tk.Label(m, text=lbl, fg=DIM2, bg=BG3,
                         font=("Courier New", 8)).pack()

            # Suggestions
            if co < 90:
                self._hist_note(card,
                    "↳  Compliance below 90%. Try the same mode again, or a simpler preset.", DIM2)
            elif co >= 98 and s['wpm'] > 0:
                self._hist_note(card,
                    "↳  Near-perfect. Consider adding a time limit or word goal.", "#1a3a2a")

        self.hist_canvas.configure(scrollregion=self.hist_canvas.bbox("all"))

    def _hist_note(self, parent, text, fg):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, padx=18)
        tk.Label(parent, text=text, fg=fg, bg=BG3,
                 font=("Courier New", 8, "italic"),
                 anchor=tk.W, padx=18, pady=5).pack(fill=tk.X)

    # ─────────────────────────────────────────────────────────────
    # BUILDER LOGIC
    # ─────────────────────────────────────────────────────────────

    def _constraints_from_builder(self) -> list:
        c = []
        if self.b['wl_on'].get():
            c.append({'type':'wordLength', 'exact': self.b['wl_n'].get()})
        if self.b['ac_on'].get():
            c.append({'type':'alphaCycle',
                      'skipX':    self.b['ac_skipx'].get(),
                      'xOptional':self.b['ac_xopt'].get()})
        if self.b['wg_on'].get():
            c.append({'type':'wordGoal',  'target':  self.b['wg_n'].get()})
        if self.b['tl_on'].get():
            c.append({'type':'timeLimit', 'seconds': self.b['tl_mins'].get() * 60})
        if self.b['sl_on'].get():
            c.append({'type':'startLetterMax', 'max': self.b['sl_n'].get()})
        if self.b['pg_on'].get():
            c.append({'type':'pangram', 'withinWords': self.b['pg_n'].get()})
        return c

    def _on_builder_change(self, *_):
        """Called whenever any builder var changes — refresh feasibility."""
        c = self._constraints_from_builder()
        ws = check_feasibility(c)

        for w in self.feas_inner.winfo_children():
            w.destroy()

        if not c:
            tk.Label(self.feas_inner,
                     text="Enable constraints above to check feasibility.",
                     fg=DIM2, bg=BG3, font=SERIF_SM).pack(anchor=tk.W)
        elif not ws:
            tk.Label(self.feas_inner, text="✓  Constraints look feasible.",
                     fg=GREEN, bg=BG3, font=("Courier New", 10)).pack(anchor=tk.W)
        else:
            for w in ws:
                is_err = w['level'] == 'error'
                tk.Label(self.feas_inner,
                         text=f"{'⚠  IMPOSSIBLE:' if is_err else '⚡  '} {w['msg']}",
                         fg=RED if is_err else AMBER,
                         bg=BG3, font=("Courier New", 9)).pack(anchor=tk.W, pady=2)

    def _apply_builder(self):
        c = self._constraints_from_builder()
        self.custom_constraints = c if c else None
        self._reset_session()

    # ─────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _empty_analysis() -> dict:
        return {
            'word_count': 0, 'wpm': 0, 'violations': [], 'compliance': 100,
            'letter_counts': {}, 'used_letters': set(),
            'pang_progress': None, 'goal_progress': None, 'next_expected': None,
        }


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    app  = ConstrainedApp(root)
    root.mainloop()
