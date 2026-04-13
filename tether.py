#!/usr/bin/env python3
"""
TETHER — typing constraint engine  v0.2
CPython + tkinter. Optional: spaCy, textstat.
Run: python3 tether.py

Persistent data stored in: ~/.tether/
  history.json   — all saved sessions (survives between launches)
  presets.json   — user-saved custom presets
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import re
import time
import json
import os
import threading
import urllib.request
import urllib.error
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════
# APP DATA DIRECTORY  (persistent storage)
# ═══════════════════════════════════════════════════════════════════

VERSION = "0.3.2"
GITHUB_REPO = "GrowlingHuel/tether"

APP_DIR           = os.path.join(os.path.expanduser("~"), ".tether")
HISTORY_FILE      = os.path.join(APP_DIR, "history.json")
PRESETS_FILE      = os.path.join(APP_DIR, "presets.json")
ONBOARDING_FILE   = os.path.join(APP_DIR, "seen_onboarding")
SCORES_FILE       = os.path.join(APP_DIR, "scores.json")


def ensure_app_dir():
    os.makedirs(APP_DIR, exist_ok=True)


def load_history() -> list:
    ensure_app_dir()
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history: list):
    ensure_app_dir()
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: could not save history: {e}")


def load_user_presets() -> list:
    ensure_app_dir()
    if not os.path.exists(PRESETS_FILE):
        return []
    try:
        with open(PRESETS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_user_presets(presets: list):
    ensure_app_dir()
    try:
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: could not save presets: {e}")


def fetch_latest_version() -> str | None:
    """Fetch latest release tag from GitHub. Returns tag string or None."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    try:
        req = urllib.request.Request(url,
            headers={"User-Agent": f"Tether/{VERSION}"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("tag_name", "").lstrip("v")
    except Exception:
        return None


def is_newer(remote: str, local: str) -> bool:
    """Return True if remote version is strictly newer than local."""
    try:
        r = tuple(int(x) for x in remote.split("."))
        l = tuple(int(x) for x in local.split("."))
        return r > l
    except Exception:
        return False


def onboarding_seen() -> bool:
    return os.path.exists(ONBOARDING_FILE)


def mark_onboarding_seen():
    ensure_app_dir()
    try:
        with open(ONBOARDING_FILE, "w") as f:
            f.write("1")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
# OPTIONAL DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════

SPACY_AVAILABLE = False
NLP = None
try:
    import spacy
    NLP = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except (ImportError, OSError):
    pass

TEXTSTAT_AVAILABLE = False
try:
    import textstat as _textstat
    TEXTSTAT_AVAILABLE = True
except ImportError:
    pass

# Wordlist
WORDLIST: set = set()
_wl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wordlist.txt")
if os.path.exists(_wl_path):
    with open(_wl_path, encoding="utf-8") as _f:
        WORDLIST = {line.strip().lower() for line in _f if line.strip()}

WORD_RARITY: dict = {}
_wr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "word_rarity.json")
if os.path.exists(_wr_path):
    try:
        with open(_wr_path, encoding="utf-8") as _f:
            WORD_RARITY = json.load(_f)
    except Exception:
        pass

LEMMA_CACHE: dict = {}

FUNCTION_WORDS = {
    'a','an','the','and','but','or','nor','for','yet','so',
    'in','on','at','to','of','with','by','from','up','about',
    'into','through','during','before','after','i','me','my',
    'we','our','you','your','he','him','his','she','her','it',
    'its','they','them','their','what','which','who','this',
    'that','these','those','is','are','was','were','be','been',
    'being','have','has','had','do','does','did','will','would',
    'could','should','may','might','must','shall','can','not',
    'no','if','as','us','than','then','when','where','how'
}

# ═══════════════════════════════════════════════════════════════════
# PALETTE
# ═══════════════════════════════════════════════════════════════════

BG     = "#0d0d11"
BG2    = "#090910"
BG3    = "#0c0c10"
BORDER = "#18181e"
ACCENT = "#f0a500"
TEXT   = "#e2ddd5"
DIM    = "#666666"
DIM2   = "#3a3a3a"
RED    = "#ef4444"
GREEN  = "#10b981"
BLUE   = "#3b82f6"
AMBER  = "#f59e0b"

SERIF_SM  = ("Georgia", 9)
GAME_BG   = "#0c0b14"
GAME_BG2  = "#100f1c"
GAME_ACC  = "#7c3aed"

# ═══════════════════════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════════════════════

ALPHABET = list("abcdefghijklmnopqrstuvwxyz")

START_FREQ = {
    'a':11.6,'b':4.5,'c':9.7,'d':5.5,'e':5.0,'f':4.8,'g':3.5,'h':4.9,
    'i':4.4,'j':0.8,'k':1.1,'l':4.2,'m':5.5,'n':2.8,'o':3.8,'p':9.0,
    'q':0.4,'r':4.9,'s':12.4,'t':8.5,'u':2.4,'v':2.1,'w':4.0,'x':0.1,
    'y':0.5,'z':0.3
}

WORDS_PER_LENGTH = {
    2:80, 3:900, 4:3800, 5:8000, 6:15000, 7:23000,
    8:28000, 9:24000, 10:20000, 11:15000, 12:10000
}

BUILTIN_PRESETS = [
    {"id":"free","name":"Free Write","color":"#6b7280",
     "desc":"No constraints. Just write.",
     "constraints":[], "builtin":True},
    {"id":"three_letter","name":"Three-Letter Words","color":"#fb923c",
     "desc":"Every word must be exactly 3 letters.",
     "constraints":[{"type":"wordLength","exact":3}], "builtin":True},
    {"id":"four_letter","name":"Four-Letter Words","color":"#f59e0b",
     "desc":"Every word must be exactly 4 letters.",
     "constraints":[{"type":"wordLength","exact":4}], "builtin":True},
    {"id":"five_letter","name":"Five-Letter Words","color":"#eab308",
     "desc":"Every word must be exactly 5 letters.",
     "constraints":[{"type":"wordLength","exact":5}], "builtin":True},
    {"id":"alpha_cycle","name":"Alphabet Cycle","color":"#10b981",
     "desc":"Each word starts with next letter (A-B-C... X optional).",
     "constraints":[{"type":"alphaCycle","skipX":False,"xOptional":True}],
     "builtin":True},
    {"id":"no_repeat","name":"No Repeated Words","color":"#8b5cf6",
     "desc":"Never reuse the same root word (ran=run=running).",
     "constraints":[{"type":"noRepeat","contentOnly":True}], "builtin":True},
    {"id":"sprint_500","name":"500-Word Sprint","color":"#3b82f6",
     "desc":"Write 500 words in 10 minutes (~50 WPM).",
     "constraints":[{"type":"wordGoal","target":500},
                    {"type":"timeLimit","seconds":600}], "builtin":True},
    {"id":"sprint_1000","name":"1000-Word Sprint","color":"#6366f1",
     "desc":"Write 1000 words in 15 minutes (~67 WPM).",
     "constraints":[{"type":"wordGoal","target":1000},
                    {"type":"timeLimit","seconds":900}], "builtin":True},
    {"id":"pangram_100","name":"Pangram in 100","color":"#8b5cf6",
     "desc":"Use every letter of the alphabet within 100 words.",
     "constraints":[{"type":"pangram","withinWords":100}], "builtin":True},
    {"id":"letter_budget","name":"Letter Budget","color":"#ec4899",
     "desc":"Each starting letter used max 30 times.",
     "constraints":[{"type":"startLetterMax","max":30}], "builtin":True},
    {"id":"gauntlet","name":"Gauntlet","color":"#ef4444",
     "desc":"4-letter words, alphabet cycle, no repeats, 300 words/15 min.",
     "constraints":[
         {"type":"wordLength","exact":4},
         {"type":"alphaCycle","skipX":False,"xOptional":True},
         {"type":"noRepeat","contentOnly":True},
         {"type":"wordGoal","target":300},
         {"type":"timeLimit","seconds":900}
     ], "builtin":True},
]

_AC = {"type": "alphaCycle", "skipX": False, "xOptional": True}

GAME_CHALLENGES = [
    {"id":"first-steps","name":"First Steps",
     "requires":None,
     "description":"Write 50 real dictionary words. A gentle warm-up.",
     "constraints":[{"type":"dictCheck"}],
     "goal":{"type":"word_count","target":50},
     "time_limit_seconds":180,"difficulty_multiplier":1.0,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":30},
         "three":{"compliance_min":0.95,"time_remaining_min":60,"score_min":160}}},
    {"id":"four-letter-sprint","name":"Four-Letter Sprint",
     "requires":None,
     "description":"Write 150 words using only 4-letter words. You have 5 minutes.",
     "constraints":[{"type":"wordLength","exact":4}],
     "goal":{"type":"word_count","target":150},
     "time_limit_seconds":300,"difficulty_multiplier":1.5,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":30},
         "three":{"compliance_min":0.95,"time_remaining_min":90,"score_min":800}}},
    {"id":"threes-company","name":"Three's Company",
     "requires":None,
     "description":"Write 100 words — every word exactly 3 letters. You have 5 minutes.",
     "constraints":[{"type":"wordLength","exact":3}],
     "goal":{"type":"word_count","target":100},
     "time_limit_seconds":300,"difficulty_multiplier":1.5,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":30},
         "three":{"compliance_min":0.95,"time_remaining_min":90,"score_min":420}}},
    {"id":"five-alive","name":"Five Alive",
     "requires":None,
     "description":"Write 120 words of exactly 5 letters each. Six minutes.",
     "constraints":[{"type":"wordLength","exact":5}],
     "goal":{"type":"word_count","target":120},
     "time_limit_seconds":360,"difficulty_multiplier":1.5,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":30},
         "three":{"compliance_min":0.95,"time_remaining_min":90,"score_min":900}}},
    {"id":"alphabet-run","name":"Alphabet Run",
     "requires":None,
     "description":"Write one full A-to-Z alphabet cycle (26 words). Three minutes.",
     "constraints":[_AC],
     "goal":{"type":"word_count","target":26},
     "time_limit_seconds":180,"difficulty_multiplier":2.0,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":30},
         "three":{"compliance_min":1.00,"time_remaining_min":60,"score_min":220}}},
    {"id":"double-alphabet","name":"Double Alphabet",
     "requires":"alphabet-run",
     "description":"Two full A-to-Z cycles (52 words). Five minutes.",
     "constraints":[_AC],
     "goal":{"type":"word_count","target":52},
     "time_limit_seconds":300,"difficulty_multiplier":2.0,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":30},
         "three":{"compliance_min":1.00,"time_remaining_min":90,"score_min":500}}},
    {"id":"no-repeats","name":"No Repeats",
     "requires":None,
     "description":"Write 200 words without reusing any root word. Eight minutes.",
     "constraints":[{"type":"noRepeat","contentOnly":True}],
     "goal":{"type":"word_count","target":200},
     "time_limit_seconds":480,"difficulty_multiplier":1.5,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":60},
         "three":{"compliance_min":0.95,"time_remaining_min":120,"score_min":1200}}},
    {"id":"pangram-dash","name":"Pangram Dash",
     "requires":None,
     "description":"Use every letter of the alphabet within 50 words. Write 100 total. Four minutes.",
     "constraints":[{"type":"pangram","withinWords":50}],
     "goal":{"type":"word_count","target":100},
     "time_limit_seconds":240,"difficulty_multiplier":1.5,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":30},
         "three":{"compliance_min":0.95,"time_remaining_min":60,"score_min":500}}},
    {"id":"letter-budget","name":"Letter Budget",
     "requires":None,
     "description":"Each starting letter may only begin 3 words. Write 150. Six minutes.",
     "constraints":[{"type":"startLetterMax","max":3}],
     "goal":{"type":"word_count","target":150},
     "time_limit_seconds":360,"difficulty_multiplier":1.25,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":30},
         "three":{"compliance_min":0.95,"time_remaining_min":90,"score_min":550}}},
    {"id":"short-and-sweet","name":"Short and Sweet",
     "requires":"threes-company",
     "description":"Write 80 real 3-letter words. Four minutes.",
     "constraints":[{"type":"wordLength","exact":3},{"type":"dictCheck"}],
     "goal":{"type":"word_count","target":80},
     "time_limit_seconds":240,"difficulty_multiplier":1.5,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":30},
         "three":{"compliance_min":0.95,"time_remaining_min":60,"score_min":360}}},
    {"id":"verbose","name":"Verbose",
     "requires":"five-alive",
     "description":"Write 60 words of exactly 7 letters each. Five minutes.",
     "constraints":[{"type":"wordLength","exact":7}],
     "goal":{"type":"word_count","target":60},
     "time_limit_seconds":300,"difficulty_multiplier":1.5,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":30},
         "three":{"compliance_min":0.95,"time_remaining_min":90,"score_min":600}}},
    {"id":"marathon","name":"Marathon",
     "requires":"no-repeats",
     "description":"Write 300 unique real words (no root repeats). Twelve minutes.",
     "constraints":[{"type":"noRepeat","contentOnly":True},{"type":"dictCheck"}],
     "goal":{"type":"word_count","target":300},
     "time_limit_seconds":720,"difficulty_multiplier":1.5,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":60},
         "three":{"compliance_min":0.95,"time_remaining_min":180,"score_min":2200}}},
    {"id":"tight-alphabet","name":"Tight Alphabet",
     "requires":"double-alphabet",
     "description":"Two alphabet cycles — every word must be a real dictionary word. Four minutes.",
     "constraints":[_AC, {"type":"dictCheck"}],
     "goal":{"type":"word_count","target":52},
     "time_limit_seconds":240,"difficulty_multiplier":2.0,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":30},
         "three":{"compliance_min":1.00,"time_remaining_min":60,"score_min":500}}},
    {"id":"gauntlet-lite","name":"Gauntlet Lite",
     "requires":"four-letter-sprint",
     "description":"100 unique real 4-letter words. Six minutes.",
     "constraints":[{"type":"wordLength","exact":4},
                    {"type":"noRepeat","contentOnly":True},
                    {"type":"dictCheck"}],
     "goal":{"type":"word_count","target":100},
     "time_limit_seconds":360,"difficulty_multiplier":2.25,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":30},
         "three":{"compliance_min":0.95,"time_remaining_min":90,"score_min":800}}},
    {"id":"the-gauntlet","name":"The Gauntlet",
     "requires":"gauntlet-lite",
     "description":"150 words: 4 letters, alphabet cycle, no repeats. Ten minutes.",
     "constraints":[{"type":"wordLength","exact":4},
                    _AC,
                    {"type":"noRepeat","contentOnly":True}],
     "goal":{"type":"word_count","target":150},
     "time_limit_seconds":600,"difficulty_multiplier":4.5,
     "star_thresholds":{
         "one":  {"compliance_min":0.70},
         "two":  {"compliance_min":0.85,"time_remaining_min":60},
         "three":{"compliance_min":0.95,"time_remaining_min":180,"score_min":2500}}},
]

GAME_SA_PRESETS = [
    {"id":"sa-blitz","name":"Blitz",
     "desc":"4-letter words, 2 minutes. Fast and focused.",
     "constraints":[{"type":"wordLength","exact":4}],
     "default_duration":120},
    {"id":"sa-endurance","name":"Endurance",
     "desc":"No repeats + real words. How far can you go?",
     "constraints":[{"type":"noRepeat","contentOnly":True},{"type":"dictCheck"}],
     "default_duration":None},
    {"id":"sa-alpha-grind","name":"Alphabet Grind",
     "desc":"Alphabet cycle + real words, endless.",
     "constraints":[_AC, {"type":"dictCheck"}],
     "default_duration":None},
    {"id":"sa-word-hoarder","name":"Word Hoarder",
     "desc":"5-letter words + pangram in 100. 5 minutes.",
     "constraints":[{"type":"wordLength","exact":5},{"type":"pangram","withinWords":100}],
     "default_duration":300},
    {"id":"sa-freeform","name":"Free Attack",
     "desc":"No constraints — pure scoring on vocabulary richness.",
     "constraints":[],
     "default_duration":300},
]

# ═══════════════════════════════════════════════════════════════════
# CONSTRAINT ENGINE
# ═══════════════════════════════════════════════════════════════════

def clean_word(w: str) -> str:
    return re.sub(r'[^a-zA-Z]', '', w).lower()

def get_words(text: str) -> list:
    return [w for w in text.strip().split() if w]

def cycle_alpha(skip_x: bool) -> list:
    return [l for l in ALPHABET if not (skip_x and l == 'x')]

def get_lemma(word: str) -> str:
    word = word.lower()
    if word in LEMMA_CACHE:
        return LEMMA_CACHE[word]
    if SPACY_AVAILABLE and NLP is not None:
        doc = NLP(word)
        lemma = doc[0].lemma_.lower() if doc else word
    else:
        lemma = word
    LEMMA_CACHE[word] = lemma
    return lemma

def check_dictionary(word: str) -> bool:
    if not WORDLIST:
        return True
    return clean_word(word) in WORDLIST

def score_readability_label(score: float) -> str:
    if score >= 80: return "easy"
    if score >= 60: return "standard"
    if score >= 40: return "difficult"
    return "very difficult"

def constraints_summary(constraints: list) -> str:
    parts = []
    for c in constraints:
        t = c['type']
        if t == 'wordLength':      parts.append(f"{c['exact']}-letter words")
        elif t == 'alphaCycle':    parts.append("alphabet cycle")
        elif t == 'wordGoal':      parts.append(f"{c['target']} words")
        elif t == 'timeLimit':     parts.append(f"{c['seconds']//60} min")
        elif t == 'startLetterMax':parts.append(f"max {c['max']}/letter")
        elif t == 'pangram':       parts.append(f"pangram/{c['withinWords']}")
        elif t == 'noRepeat':      parts.append("no repeats")
        elif t == 'dictCheck':     parts.append("dict check")
    return " · ".join(parts) if parts else "no constraints"

def deep_analyze(text: str) -> dict:
    result = {
        'repeated_lemmas': {}, 'unknown_words': [],
        'readability': {}, 'lemma_richness': None,
        'content_word_count': 0,
    }
    words_raw = [w for w in text.split() if w]
    if not words_raw or len(words_raw) < 3:
        return result

    if WORDLIST:
        result['unknown_words'] = [
            w for w in words_raw
            if clean_word(w) and not check_dictionary(clean_word(w))
        ]

    if TEXTSTAT_AVAILABLE:
        try:
            result['readability'] = {
                'flesch_ease':    round(_textstat.flesch_reading_ease(text), 1),
                'flesch_kincaid': round(_textstat.flesch_kincaid_grade(text), 1),
                'gunning_fog':    round(_textstat.gunning_fog(text), 1),
                'avg_word_len':   round(
                    sum(len(clean_word(w)) for w in words_raw if clean_word(w))
                    / max(1, len([w for w in words_raw if clean_word(w)])), 1),
            }
        except Exception:
            # pyphen (textstat dependency) fails inside Nuitka binaries due to
            # resource-loading incompatibility -- degrade gracefully.
            pass

    if not SPACY_AVAILABLE or NLP is None:
        return result

    CONTENT_POS = {'NOUN', 'VERB', 'ADJ', 'ADV'}
    doc = NLP(text)
    content_tokens = [
        (token.text, token.lemma_.lower(), token.pos_)
        for token in doc
        if token.pos_ in CONTENT_POS and not token.is_stop
        and not token.is_punct and token.is_alpha
    ]
    if content_tokens:
        unique_lemmas = {lemma for _, lemma, _ in content_tokens}
        result['lemma_richness']     = round(len(unique_lemmas)/len(content_tokens), 3)
        result['content_word_count'] = len(content_tokens)
    lemma_map: dict = {}
    for word, lemma, _ in content_tokens:
        lemma_map.setdefault(lemma, []).append(word)
    result['repeated_lemmas'] = {k: v for k, v in lemma_map.items() if len(v) > 1}
    return result


def analyze_text(text: str, constraints: list, elapsed: int) -> dict:
    raw_words   = get_words(text)
    words       = [clean_word(w) for w in raw_words]
    words       = [w for w in words if w]
    word_count  = len(words)
    minutes     = elapsed / 60
    wpm         = round(word_count / minutes) if minutes > 0.1 else 0

    violations:    list = []
    letter_counts: dict = {}
    used_letters:  set  = set()
    seen_lemmas:   dict = {}

    wl      = next((c for c in constraints if c['type'] == 'wordLength'),     None)
    cyc     = next((c for c in constraints if c['type'] == 'alphaCycle'),     None)
    sl_max  = next((c for c in constraints if c['type'] == 'startLetterMax'), None)
    pangram = next((c for c in constraints if c['type'] == 'pangram'),        None)
    goal_c  = next((c for c in constraints if c['type'] == 'wordGoal'),       None)
    no_rep  = next((c for c in constraints if c['type'] == 'noRepeat'),       None)
    dict_c  = next((c for c in constraints if c['type'] == 'dictCheck'),      None)

    alpha = cycle_alpha(cyc.get('skipX', False)) if cyc else []

    for i, word in enumerate(words):
        if not word:
            continue
        first = word[0]
        letter_counts[first] = letter_counts.get(first, 0) + 1
        for ch in word:
            used_letters.add(ch)
        raw = raw_words[i] if i < len(raw_words) else word

        if wl and wl.get('exact') and len(word) != wl['exact']:
            violations.append({
                'word_index': i, 'word': raw, 'type': 'wordLength',
                'message': f'"{raw}" is {len(word)} letters (need {wl["exact"]})',
                'colour': RED})

        if cyc and alpha:
            expected   = alpha[i % len(alpha)]
            x_optional = cyc.get('xOptional', True)
            if not (expected == 'x' and x_optional) and first != expected:
                violations.append({
                    'word_index': i, 'word': raw, 'type': 'alphaCycle',
                    'message': f'Word {i+1}: expected "{expected.upper()}", got "{first.upper()}"',
                    'colour': RED})

        if sl_max and letter_counts[first] > sl_max['max']:
            violations.append({
                'word_index': i, 'word': raw, 'type': 'startLetterMax',
                'message': f'"{first.upper()}" used {letter_counts[first]}x (max {sl_max["max"]})',
                'colour': RED})

        if no_rep:
            skip = no_rep.get('contentOnly', True) and word in FUNCTION_WORDS
            if not skip:
                lemma = get_lemma(word)
                if lemma in seen_lemmas and seen_lemmas[lemma] != raw:
                    violations.append({
                        'word_index': i, 'word': raw, 'type': 'noRepeat',
                        'message': f'"{raw}" repeats "{seen_lemmas[lemma]}" (same root)',
                        'colour': AMBER})
                else:
                    seen_lemmas[lemma] = raw

        if dict_c and WORDLIST and not check_dictionary(word):
            violations.append({
                'word_index': i, 'word': raw, 'type': 'dictCheck',
                'message': f'"{raw}" not found in dictionary',
                'colour': BLUE})

    pang_progress = None
    if pangram:
        window      = words[:pangram['withinWords']]
        window_used = {ch for w in window for ch in w}
        pang_progress = {
            'window_missing': [l for l in ALPHABET if l not in window_used],
            'all_missing':    [l for l in ALPHABET if l not in used_letters],
            'target':          pangram['withinWords']}

    goal_progress = (
        {'current': word_count, 'target': goal_c['target']} if goal_c else None)

    next_expected = None
    if cyc and alpha:
        nxt = alpha[word_count % len(alpha)]
        next_expected = ('X*' if nxt == 'x' and cyc.get('xOptional', True)
                         else nxt.upper())

    structural_types = {'wordLength', 'alphaCycle', 'startLetterMax', 'noRepeat'}
    sv   = [v for v in violations if v['type'] in structural_types]
    compliance = (
        max(0, round(((word_count - len(sv)) / word_count) * 100))
        if word_count > 0 else 100)

    return {
        'word_count': word_count, 'wpm': wpm,
        'violations': violations, 'compliance': compliance,
        'letter_counts': letter_counts, 'used_letters': used_letters,
        'pang_progress': pang_progress, 'goal_progress': goal_progress,
        'next_expected': next_expected,
    }


def check_feasibility(constraints: list) -> list:
    warnings = []
    wl     = next((c for c in constraints if c['type'] == 'wordLength'),     None)
    goal   = next((c for c in constraints if c['type'] == 'wordGoal'),       None)
    time_c = next((c for c in constraints if c['type'] == 'timeLimit'),      None)
    sl_max = next((c for c in constraints if c['type'] == 'startLetterMax'), None)
    cyc    = next((c for c in constraints if c['type'] == 'alphaCycle'),     None)
    no_rep = next((c for c in constraints if c['type'] == 'noRepeat'),       None)

    if wl and wl.get('exact'):
        n = wl['exact']
        avail = WORDS_PER_LENGTH.get(n, 0)
        if avail == 0:
            warnings.append({'level':'error',
                'msg': f'No common English words of exactly {n} letters.'})
        elif avail < 200:
            warnings.append({'level':'warn',
                'msg': f'Only ~{avail} words of length {n} — very limited.'})

    if goal and sl_max:
        ceiling = sl_max['max'] * 26
        if goal['target'] > ceiling:
            warnings.append({'level':'error',
                'msg': (f'Impossible: {goal["target"]} words but ceiling is '
                        f'{ceiling} ({sl_max["max"]} per letter).')})

    if goal and time_c:
        req_wpm = round(goal['target'] / (time_c['seconds'] / 60))
        if req_wpm > 120:
            warnings.append({'level':'error',
                'msg': f'Requires {req_wpm} WPM — near-impossible.'})
        elif req_wpm > 80:
            warnings.append({'level':'warn',
                'msg': f'Requires {req_wpm} WPM — fast typist territory.'})

    if cyc and not cyc.get('skipX') and not cyc.get('xOptional'):
        warnings.append({'level':'warn',
            'msg': 'X is very rare as a word-starter. Consider making it optional.'})

    if cyc and wl and wl.get('exact') == 3:
        warnings.append({'level':'warn',
            'msg': 'Cycle + 3-letter words: Q, X, Z have very few options.'})

    if no_rep and goal and goal['target'] > 500:
        warnings.append({'level':'warn',
            'msg': f'No-repeat + {goal["target"]} words is very demanding.'})

    return warnings


def fmt_time(s: int) -> str:
    return f"{s // 60}:{s % 60:02d}"


# ═══════════════════════════════════════════════════════════════════
# GAME ENGINE
# ═══════════════════════════════════════════════════════════════════

_CONSTRAINT_DIFF = {
    'dictCheck': 1.0, 'wordLength': 1.5, 'alphaCycle': 2.0,
    'noRepeat': 1.5, 'startLetterMax': 1.25, 'pangram': 1.5,
}

def compute_difficulty_mult(constraints: list) -> float:
    active = [c for c in constraints
              if c['type'] not in ('wordGoal', 'timeLimit')]
    if not active:
        return 1.0
    mult = 1.0
    for c in active:
        mult *= _CONSTRAINT_DIFF.get(c['type'], 1.0)
    return min(5.0, round(mult, 2))


class GameScorer:
    _STREAK_TIERS = [(100, 4.0), (50, 3.0), (25, 2.0), (10, 1.5), (0, 1.0)]

    def __init__(self, difficulty: str, constraints: list,
                 preset_mult: float = None):
        self.difficulty  = difficulty
        self.diff_mult   = (preset_mult if preset_mult is not None
                            else compute_difficulty_mult(constraints))
        self.streak      = 0
        self.peak_streak = 0
        self.peak_mult   = 1.0
        self.score       = 0.0
        self.total_words = 0
        self.compliant_words = 0
        self._consec_viols   = 0
        self._last_viol_time = 0.0

    def streak_mult(self) -> float:
        for threshold, m in self._STREAK_TIERS:
            if self.streak >= threshold:
                return m
        return 1.0

    def score_word(self, word: str, compliant: bool,
                   now: float = None) -> float:
        if now is None:
            now = time.monotonic()
        self.total_words += 1
        if compliant:
            self.streak      += 1
            self.compliant_words += 1
            self.peak_streak  = max(self.peak_streak, self.streak)
            self.peak_mult    = max(self.peak_mult, self.streak_mult())
            self._consec_viols = 0
            base   = len(clean_word(word))
            pts    = base * self.diff_mult * self.streak_mult() * \
                     WORD_RARITY.get(word.lower(), 1.0)
            self.score += pts
            return pts
        else:
            self.streak = 0
            if now - self._last_viol_time > 30:
                self._consec_viols = 0
            self._consec_viols   += 1
            self._last_viol_time  = now
            deduction = 0.0
            if self.difficulty == 'medium':
                deduction = 5.0
            elif self.difficulty == 'hard':
                deduction = min(5.0 * (2 ** (self._consec_viols - 1)), 40.0)
            self.score = max(0.0, self.score - deduction)
            return -deduction

    @property
    def compliance(self) -> float:
        return (self.compliant_words / self.total_words
                if self.total_words else 1.0)

    def int_score(self) -> int:
        return int(self.score)


def load_scores() -> dict:
    ensure_app_dir()
    if not os.path.exists(SCORES_FILE):
        return {"challenges": {}, "score_attack": {}}
    try:
        with open(SCORES_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"challenges": {}, "score_attack": {}}


def save_scores(data: dict):
    ensure_app_dir()
    try:
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: could not save scores: {e}")


def challenge_has_star(cid: str) -> bool:
    """Return True if challenge has at least 1 ★ completion (any difficulty)."""
    data = load_scores()
    diffs = data.get("challenges", {}).get(cid, {})
    for entries in diffs.values():
        for e in entries:
            if e.get('stars', 0) >= 1:
                return True
    return False


def get_unlocked_challenges() -> set:
    """Return set of challenge IDs that are currently accessible."""
    unlocked = set()
    for ch in GAME_CHALLENGES:
        req = ch.get('requires')
        if req is None or challenge_has_star(req):
            unlocked.add(ch['id'])
    return unlocked


def append_score(data: dict, category: str, key: str,
                 difficulty: str, entry: dict):
    """Append entry to scores data, capping at 100 per bucket."""
    data.setdefault(category, {}).setdefault(key, {}).setdefault(difficulty, [])
    bucket = data[category][key][difficulty]
    bucket.append(entry)
    bucket.sort(key=lambda x: x['score'], reverse=True)
    if len(bucket) > 100:
        del bucket[100:]


def eval_stars(ch: dict, compliance: float, time_remaining: int,
               score: int) -> int:
    th = ch.get('star_thresholds', {})
    stars = 0
    if compliance >= th.get('one', {}).get('compliance_min', 1.0):
        stars = 1
    two = th.get('two', {})
    if (stars >= 1
            and compliance >= two.get('compliance_min', 1.0)
            and time_remaining >= two.get('time_remaining_min', 0)):
        stars = 2
    three = th.get('three', {})
    if (stars >= 2
            and compliance >= three.get('compliance_min', 1.0)
            and time_remaining >= three.get('time_remaining_min', 0)
            and score >= three.get('score_min', 0)):
        stars = 3
    return stars


# ═══════════════════════════════════════════════════════════════════
# APPLICATION
# ═══════════════════════════════════════════════════════════════════

class ConstrainedApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TETHER  v0.3.2")
        self.root.configure(bg=BG)
        self.root.geometry("1200x760")
        self.root.minsize(880, 560)

        # Persistent state (loaded from disk)
        self.history: list      = load_history()
        self.user_presets: list = load_user_presets()

        # Session state
        self.active_preset      = BUILTIN_PRESETS[0]
        self.custom_constraints = None
        self.text_content       = ""
        self.session_started    = False
        self.elapsed            = 0
        self.timer_target       = None
        self.timer_running      = False
        self.analysis: dict     = self._empty_analysis()
        self.deep: dict         = {}

        # Game mode state
        self._game_mode          = "write"      # "write" | "game"
        self._game_submode       = "challenge"  # "challenge" | "scoreattack"
        self._game_difficulty    = "medium"     # "easy" | "medium" | "hard"
        self._game_state         = "idle"       # "idle"|"countdown"|"active"|"done"
        self._game_scorer: GameScorer | None = None
        self._game_challenge     = None         # selected challenge dict
        self._game_sa_preset     = None         # selected SA preset dict
        self._game_sa_timed      = True         # timed vs endless (SA)
        self._game_sa_duration   = 300          # seconds (SA timed)
        self._game_start_mono    = 0.0
        self._game_elapsed       = 0            # integer seconds
        self._game_time_limit    = None         # int seconds or None
        self._game_last_wc       = 0            # word count at last scoring
        self._game_timer_job     = None
        self._game_feedback_job  = None   # pending root.after for feedback clear
        self._game_streak_prev   = 0      # track prev streak to detect resets
        self._game_unlocked      = get_unlocked_challenges()

        # Builder vars
        self.b = {
            'wl_on':      tk.BooleanVar(value=False),
            'wl_n':       tk.IntVar(value=4),
            'ac_on':      tk.BooleanVar(value=False),
            'ac_skipx':   tk.BooleanVar(value=False),
            'ac_xopt':    tk.BooleanVar(value=True),
            'wg_on':      tk.BooleanVar(value=False),
            'wg_n':       tk.IntVar(value=500),
            'tl_on':      tk.BooleanVar(value=False),
            'tl_mins':    tk.IntVar(value=10),
            'sl_on':      tk.BooleanVar(value=False),
            'sl_n':       tk.IntVar(value=30),
            'pg_on':      tk.BooleanVar(value=False),
            'pg_n':       tk.IntVar(value=100),
            'nr_on':      tk.BooleanVar(value=False),
            'nr_content': tk.BooleanVar(value=True),
            'dc_on':      tk.BooleanVar(value=False),
        }
        for v in self.b.values():
            v.trace_add('write', self._on_builder_change)

        self._build_ui()
        self._show_view("editor")
        self._start_update_check()
        if not onboarding_seen():
            self.root.after(600, self._show_onboarding)

    # ─────────────────────────────────────────────────────────────
    # PRESET HELPERS
    # ─────────────────────────────────────────────────────────────

    def _all_presets(self) -> list:
        return BUILTIN_PRESETS + self.user_presets

    def _find_preset(self, pid: str) -> dict | None:
        return next((p for p in self._all_presets() if p['id'] == pid), None)

    # ─────────────────────────────────────────────────────────────
    # UI CONSTRUCTION
    # ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self.root, bg=BG2, height=52)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        tk.Label(hdr, text="TETHER", fg=ACCENT, bg=BG2,
                 font=("Courier New", 14, "bold")).pack(side=tk.LEFT, padx=20)
        tk.Label(hdr, text="typing constraint engine", fg=DIM2, bg=BG2,
                 font=SERIF_SM).pack(side=tk.LEFT, padx=(0, 24))

        self.hdr_timer = tk.Label(hdr, text="", fg=DIM, bg=BG2,
                                   font=("Courier New", 20))
        self.hdr_timer.pack(side=tk.LEFT)

        nav = tk.Frame(hdr, bg=BG2)
        nav.pack(side=tk.RIGHT, padx=16)
        self.nav_btns = {}
        for v, label in [("editor","✎ Editor"),
                          ("history","◷ History"),
                          ("builder","⊞ Builder")]:
            b = tk.Button(nav, text=label, bg=BG2, fg=DIM, relief=tk.FLAT,
                          font=("Courier New", 9), padx=12, pady=7,
                          cursor="hand2", activebackground=BG2, bd=0,
                          command=lambda v=v: self._show_view(v))
            b.pack(side=tk.LEFT, padx=2)
            self.nav_btns[v] = b

        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill=tk.BOTH, expand=True)

        # Update notification banner (hidden until needed)
        self._update_banner = tk.Frame(self.root, bg="#1a1a0a")
        self._update_lbl    = tk.Label(
            self._update_banner, text="", fg=AMBER, bg="#1a1a0a",
            font=("Courier New", 9), pady=4)
        self._update_lbl.pack(side=tk.LEFT, padx=16)
        tk.Button(
            self._update_banner, text="✕", fg=DIM, bg="#1a1a0a",
            relief=tk.FLAT, font=("Courier New", 9), bd=0,
            activebackground="#1a1a0a", cursor="hand2",
            command=lambda: self._update_banner.pack_forget()
        ).pack(side=tk.RIGHT, padx=8)

        self._build_editor_view()
        self._build_history_view()
        self._build_builder_view()

    # ── EDITOR ────────────────────────────────────────────────────

    def _build_editor_view(self):
        self.editor_frame = tk.Frame(self.body, bg=BG)

        sb = tk.Frame(self.editor_frame, bg=BG2, width=222)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        sb.pack_propagate(False)

        # Write / Game mode toggle
        _tog = tk.Frame(sb, bg=BG2)
        _tog.pack(fill=tk.X, padx=6, pady=(6, 2))
        self._wb = tk.Button(_tog, text="WRITE", bg=ACCENT, fg="#000",
            relief=tk.FLAT, font=("Courier New", 8, "bold"), pady=3, bd=0,
            cursor="hand2", activeforeground="#000", activebackground=ACCENT,
            command=lambda: self._game_toggle_mode("write"))
        self._wb.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 1))
        self._gb = tk.Button(_tog, text="GAME", bg=BG3, fg=DIM,
            relief=tk.FLAT, font=("Courier New", 8, "bold"), pady=3, bd=0,
            cursor="hand2", activeforeground=GAME_ACC, activebackground=BG3,
            command=lambda: self._game_toggle_mode("game"))
        self._gb.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(1, 0))

        # Write mode sidebar (scrollable canvas)
        self._write_sb_frame = tk.Frame(sb, bg=BG2)
        self._write_sb_frame.pack(fill=tk.BOTH, expand=True)

        self._sb_canvas = tk.Canvas(self._write_sb_frame, bg=BG2,
                                    highlightthickness=0)
        sb_scroll = tk.Scrollbar(self._write_sb_frame, orient=tk.VERTICAL,
                                  command=self._sb_canvas.yview,
                                  bg=BG2, troughcolor=BG2)
        self._sb_canvas.configure(yscrollcommand=sb_scroll.set)
        sb_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._sb_canvas.pack(fill=tk.BOTH, expand=True)

        self._sb_inner = tk.Frame(self._sb_canvas, bg=BG2)
        self._sb_win   = self._sb_canvas.create_window(
            (0, 0), window=self._sb_inner, anchor=tk.NW)
        self._sb_inner.bind("<Configure>",
            lambda e: self._sb_canvas.configure(
                scrollregion=self._sb_canvas.bbox("all")))
        self._sb_canvas.bind("<Configure>",
            lambda e: self._sb_canvas.itemconfig(
                self._sb_win, width=e.width))

        def _mw(event):
            self._sb_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self._sb_canvas.bind_all("<MouseWheel>", _mw)

        # Game mode sidebar (initially hidden, built after _build_sidebar_contents)
        self._game_sb_frame = tk.Frame(sb, bg=GAME_BG)

        self._build_sidebar_contents()
        self._build_game_sidebar()

        main = tk.Frame(self.editor_frame, bg=BG)
        main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ctx = tk.Frame(main, bg=BG2)
        ctx.pack(fill=tk.X)
        self.ctx_lbl = tk.Label(ctx, text="", fg="#888", bg=BG2,
                                 font=SERIF_SM, anchor=tk.W)
        self.ctx_lbl.pack(side=tk.LEFT, padx=16, pady=7)
        btn_row = tk.Frame(ctx, bg=BG2)
        btn_row.pack(side=tk.RIGHT, padx=8)
        for txt, cmd, col in [
            ("↺ Reset",  self._reset_session, DIM),
            ("◼ Save",   self._save_session,  GREEN),
            ("↓ Export", self._export_txt,    BLUE),
        ]:
            tk.Button(btn_row, text=txt, fg=col, bg=BG2, relief=tk.FLAT,
                      font=("Courier New", 8), padx=10, pady=5,
                      cursor="hand2", bd=0, activebackground=BG2,
                      command=cmd).pack(side=tk.LEFT, padx=2)

        self.warn_frame   = tk.Frame(main, bg=BG)
        self.warn_frame.pack(fill=tk.X)
        self.warn_widgets: list = []

        self.text_widget = tk.Text(
            main, bg=BG, fg=TEXT, insertbackground=ACCENT,
            relief=tk.FLAT, font=("Courier New", 15), padx=48, pady=36,
            wrap=tk.WORD, spacing1=3, spacing3=3,
            selectbackground="#252530", selectforeground=TEXT,
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        self.text_widget.bind('<KeyRelease>', self._on_key_release)
        self.text_widget.bind('<KeyPress>',   self._on_key_press)

        self.viol_frame = tk.Frame(main, bg=BG2)
        self.viol_text  = tk.Text(
            self.viol_frame, bg=BG2, fg=RED,
            font=("Courier New", 9), height=5, relief=tk.FLAT,
            padx=14, pady=6, state=tk.DISABLED
        )
        self.viol_text.pack(fill=tk.X)
        self.viol_text.tag_configure('amber', foreground=AMBER)
        self.viol_text.tag_configure('blue',  foreground=BLUE)
        self.viol_text.tag_configure('red',   foreground=RED)

    def _build_sidebar_contents(self):
        """Build/rebuild all sidebar widgets. Called on init and when presets change."""
        for w in self._sb_inner.winfo_children():
            w.destroy()
        self.preset_rows: dict = {}
        self.stat_vars:   dict = {}
        self.lang_vars:   dict = {}

        sb = self._sb_inner

        # Built-in modes
        self._sb_label(sb, "MODES")
        for p in BUILTIN_PRESETS:
            self._make_preset_row(sb, p, deletable=False)

        # User presets
        if self.user_presets:
            tk.Frame(sb, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=4)
            self._sb_label(sb, "MY PRESETS")
            for p in self.user_presets:
                self._make_preset_row(sb, p, deletable=True)

        # Stats
        tk.Frame(sb, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)
        self._sb_label(sb, "STATS")
        for key, label in [
            ('word_count','Words'), ('wpm','WPM'),
            ('compliance','Comply'), ('violations','Violations'), ('time','Time')
        ]:
            row = tk.Frame(sb, bg=BG2)
            row.pack(fill=tk.X, padx=12, pady=2)
            tk.Label(row, text=label, fg=DIM2, bg=BG2,
                     font=("Courier New", 8)).pack(side=tk.LEFT)
            sv  = tk.StringVar(value="0")
            lbl = tk.Label(row, textvariable=sv, fg=DIM, bg=BG2,
                           font=("Courier New", 12))
            lbl.pack(side=tk.RIGHT)
            self.stat_vars[key] = (sv, lbl)

        self.goal_bar_frame  = self._sb_bar_section(sb, "Word goal")
        self.timer_bar_frame = self._sb_bar_section(sb, "Time")

        # Next letter
        tk.Frame(sb, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)
        self._sb_label(sb, "NEXT LETTER")
        self.next_ltr_var = tk.StringVar(value="")
        self.next_ltr_lbl = tk.Label(sb, textvariable=self.next_ltr_var,
                                      fg=ACCENT, bg=BG2,
                                      font=("Courier New", 32, "bold"))
        self.next_ltr_lbl.pack(pady=(2, 0))
        self.next_ltr_sub = tk.Label(sb, text="", fg=DIM2, bg=BG2,
                                      font=("Courier New", 8))
        self.next_ltr_sub.pack()

        # Pangram
        tk.Frame(sb, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)
        self._sb_label(sb, "PANGRAM — MISSING")
        self.pang_var = tk.StringVar(value="")
        tk.Label(sb, textvariable=self.pang_var, fg=AMBER, bg=BG2,
                 font=("Courier New", 10), wraplength=198,
                 justify=tk.LEFT).pack(anchor=tk.W, padx=12, pady=(0, 4))

        # Language
        tk.Frame(sb, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)
        self._sb_label(sb, "LANGUAGE")
        for key, label in [
            ('richness','Richness'), ('repeats','Repeats'),
            ('unknown','Unknown'), ('flesch','Readability'),
            ('grade','Grade level'), ('fog','Fog index'),
            ('avg_wl','Avg word len'),
        ]:
            row = tk.Frame(sb, bg=BG2)
            row.pack(fill=tk.X, padx=12, pady=1)
            tk.Label(row, text=label, fg=DIM2, bg=BG2,
                     font=("Courier New", 8)).pack(side=tk.LEFT)
            sv  = tk.StringVar(value="—")
            lbl = tk.Label(row, textvariable=sv, fg=DIM, bg=BG2,
                           font=("Courier New", 10))
            lbl.pack(side=tk.RIGHT)
            self.lang_vars[key] = (sv, lbl)

        notes = []
        if not SPACY_AVAILABLE:   notes.append("spaCy not found — richness N/A")
        if not TEXTSTAT_AVAILABLE:notes.append("textstat not found — readability N/A")
        if not WORDLIST:          notes.append("wordlist.txt missing")
        for n in notes:
            tk.Label(sb, text=n, fg=DIM2, bg=BG2,
                     font=("Courier New", 7),
                     justify=tk.CENTER).pack(pady=1)

        self._sb_canvas.configure(
            scrollregion=self._sb_canvas.bbox("all"))

    # ── GAME SIDEBAR ──────────────────────────────────────────────

    def _build_game_sidebar(self):
        """Build the game panel inside _game_sb_frame."""
        sb = self._game_sb_frame

        def glabel(parent, text, fg=None, font=None):
            kw = dict(fg=fg or DIM2, bg=GAME_BG,
                      font=font or ("Courier New", 8))
            tk.Label(parent, text=text, **kw).pack(
                anchor=tk.W, padx=10, pady=(5, 1))

        def gdiv():
            tk.Frame(sb, bg="#1e1a2e", height=1).pack(
                fill=tk.X, padx=6, pady=4)

        # ── Sub-mode toggle ──────────────────────────────────────
        sm = tk.Frame(sb, bg=GAME_BG)
        sm.pack(fill=tk.X, padx=6, pady=(6, 2))
        self._ch_btn = tk.Button(sm, text="CHALLENGE",
            bg=GAME_ACC, fg="#fff", relief=tk.FLAT,
            font=("Courier New", 8, "bold"), pady=3, bd=0, cursor="hand2",
            activeforeground="#fff", activebackground=GAME_ACC,
            command=lambda: self._game_set_submode("challenge"))
        self._ch_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,1))
        self._sa_btn = tk.Button(sm, text="SCORE ATTACK",
            bg=GAME_BG2, fg=DIM, relief=tk.FLAT,
            font=("Courier New", 8, "bold"), pady=3, bd=0, cursor="hand2",
            activeforeground=GAME_ACC, activebackground=GAME_BG2,
            command=lambda: self._game_set_submode("scoreattack"))
        self._sa_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(1,0))

        # ── Difficulty ───────────────────────────────────────────
        gdiv()
        glabel(sb, "DIFFICULTY")
        diff_row = tk.Frame(sb, bg=GAME_BG)
        diff_row.pack(fill=tk.X, padx=6, pady=(2, 2))
        self._diff_btns = {}
        for d, label in [("easy","Easy"),("medium","Med"),("hard","Hard")]:
            b = tk.Button(diff_row, text=label,
                bg=GAME_ACC if d == "medium" else GAME_BG2,
                fg="#fff" if d == "medium" else DIM,
                relief=tk.FLAT, font=("Courier New", 8), pady=2, bd=0,
                cursor="hand2",
                command=lambda d=d: self._game_set_difficulty(d))
            b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
            self._diff_btns[d] = b

        # ── Challenge list ────────────────────────────────────────
        self._ch_list_frame = tk.Frame(sb, bg=GAME_BG)
        self._ch_list_frame.pack(fill=tk.X)
        gdiv()
        glabel(self._ch_list_frame, "CHALLENGES")
        self._ch_rows = {}
        self._ch_sub_rows = {}   # sub-label for locked prerequisite hint
        for ch in GAME_CHALLENGES:
            locked = ch['id'] not in self._game_unlocked
            req_name = ""
            if locked and ch.get('requires'):
                req_ch = next((c for c in GAME_CHALLENGES if c['id'] == ch['requires']), None)
                req_name = req_ch['name'] if req_ch else ch['requires']
            row = tk.Frame(self._ch_list_frame, bg=GAME_BG,
                           cursor="" if locked else "hand2")
            row.pack(fill=tk.X)
            dot = tk.Label(row, text="🔒" if locked else "▪",
                           fg=DIM2 if locked else GAME_ACC, bg=GAME_BG,
                           font=("Courier New", 8), width=2)
            dot.pack(side=tk.LEFT, padx=(8, 0), anchor=tk.N, pady=4)
            name_col = tk.Frame(row, bg=GAME_BG)
            name_col.pack(side=tk.LEFT, padx=4, pady=2, fill=tk.X, expand=True)
            lbl = tk.Label(name_col, text=ch['name'],
                           fg=DIM2 if locked else DIM, bg=GAME_BG,
                           font=SERIF_SM, anchor=tk.W,
                           cursor="" if locked else "hand2")
            lbl.pack(anchor=tk.W)
            sub_lbl = None
            if locked and req_name:
                sub_lbl = tk.Label(name_col, text=f"beat {req_name} first",
                                   fg=DIM2, bg=GAME_BG,
                                   font=("Courier New", 7), anchor=tk.W)
                sub_lbl.pack(anchor=tk.W)
            if not locked:
                for w in (row, dot, name_col, lbl):
                    w.bind("<Button-1>",
                        lambda e, c=ch: self._game_select_challenge(c))
            self._ch_rows[ch['id']] = (row, lbl, dot)
            self._ch_sub_rows[ch['id']] = sub_lbl

        # ── Score Attack preset list ──────────────────────────────
        self._sa_list_frame = tk.Frame(sb, bg=GAME_BG)
        glabel(self._sa_list_frame, "PRESET")
        self._sa_rows = {}
        for p in GAME_SA_PRESETS:
            row = tk.Frame(self._sa_list_frame, bg=GAME_BG, cursor="hand2")
            row.pack(fill=tk.X)
            dot = tk.Label(row, text="▪", fg=BLUE, bg=GAME_BG,
                           font=("Courier New", 8), width=2)
            dot.pack(side=tk.LEFT, padx=(8, 0))
            lbl = tk.Label(row, text=p['name'], fg=DIM, bg=GAME_BG,
                           font=SERIF_SM, anchor=tk.W, cursor="hand2")
            lbl.pack(side=tk.LEFT, padx=4, pady=4, fill=tk.X, expand=True)
            for w in (row, dot, lbl):
                w.bind("<Button-1>",
                    lambda e, pr=p: self._game_select_sa_preset(pr))
            self._sa_rows[p['id']] = (row, lbl, dot)

        # SA duration selector (inside sa_list_frame)
        self._sa_dur_frame = tk.Frame(self._sa_list_frame, bg=GAME_BG)
        self._sa_dur_frame.pack(fill=tk.X, padx=8, pady=(4, 2))
        glabel(self._sa_dur_frame, "DURATION")
        dur_row = tk.Frame(self._sa_dur_frame, bg=GAME_BG)
        dur_row.pack(fill=tk.X)
        self._sa_dur_btns = {}
        for secs, label in [(120,"2m"),(300,"5m"),(600,"10m"),(0,"∞")]:
            b = tk.Button(dur_row, text=label,
                bg=GAME_ACC if secs == 300 else GAME_BG2,
                fg="#fff" if secs == 300 else DIM,
                relief=tk.FLAT, font=("Courier New", 8), pady=2, bd=0,
                cursor="hand2",
                command=lambda s=secs: self._game_set_duration(s))
            b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
            self._sa_dur_btns[secs] = b

        # ── Challenge info panel (shown when a challenge is selected) ────
        self._game_ch_info_frame = tk.Frame(sb, bg=GAME_BG)
        # Back button — returns to the challenge list
        tk.Button(self._game_ch_info_frame, text="← Back",
            bg=GAME_BG, fg=DIM, relief=tk.FLAT,
            font=("Courier New", 8), pady=3, bd=0, cursor="hand2",
            activeforeground=GAME_ACC, activebackground=GAME_BG,
            command=self._game_back_to_list).pack(anchor=tk.W, padx=6, pady=(4,0))
        self._ch_info_name_var = tk.StringVar(value="")
        tk.Label(self._game_ch_info_frame, textvariable=self._ch_info_name_var,
            fg="#fff", bg=GAME_BG, font=("Courier New", 11, "bold"),
            wraplength=200, justify=tk.LEFT).pack(anchor=tk.W, padx=10, pady=(4,2))
        self._ch_info_desc_var = tk.StringVar(value="")
        tk.Label(self._game_ch_info_frame, textvariable=self._ch_info_desc_var,
            fg=DIM, bg=GAME_BG, font=("Courier New", 8),
            wraplength=200, justify=tk.LEFT).pack(anchor=tk.W, padx=10, pady=(0,4))
        tk.Frame(self._game_ch_info_frame, bg="#1e1a2e", height=1).pack(
            fill=tk.X, padx=6, pady=2)
        self._ch_info_constr_var = tk.StringVar(value="")
        tk.Label(self._game_ch_info_frame, textvariable=self._ch_info_constr_var,
            fg=GAME_ACC, bg=GAME_BG, font=("Courier New", 8),
            wraplength=200, justify=tk.LEFT).pack(anchor=tk.W, padx=10, pady=(4,0))
        self._ch_info_goal_var = tk.StringVar(value="")
        tk.Label(self._game_ch_info_frame, textvariable=self._ch_info_goal_var,
            fg=DIM2, bg=GAME_BG, font=("Courier New", 8)).pack(
            anchor=tk.W, padx=10, pady=(2,4))
        self._game_ch_start_btn = tk.Button(self._game_ch_info_frame,
            text="▶  START CHALLENGE",
            bg=GAME_ACC, fg="#fff", relief=tk.FLAT,
            font=("Courier New", 10, "bold"), pady=6, bd=0,
            cursor="hand2", activeforeground="#fff",
            activebackground="#6d28d9",
            command=self._game_start_countdown)
        self._game_ch_start_btn.pack(fill=tk.X, padx=8, pady=(4,8))

        # ── Start button (Score Attack) ───────────────────────────
        self._game_pre_start_div = tk.Frame(sb, bg="#1e1a2e", height=1)
        # not packed — _game_lb_div is the layout anchor
        self._game_start_btn = tk.Button(sb, text="▶  START",
            bg=GAME_ACC, fg="#fff", relief=tk.FLAT,
            font=("Courier New", 10, "bold"), pady=6, bd=0,
            cursor="hand2", activeforeground="#fff",
            activebackground="#6d28d9",
            command=self._game_start_countdown)
        self._game_start_btn.pack(fill=tk.X, padx=8, pady=4)

        # ── Live stats (hidden until active) ─────────────────────
        self._game_live_frame = tk.Frame(sb, bg=GAME_BG)

        gdiv2 = lambda: tk.Frame(self._game_live_frame,
            bg="#1e1a2e", height=1).pack(fill=tk.X, padx=6, pady=3)

        # 1. Challenge/preset name + constraint summary
        self._game_live_mode_var = tk.StringVar(value="")
        tk.Label(self._game_live_frame, textvariable=self._game_live_mode_var,
            fg=GAME_ACC, bg=GAME_BG, font=("Courier New", 9, "bold"),
            anchor=tk.CENTER).pack(fill=tk.X, padx=10, pady=(6,0))
        self._game_live_constr_var = tk.StringVar(value="")
        tk.Label(self._game_live_frame, textvariable=self._game_live_constr_var,
            fg=DIM2, bg=GAME_BG, font=("Courier New", 7),
            wraplength=190, justify=tk.CENTER, anchor=tk.CENTER).pack(
            fill=tk.X, padx=10, pady=(0,2))
        gdiv2()

        # 2. SCORE — huge and centered
        score_section = tk.Frame(self._game_live_frame, bg=GAME_BG)
        score_section.pack(fill=tk.X, pady=(4, 0))
        self._game_score_var = tk.StringVar(value="0")
        self._game_score_lbl = tk.Label(score_section,
            textvariable=self._game_score_var,
            fg="#fff", bg=GAME_BG, font=("Courier New", 36, "bold"),
            anchor=tk.CENTER)
        self._game_score_lbl.pack(fill=tk.X)
        tk.Label(score_section, text="pts", fg=GAME_ACC, bg=GAME_BG,
                 font=("Courier New", 9), anchor=tk.CENTER).pack()

        # 3. Per-word feedback label
        self._game_feedback_var = tk.StringVar(value="")
        self._game_feedback_lbl = tk.Label(self._game_live_frame,
            textvariable=self._game_feedback_var,
            fg=GREEN, bg=GAME_BG, font=("Courier New", 11, "bold"),
            anchor=tk.CENTER)
        self._game_feedback_lbl.pack(fill=tk.X, padx=10, pady=(2, 0))

        gdiv2()

        # 4. Streak + multiplier — combined, large, emotionally central
        self._game_streak_lbl = tk.Label(self._game_live_frame,
            text="streak: 0", fg=DIM, bg=GAME_BG,
            font=("Courier New", 16, "bold"), anchor=tk.CENTER)
        self._game_streak_lbl.pack(fill=tk.X, padx=10, pady=(4, 4))

        gdiv2()

        # 5. Timer
        self._game_timer_var = tk.StringVar(value="0:00")
        self._game_timer_lbl = tk.Label(self._game_live_frame,
            textvariable=self._game_timer_var,
            fg=DIM, bg=GAME_BG, font=("Courier New", 22, "bold"),
            anchor=tk.CENTER)
        self._game_timer_lbl.pack(fill=tk.X, padx=10, pady=(2,0))

        # 6. Word progress (challenge word goal)
        self._game_prog_frame = tk.Frame(self._game_live_frame, bg=GAME_BG)
        prog_inner = tk.Frame(self._game_prog_frame, bg=GAME_BG)
        prog_inner.pack(fill=tk.X, padx=10)
        tk.Label(prog_inner, text="words", fg=DIM2, bg=GAME_BG,
                 font=("Courier New", 8)).pack(side=tk.LEFT)
        self._game_prog_var = tk.StringVar(value="")
        tk.Label(prog_inner, textvariable=self._game_prog_var,
            fg=DIM, bg=GAME_BG, font=("Courier New", 11, "bold")).pack(side=tk.RIGHT)
        self._game_prog_bar = tk.Canvas(self._game_prog_frame,
            bg="#1e1a2e", height=3, highlightthickness=0)
        self._game_prog_bar.pack(fill=tk.X, padx=10, pady=(1,0))

        gdiv2()

        # 7. Stop button
        self._game_stop_btn = tk.Button(self._game_live_frame,
            text="■  STOP", bg="#3a1a1a", fg=RED,
            relief=tk.FLAT, font=("Courier New", 9, "bold"), pady=4, bd=0,
            cursor="hand2", activeforeground=RED, activebackground="#4a1a1a",
            command=self._game_stop_session)
        self._game_stop_btn.pack(fill=tk.X, padx=8, pady=(0, 4))

        # ── Results panel (shown after a session ends) ────────────
        self._game_results_frame = tk.Frame(sb, bg=GAME_BG)

        self._game_res_title_var = tk.StringVar(value="")
        tk.Label(self._game_results_frame, textvariable=self._game_res_title_var,
            fg=GAME_ACC, bg=GAME_BG, font=("Courier New", 8, "bold"),
            anchor=tk.CENTER).pack(fill=tk.X, padx=10, pady=(8, 0))

        self._game_res_stars_var = tk.StringVar(value="")
        self._game_res_stars_lbl = tk.Label(self._game_results_frame,
            textvariable=self._game_res_stars_var,
            fg=AMBER, bg=GAME_BG, font=("Courier New", 28))
        self._game_res_stars_lbl.pack(pady=(4, 0))

        self._game_res_score_var = tk.StringVar(value="0")
        tk.Label(self._game_results_frame, textvariable=self._game_res_score_var,
            fg="#fff", bg=GAME_BG,
            font=("Courier New", 36, "bold")).pack()
        tk.Label(self._game_results_frame, text="pts",
            fg=GAME_ACC, bg=GAME_BG, font=("Courier New", 8)).pack()

        # High score callout
        self._game_res_highscore_var = tk.StringVar(value="")
        self._game_res_highscore_lbl = tk.Label(self._game_results_frame,
            textvariable=self._game_res_highscore_var,
            fg=AMBER, bg=GAME_BG, font=("Courier New", 9, "bold"),
            anchor=tk.CENTER)
        # (packed conditionally in _game_show_results)

        tk.Frame(self._game_results_frame, bg="#1e1a2e", height=1).pack(
            fill=tk.X, padx=6, pady=6)

        res_stats = tk.Frame(self._game_results_frame, bg=GAME_BG)
        res_stats.pack(fill=tk.X, padx=10)
        self._game_res_stat_vars = {}
        for key, label in [("time","time"),("words","words"),
                            ("comply","comply"),("streak","streak"),
                            ("mult","best ×")]:
            row = tk.Frame(res_stats, bg=GAME_BG)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=label, fg=DIM2, bg=GAME_BG,
                font=("Courier New", 8)).pack(side=tk.LEFT)
            var = tk.StringVar(value="—")
            self._game_res_stat_vars[key] = var
            tk.Label(row, textvariable=var, fg=DIM, bg=GAME_BG,
                font=("Courier New", 10)).pack(side=tk.RIGHT)

        tk.Frame(self._game_results_frame, bg="#1e1a2e", height=1).pack(
            fill=tk.X, padx=6, pady=6)

        res_btns = tk.Frame(self._game_results_frame, bg=GAME_BG)
        res_btns.pack(fill=tk.X, padx=8, pady=(0, 4))
        self._game_res_retry_btn = tk.Button(res_btns, text="↻ Retry",
            bg=GAME_ACC, fg="#fff", relief=tk.FLAT,
            font=("Courier New", 8, "bold"), pady=4, bd=0, cursor="hand2",
            activeforeground="#fff", activebackground="#6d28d9")
        self._game_res_retry_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,1))
        self._game_res_next_btn = tk.Button(res_btns, text="→ Next",
            bg=GAME_BG2, fg=DIM, relief=tk.FLAT,
            font=("Courier New", 8), pady=4, bd=0, cursor="hand2",
            activeforeground=GAME_ACC, activebackground=GAME_BG2)
        self._game_res_next_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        self._game_res_back_btn = tk.Button(res_btns, text="← List",
            bg=GAME_BG2, fg=DIM, relief=tk.FLAT,
            font=("Courier New", 8), pady=4, bd=0, cursor="hand2",
            activeforeground=GAME_ACC, activebackground=GAME_BG2)
        self._game_res_back_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(1,0))

        # Unlock notification
        self._game_res_unlock_var = tk.StringVar(value="")
        self._game_res_unlock_lbl = tk.Label(self._game_results_frame,
            textvariable=self._game_res_unlock_var,
            fg=GREEN, bg=GAME_BG, font=("Courier New", 9, "bold"),
            wraplength=200, justify=tk.CENTER, anchor=tk.CENTER)
        # (packed conditionally in _game_show_results)

        # ── Leaderboard button ────────────────────────────────────
        self._game_lb_div = tk.Frame(sb, bg="#1e1a2e", height=1)
        self._game_lb_div.pack(fill=tk.X, padx=6, pady=4)
        tk.Button(sb, text="📊  Scores", bg=GAME_BG2, fg=DIM,
            relief=tk.FLAT, font=("Courier New", 8), pady=3, bd=0,
            cursor="hand2", activeforeground=GAME_ACC,
            activebackground=GAME_BG2,
            command=self._game_show_leaderboard).pack(
            fill=tk.X, padx=8, pady=(0, 6))

        # Default state: challenge mode, list visible, SA start btn hidden
        self._game_start_btn.pack_forget()

    # ── GAME MODE LOGIC ───────────────────────────────────────────

    def _game_toggle_mode(self, mode: str):
        if mode == self._game_mode:
            return
        self._game_mode = mode
        if mode == "game":
            self._write_sb_frame.pack_forget()
            self._game_sb_frame.pack(fill=tk.BOTH, expand=True)
            self._wb.config(bg=BG3, fg=DIM,
                activeforeground=DIM, activebackground=BG3)
            self._gb.config(bg=GAME_ACC, fg="#fff",
                activeforeground="#fff", activebackground=GAME_ACC)
        else:
            self._game_sb_frame.pack_forget()
            self._write_sb_frame.pack(fill=tk.BOTH, expand=True)
            self._wb.config(bg=ACCENT, fg="#000",
                activeforeground="#000", activebackground=ACCENT)
            self._gb.config(bg=BG3, fg=DIM,
                activeforeground=GAME_ACC, activebackground=BG3)
            if self._game_state == "active":
                self._game_stop_session()

    def _game_set_submode(self, mode: str):
        self._game_submode = mode
        if mode == "challenge":
            self._ch_btn.config(bg=GAME_ACC, fg="#fff")
            self._sa_btn.config(bg=GAME_BG2, fg=DIM)
            self._sa_list_frame.pack_forget()
            self._game_ch_info_frame.pack_forget()
            self._game_results_frame.pack_forget()
            self._ch_list_frame.pack(fill=tk.X)
            self._game_start_btn.pack_forget()
        else:
            self._sa_btn.config(bg=GAME_ACC, fg="#fff")
            self._ch_btn.config(bg=GAME_BG2, fg=DIM)
            self._ch_list_frame.pack_forget()
            self._game_ch_info_frame.pack_forget()
            self._game_results_frame.pack_forget()
            self._sa_list_frame.pack(fill=tk.X, padx=6)
            if not self._game_start_btn.winfo_ismapped():
                self._game_start_btn.pack(
                    fill=tk.X, padx=8, pady=4,
                    before=self._game_lb_div)
            if not self._game_sa_preset and GAME_SA_PRESETS:
                self._game_select_sa_preset(GAME_SA_PRESETS[0])

    def _game_set_difficulty(self, d: str):
        self._game_difficulty = d
        for k, b in self._diff_btns.items():
            b.config(bg=GAME_ACC if k == d else GAME_BG2,
                     fg="#fff" if k == d else DIM)

    def _game_set_duration(self, secs: int):
        self._game_sa_duration = secs
        self._game_sa_timed    = secs > 0
        for k, b in self._sa_dur_btns.items():
            b.config(bg=GAME_ACC if k == secs else GAME_BG2,
                     fg="#fff" if k == secs else DIM)

    def _game_select_challenge(self, ch: dict):
        if ch['id'] not in self._game_unlocked:
            return
        self._game_challenge = ch
        for cid, (row, lbl, dot) in self._ch_rows.items():
            active = cid == ch['id']
            row.config(bg="#161226" if active else GAME_BG)
            lbl.config(bg="#161226" if active else GAME_BG,
                       fg="#fff" if active else DIM)
            dot.config(bg="#161226" if active else GAME_BG)
        # Populate info panel
        self._ch_info_name_var.set(ch['name'])
        self._ch_info_desc_var.set(ch['description'])
        self._ch_info_constr_var.set(constraints_summary(ch['constraints']))
        goal = ch['goal']
        if goal['type'] == 'word_count':
            goal_str = f"{goal['target']} words"
        elif goal['type'] == 'score_target':
            goal_str = f"{goal['target']} pts"
        else:
            goal_str = "timed survival"
        self._ch_info_goal_var.set(
            f"goal: {goal_str}  ·  {fmt_time(ch['time_limit_seconds'])}")
        self._game_ch_start_btn.config(
            text="▶  START CHALLENGE", bg=GAME_ACC, fg="#fff", state=tk.NORMAL)
        # Hide list, show info panel in its place
        self._ch_list_frame.pack_forget()
        self._game_results_frame.pack_forget()
        if not self._game_ch_info_frame.winfo_ismapped():
            self._game_ch_info_frame.pack(
                fill=tk.X, before=self._game_lb_div)
        self._game_start_btn.pack_forget()

    def _game_refresh_challenge_list(self):
        """Rebuild challenge row lock states after unlocks."""
        self._game_unlocked = get_unlocked_challenges()
        for ch in GAME_CHALLENGES:
            if ch['id'] not in self._ch_rows:
                continue
            row, lbl, dot = self._ch_rows[ch['id']]
            sub_lbl = self._ch_sub_rows.get(ch['id'])
            locked = ch['id'] not in self._game_unlocked
            lbl.config(fg=DIM2 if locked else DIM,
                       cursor="" if locked else "hand2")
            dot.config(text="🔒" if locked else "▪",
                       fg=DIM2 if locked else GAME_ACC)
            row.config(cursor="" if locked else "hand2")
            # Show/hide the sub-label (prereq hint)
            if sub_lbl:
                if locked:
                    sub_lbl.pack(anchor=tk.W)
                else:
                    sub_lbl.pack_forget()
            # Remove all button-1 bindings then re-add if unlocked
            name_col = lbl.master
            for w in (row, dot, name_col, lbl):
                w.unbind("<Button-1>")
            if not locked:
                for w in (row, dot, name_col, lbl):
                    w.bind("<Button-1>",
                        lambda e, c=ch: self._game_select_challenge(c))

    def _game_select_sa_preset(self, p: dict):
        self._game_sa_preset = p
        # Set default duration
        dur = p.get('default_duration') or 0
        self._game_set_duration(dur)
        for pid, (row, lbl, dot) in self._sa_rows.items():
            active = pid == p['id']
            row.config(bg="#0d1626" if active else GAME_BG)
            lbl.config(bg="#0d1626" if active else GAME_BG,
                       fg="#fff" if active else DIM)
            dot.config(bg="#0d1626" if active else GAME_BG)
        self._game_start_btn.config(text=f"▶  {p['name'][:18]}")

    def _game_start_countdown(self):
        if self._game_state in ("countdown", "active"):
            return
        if self._game_submode == "challenge" and not self._game_challenge:
            return
        if self._game_submode == "scoreattack" and not self._game_sa_preset:
            return
        # Reset editor
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_content    = ""
        self.session_started = False
        self.elapsed         = 0
        self.analysis        = self._empty_analysis()
        self._game_last_wc   = 0

        self._game_state = "countdown"
        self._game_show_live(False)
        self._game_do_countdown(3)

    def _game_do_countdown(self, n: int):
        if self._game_state != "countdown":
            return
        btn = (self._game_ch_start_btn if self._game_submode == "challenge"
               else self._game_start_btn)
        if n > 0:
            btn.config(text=str(n), bg="#3a1a0a", fg=AMBER, state=tk.DISABLED)
            self.root.after(1000, lambda: self._game_do_countdown(n - 1))
        else:
            btn.config(text="WRITING...", bg="#0d1a0d", fg=GREEN, state=tk.DISABLED)
            self._game_activate_session()

    def _game_activate_session(self):
        if self._game_submode == "challenge":
            ch    = self._game_challenge
            constr = ch['constraints']
            mult   = ch['difficulty_multiplier']
            self._game_time_limit = ch['time_limit_seconds']
            self._game_live_mode_var.set(ch['name'].upper())
        else:
            p      = self._game_sa_preset
            constr = p['constraints']
            mult   = compute_difficulty_mult(constr)
            self._game_time_limit = (self._game_sa_duration
                                     if self._game_sa_timed else None)
            self._game_live_mode_var.set(f"SCORE ATTACK — {p['name']}")
        self._game_live_constr_var.set(constraints_summary(constr))

        self._game_scorer    = GameScorer(self._game_difficulty, constr, mult)
        self._game_state     = "active"
        self._game_start_mono = time.monotonic()
        self._game_elapsed   = 0
        self._game_show_live(True)
        self.text_widget.focus_set()
        self._game_tick()

    def _game_show_live(self, show: bool):
        if show:
            self._game_live_frame.pack(
                fill=tk.X, before=self._game_lb_div)
            self._game_ch_info_frame.pack_forget()
            self._game_results_frame.pack_forget()
            self._game_start_btn.pack_forget()
        else:
            self._game_live_frame.pack_forget()
            # Restore the pre-session UI (countdown case: re-show info/start)
            if self._game_submode == "challenge":
                if self._game_challenge:
                    if not self._game_ch_info_frame.winfo_ismapped():
                        self._game_ch_info_frame.pack(
                            fill=tk.X, before=self._game_lb_div)
                    self._game_ch_start_btn.config(
                        text="▶  START CHALLENGE",
                        bg=GAME_ACC, fg="#fff", state=tk.NORMAL)
            else:
                if not self._game_start_btn.winfo_ismapped():
                    self._game_start_btn.pack(
                        fill=tk.X, padx=8, pady=4,
                        before=self._game_lb_div)
                if self._game_sa_preset:
                    self._game_start_btn.config(
                        text=f"▶  {self._game_sa_preset['name'][:18]}",
                        bg=GAME_ACC, fg="#fff", state=tk.NORMAL)
                else:
                    self._game_start_btn.config(
                        text="▶  START", bg=GAME_ACC, fg="#fff",
                        state=tk.NORMAL)

    def _game_tick(self):
        if self._game_state != "active":
            return
        self._game_elapsed = int(time.monotonic() - self._game_start_mono)
        self._game_update_display()

        if self._game_time_limit:
            remaining = self._game_time_limit - self._game_elapsed
            if remaining <= 0:
                self._game_end_session(timed_out=True)
                return

        self._game_timer_job = self.root.after(500, self._game_tick)

    def _game_update_display(self):
        if not self._game_scorer:
            return
        sc = self._game_scorer
        self._game_score_var.set(str(sc.int_score()))

        mult = sc.streak_mult()
        score_col = ("#e879f9" if mult >= 4.0 else
                     RED        if mult >= 3.0 else
                     "#f97316"  if mult >= 2.0 else
                     AMBER      if mult >= 1.5 else "#fff")
        self._game_score_lbl.config(fg=score_col)

        # Combined streak + multiplier label
        streak = sc.streak
        if streak > 0:
            streak_text = f"🔥 {streak} STREAK  ×{mult:.1f}"
        else:
            streak_text = f"streak: 0  ×{mult:.1f}"
        streak_col = ("#e879f9" if mult >= 4.0 else
                      RED        if mult >= 3.0 else
                      "#f97316"  if mult >= 2.0 else
                      AMBER      if mult >= 1.5 else DIM)
        # Flash red on streak reset
        if streak == 0 and self._game_streak_prev > 0:
            self._game_streak_lbl.config(text=streak_text, fg=RED)
            self.root.after(500, lambda: self._game_streak_lbl.config(fg=DIM)
                            if self._game_scorer and self._game_scorer.streak == 0
                            else None)
        else:
            self._game_streak_lbl.config(text=streak_text, fg=streak_col)
        self._game_streak_prev = streak

        if self._game_time_limit:
            remaining = max(0, self._game_time_limit - self._game_elapsed)
            self._game_timer_var.set(
                fmt_time(remaining) + (" ⚠" if remaining < 30 else ""))
            self._game_timer_lbl.config(
                fg=RED if remaining < 30 else
                AMBER if remaining < 60 else DIM)
        else:
            self._game_timer_var.set(fmt_time(self._game_elapsed))
            self._game_timer_lbl.config(fg=DIM)

        # Progress bar (challenge word-count goal)
        if self._game_submode == "challenge" and self._game_challenge:
            goal = self._game_challenge['goal']
            if goal['type'] == 'word_count':
                wc  = self._game_scorer.total_words
                tgt = goal['target']
                self._game_prog_var.set(f"{wc} / {tgt}")
                self._game_prog_frame.pack(fill=tk.X)

                def _draw_prog():
                    w = self._game_prog_bar.winfo_width()
                    self._game_prog_bar.delete("all")
                    pct = min(1.0, wc / tgt) if tgt else 0
                    self._game_prog_bar.create_rectangle(
                        0, 0, int(w * pct), 3,
                        fill=GREEN if pct >= 1.0 else GAME_ACC, outline="")
                self._game_prog_bar.after_idle(_draw_prog)
        else:
            self._game_prog_frame.pack_forget()

    def _game_show_word_feedback(self, pts: float, compliant: bool):
        """Flash per-word score feedback below the score label."""
        if self._game_feedback_job:
            self.root.after_cancel(self._game_feedback_job)
            self._game_feedback_job = None
        if compliant:
            mult = self._game_scorer.streak_mult() if self._game_scorer else 1.0
            if mult > 1.0:
                text = f"+{int(pts)}  ×{mult:.1f}"
            else:
                text = f"+{int(pts)}"
            self._game_feedback_lbl.config(fg=GREEN)
        else:
            text = "STREAK LOST"
            self._game_feedback_lbl.config(fg=RED)
        self._game_feedback_var.set(text)
        self._game_feedback_job = self.root.after(
            1000, lambda: self._game_feedback_var.set(""))

    def _game_on_text_change(self, analysis: dict):
        """Called from _on_key_release when game session is active."""
        if self._game_state != "active" or not self._game_scorer:
            return
        wc = analysis['word_count']
        # Only score words that are "complete" (followed by whitespace).
        # If text does NOT end with whitespace, the last token is still being typed —
        # hold it back so feedback fires on the space keypress, not the first letter.
        trailing_ws = bool(self.text_content and self.text_content[-1] in ' \t\n')
        complete_wc = wc if trailing_ws else max(0, wc - 1)
        if complete_wc <= self._game_last_wc:
            return
        raw_words  = get_words(self.text_content)
        viol_idxs  = {v['word_index'] for v in analysis['violations']}
        now        = time.monotonic()
        for i in range(self._game_last_wc, complete_wc):
            if i >= len(raw_words):
                break
            word      = clean_word(raw_words[i])
            if not word:
                continue
            compliant = i not in viol_idxs
            pts = self._game_scorer.score_word(word, compliant, now)
            self._game_show_word_feedback(pts, compliant)
        self._game_last_wc = complete_wc
        self._game_update_display()
        self._game_check_goal(analysis)

    def _game_check_goal(self, analysis: dict):
        """Check if challenge/SA goal has been met."""
        if self._game_state != "active":
            return
        if self._game_submode != "challenge":
            return
        ch   = self._game_challenge
        goal = ch['goal']
        sc   = self._game_scorer
        met  = False
        if goal['type'] == 'word_count':
            met = sc.total_words >= goal['target']
        elif goal['type'] == 'score_target':
            met = sc.int_score() >= goal['target']
        if met:
            self._game_end_session(timed_out=False)

    def _game_stop_session(self):
        """User manually stops the session."""
        if self._game_state == "active":
            self._game_end_session(timed_out=False, manual_stop=True)
        elif self._game_state == "countdown":
            self._game_state = "idle"
            self._game_show_live(False)

    def _game_end_session(self, timed_out: bool = False,
                          manual_stop: bool = False):
        self._game_state = "done"
        if self._game_timer_job:
            self.root.after_cancel(self._game_timer_job)
            self._game_timer_job = None
        self.timer_running = False

        sc = self._game_scorer
        if not sc:
            self._game_state = "idle"
            self._game_show_live(False)
            return

        remaining = 0
        if self._game_time_limit:
            remaining = max(0, self._game_time_limit - self._game_elapsed)

        stars = 0
        if self._game_submode == "challenge" and self._game_challenge:
            stars = eval_stars(self._game_challenge, sc.compliance,
                               remaining, sc.int_score())

        entry = {
            "score":       sc.int_score(),
            "compliance":  round(sc.compliance, 3),
            "words":       sc.total_words,
            "peak_streak": sc.peak_streak,
            "peak_mult":   sc.peak_mult,
            "date":        datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }

        # Capture previous best before saving new score
        _prev_best = self._get_best_score()

        # Persist score silently in background (capture state before thread)
        _submode   = self._game_submode
        _challenge = self._game_challenge
        _sa_preset = self._game_sa_preset
        _diff      = self._game_difficulty
        _elapsed   = self._game_elapsed
        def _save():
            data = load_scores()
            if _submode == "challenge" and _challenge:
                entry["stars"]        = stars
                entry["time_seconds"] = _elapsed
                append_score(data, "challenges",
                             _challenge['id'], _diff, entry)
            else:
                key = f"preset:{_sa_preset['id']}" if _sa_preset else "custom"
                entry["duration"] = _elapsed
                append_score(data, "score_attack", key, _diff, entry)
            save_scores(data)
        threading.Thread(target=_save, daemon=True).start()

        # Set elapsed in entry so results panel can display it
        if _submode == "challenge" and _challenge:
            entry["time_seconds"] = _elapsed
        else:
            entry["duration"] = _elapsed

        # Hide live frame without restoring the pre-session UI
        self._game_live_frame.pack_forget()
        self._game_state = "idle"
        self.root.after(50, lambda: self._game_show_results(
            entry, stars, timed_out, manual_stop, _prev_best))

    def _game_back_to_list(self):
        """Return to the challenge or preset list from info/results panels."""
        self._game_ch_info_frame.pack_forget()
        self._game_results_frame.pack_forget()
        if self._game_submode == "challenge":
            self._ch_list_frame.pack(fill=tk.X)
        else:
            if not self._sa_list_frame.winfo_ismapped():
                self._sa_list_frame.pack(fill=tk.X, padx=6)
            if not self._game_start_btn.winfo_ismapped():
                self._game_start_btn.pack(
                    fill=tk.X, padx=8, pady=4, before=self._game_lb_div)

    def _game_show_results(self, entry: dict, stars: int,
                           timed_out: bool, manual_stop: bool,
                           prev_best: int | None = None):
        """Populate and show the in-sidebar results panel."""
        is_challenge = (self._game_submode == "challenge"
                        and self._game_challenge)

        # Title line
        if is_challenge:
            title = self._game_challenge['name']
        elif self._game_sa_preset:
            title = f"Score Attack — {self._game_sa_preset['name']}"
        else:
            title = "Score Attack"
        if timed_out:
            title += "  · Time's Up!"
        elif manual_stop:
            title += "  · Stopped"
        self._game_res_title_var.set(title)

        # Stars (challenge only)
        if is_challenge:
            star_str = "★" * stars + "☆" * (3 - stars)
            star_col = (GREEN if stars == 3 else
                        AMBER if stars == 2 else
                        RED   if stars == 1 else DIM2)
            self._game_res_stars_var.set(star_str)
            self._game_res_stars_lbl.config(fg=star_col)
            self._game_res_stars_lbl.pack(pady=(4, 0))
        else:
            self._game_res_stars_lbl.pack_forget()

        # Score
        self._game_res_score_var.set(str(entry['score']))

        # High score callout
        best = prev_best
        is_new_high = (best is None or entry['score'] > best) and entry['score'] > 0
        if is_new_high:
            self._game_res_highscore_var.set("🏆 NEW HIGH SCORE")
            self._game_res_highscore_lbl.config(fg=AMBER)
            self._game_res_highscore_lbl.pack(pady=(2, 0))
        elif best is not None and best > 0:
            self._game_res_highscore_var.set(f"Best: {best}")
            self._game_res_highscore_lbl.config(fg=DIM2)
            self._game_res_highscore_lbl.pack(pady=(2, 0))
        else:
            self._game_res_highscore_lbl.pack_forget()

        # Stats
        elapsed = entry.get('time_seconds', entry.get('duration', 0))
        co = entry['compliance']
        co_col = (GREEN if co >= 0.95 else AMBER if co >= 0.80 else RED)
        self._game_res_stat_vars['time'].set(fmt_time(elapsed))
        self._game_res_stat_vars['words'].set(str(entry['words']))
        self._game_res_stat_vars['comply'].set(f"{int(co*100)}%")
        self._game_res_stat_vars['streak'].set(str(entry['peak_streak']))
        self._game_res_stat_vars['mult'].set(
            f"×{entry.get('peak_mult', 1.0):.1f}")

        # Wire buttons
        self._game_res_retry_btn.config(
            command=self._game_start_countdown)

        # Always repack back btn last to preserve [Retry][Next?][Back] order
        self._game_res_back_btn.pack_forget()
        if is_challenge:
            ch_list = GAME_CHALLENGES
            idx = next((i for i, c in enumerate(ch_list)
                        if c['id'] == self._game_challenge['id']), -1)
            if idx >= 0 and idx + 1 < len(ch_list):
                next_ch = ch_list[idx + 1]
                self._game_res_next_btn.config(
                    command=lambda c=next_ch: [
                        self._game_results_frame.pack_forget(),
                        self._game_select_challenge(c),
                    ])
                self._game_res_next_btn.pack(
                    side=tk.LEFT, fill=tk.X, expand=True, padx=1)
            else:
                self._game_res_next_btn.pack_forget()
            self._game_res_back_btn.config(
                text="← Challenges",
                command=self._game_back_to_list)
        else:
            self._game_res_next_btn.pack_forget()
            self._game_res_back_btn.config(
                text="← Presets",
                command=self._game_back_to_list)
        self._game_res_back_btn.pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(1, 0))

        # Unlock notification
        newly = self._get_newly_unlocked()
        if newly:
            names = ", ".join(c['name'] for c in newly)
            self._game_res_unlock_var.set(f"🔓 UNLOCKED: {names}")
            self._game_res_unlock_lbl.pack(fill=tk.X, padx=10, pady=(4, 0))
            self._game_refresh_challenge_list()
        else:
            self._game_res_unlock_lbl.pack_forget()

        # Show the results frame
        self._game_results_frame.pack(
            fill=tk.X, before=self._game_lb_div)

    def _get_best_score(self) -> int | None:
        """Return best previous score for current challenge/preset+difficulty, or None."""
        data = load_scores()
        diff = self._game_difficulty
        if self._game_submode == "challenge" and self._game_challenge:
            entries = data.get("challenges", {}).get(
                self._game_challenge['id'], {}).get(diff, [])
        elif self._game_sa_preset:
            key = f"preset:{self._game_sa_preset['id']}"
            entries = data.get("score_attack", {}).get(key, {}).get(diff, [])
        else:
            return None
        if not entries:
            return None
        return max(e.get('score', 0) for e in entries)

    def _get_newly_unlocked(self) -> list:
        """Return list of challenge dicts newly unlocked by the last session."""
        new_unlocked = get_unlocked_challenges()
        newly = [ch for ch in GAME_CHALLENGES
                 if ch['id'] in new_unlocked
                 and ch['id'] not in self._game_unlocked]
        self._game_unlocked = new_unlocked
        return newly

    def _game_show_leaderboard(self):
        from tkinter import ttk
        data = load_scores()
        win  = tk.Toplevel(self.root)
        win.title("Scores")
        win.configure(bg=GAME_BG)
        win.geometry("540x420")
        win.attributes("-topmost", True)

        tk.Label(win, text="LEADERBOARDS", fg=GAME_ACC, bg=GAME_BG,
                 font=("Courier New", 11, "bold")).pack(
                 anchor=tk.W, padx=16, pady=(14, 4))

        # Build flat list of all entries
        rows = []
        for cid, diffs in data.get("challenges", {}).items():
            ch_name = next((c['name'] for c in GAME_CHALLENGES
                           if c['id'] == cid), cid)
            for diff, entries in diffs.items():
                for e in entries[:10]:
                    rows.append((ch_name, diff,
                                 str(e.get('score', 0)),
                                 "★"*e.get('stars', 0),
                                 f"{int(e.get('compliance',0)*100)}%",
                                 e.get('date','')[:10]))
        for pid, diffs in data.get("score_attack", {}).items():
            label = pid.replace("preset:", "SA: ").replace("custom","SA: custom")
            for diff, entries in diffs.items():
                for e in entries[:10]:
                    rows.append((label, diff,
                                 str(e.get('score', 0)),
                                 "—",
                                 f"{int(e.get('compliance',0)*100)}%",
                                 e.get('date','')[:10]))

        style = ttk.Style(win)
        style.theme_use('clam')
        style.configure("Game.Treeview",
            background=GAME_BG2, foreground=DIM,
            rowheight=22, fieldbackground=GAME_BG2,
            bordercolor=GAME_BG, font=("Courier New", 9))
        style.configure("Game.Treeview.Heading",
            background=GAME_BG, foreground=DIM2,
            font=("Courier New", 8, "bold"))

        cols = ("Mode", "Diff", "Score", "Stars", "Comply", "Date")
        tv   = ttk.Treeview(win, columns=cols, show="headings",
                             style="Game.Treeview")
        for col, w in zip(cols, [140, 50, 60, 50, 60, 80]):
            tv.heading(col, text=col)
            tv.column(col, width=w, anchor=tk.CENTER
                       if col != "Mode" else tk.W)

        if rows:
            rows.sort(key=lambda r: -int(r[2]))
            for r in rows:
                tv.insert("", tk.END, values=r)
        else:
            tv.insert("", tk.END, values=("No scores yet","","","","",""))

        sb2 = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tv.yview)
        tv.configure(yscrollcommand=sb2.set)
        sb2.pack(side=tk.RIGHT, fill=tk.Y, padx=(0,8), pady=(0,8))
        tv.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,8))

        tk.Button(win, text="Close", fg=DIM, bg=GAME_BG2, relief=tk.FLAT,
            font=("Courier New", 9), pady=4, bd=0, cursor="hand2",
            activebackground=GAME_BG2,
            command=win.destroy).pack(pady=(0,8))

    def _make_preset_row(self, parent, p: dict, deletable: bool):
        row = tk.Frame(parent, bg=BG2, cursor="hand2")
        row.pack(fill=tk.X)
        dot = tk.Label(row, text="▪", fg=p['color'], bg=BG2,
                       font=("Courier New", 9), width=2)
        dot.pack(side=tk.LEFT, padx=(8, 0))
        lbl = tk.Label(row, text=p['name'], fg=DIM, bg=BG2,
                       font=SERIF_SM, anchor=tk.W, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=4, pady=6, fill=tk.X, expand=True)
        if deletable:
            del_btn = tk.Label(row, text="✕", fg=DIM2, bg=BG2,
                               font=("Courier New", 8), cursor="hand2", padx=4)
            del_btn.pack(side=tk.RIGHT, padx=(0, 6))
            del_btn.bind("<Button-1>",
                lambda e, pid=p['id']: self._delete_user_preset(pid))
        for w in (row, dot, lbl):
            w.bind("<Button-1>",
                   lambda e, pid=p['id']: self._select_preset(pid))
        self.preset_rows[p['id']] = (row, lbl, dot)

    def _sb_label(self, parent, text):
        tk.Label(parent, text=text, fg=DIM2, bg=BG2,
                 font=("Courier New", 8)).pack(anchor=tk.W, padx=12, pady=(6, 2))

    def _sb_bar_section(self, parent, label):
        f   = tk.Frame(parent, bg=BG2)
        row = tk.Frame(f, bg=BG2)
        row.pack(fill=tk.X)
        tk.Label(row, text=label, fg=DIM2, bg=BG2,
                 font=("Courier New", 8)).pack(side=tk.LEFT)
        sv = tk.StringVar(value="")
        tk.Label(row, textvariable=sv, fg=DIM, bg=BG2,
                 font=("Courier New", 9)).pack(side=tk.RIGHT)
        bar = tk.Canvas(f, bg=BORDER, height=3, highlightthickness=0)
        bar.pack(fill=tk.X, pady=(2, 0))
        f._sv  = sv
        f._bar = bar
        f.pack_forget()
        return f

    def _update_bar(self, frame, pct: float, label: str, color: str):
        frame._sv.set(label)
        def _draw():
            w = frame._bar.winfo_width()
            frame._bar.delete("all")
            frame._bar.create_rectangle(
                0, 0, max(0, int(w * min(1.0, pct/100))), 3,
                fill=color, outline="")
        frame._bar.after_idle(_draw)
        frame.pack(fill=tk.X, padx=12, pady=3)

    # ── HISTORY ───────────────────────────────────────────────────

    def _build_history_view(self):
        self.history_frame = tk.Frame(self.body, bg=BG)

        hdr_row = tk.Frame(self.history_frame, bg=BG)
        hdr_row.pack(fill=tk.X, padx=32, pady=(24, 12))
        tk.Label(hdr_row, text="SESSION HISTORY", fg=DIM2, bg=BG,
                 font=("Courier New", 9)).pack(side=tk.LEFT)
        right = tk.Frame(hdr_row, bg=BG)
        right.pack(side=tk.RIGHT)
        tk.Button(right, text="Clear all", fg=DIM2, bg=BG,
                  relief=tk.FLAT, font=("Courier New", 8), cursor="hand2",
                  bd=0, activebackground=BG,
                  command=self._clear_history).pack(side=tk.LEFT, padx=8)
        tk.Button(right, text="+ New Session", fg=ACCENT, bg=BG,
                  relief=tk.FLAT, font=("Courier New", 9), cursor="hand2",
                  bd=0, activebackground=BG,
                  command=lambda: self._show_view("editor")).pack(side=tk.LEFT)

        canvas = tk.Canvas(self.history_frame, bg=BG, highlightthickness=0)
        sb     = tk.Scrollbar(self.history_frame, orient=tk.VERTICAL,
                               command=canvas.yview, bg=BG2, troughcolor=BG)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True, padx=32)

        self.hist_inner  = tk.Frame(canvas, bg=BG)
        self.hist_window = canvas.create_window(
            (0, 0), window=self.hist_inner, anchor=tk.NW)
        self.hist_canvas = canvas
        self.hist_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(self.hist_window, width=e.width))

    # ── BUILDER ───────────────────────────────────────────────────

    def _build_builder_view(self):
        self.builder_frame = tk.Frame(self.body, bg=BG)

        canvas = tk.Canvas(self.builder_frame, bg=BG, highlightthickness=0)
        sb     = tk.Scrollbar(self.builder_frame, orient=tk.VERTICAL,
                               command=canvas.yview, bg=BG2, troughcolor=BG)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=BG)
        win   = canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width))

        pad = tk.Frame(inner, bg=BG)
        pad.pack(fill=tk.BOTH, expand=True, padx=48, pady=28)

        tk.Label(pad, text="CONSTRAINT BUILDER", fg=DIM2, bg=BG,
                 font=("Courier New", 9)).pack(anchor=tk.W, pady=(0, 16))

        self._brow(pad, "Exact Word Length",
                   "Every word must be exactly N letters long.",
                   self.b['wl_on'], [("Letters:", self.b['wl_n'], 2, 15)])
        self._brow(pad, "Alphabet Cycle",
                   "Each word starts with the next letter (A-B-C...Z-A...).",
                   self.b['ac_on'], [], extra_widgets=self._alpha_extras)
        self._brow(pad, "Word Goal",
                   "Session target: write N words.",
                   self.b['wg_on'], [("Target:", self.b['wg_n'], 10, 50000)])
        self._brow(pad, "Time Limit",
                   "Countdown begins on your first keystroke.",
                   self.b['tl_on'], [("Minutes:", self.b['tl_mins'], 1, 180)])
        self._brow(pad, "Starting Letter Max",
                   "Each letter of the alphabet may start at most N words.",
                   self.b['sl_on'], [("Max:", self.b['sl_n'], 1, 10000)])
        self._brow(pad, "Pangram Challenge",
                   "Use every letter of the alphabet within N words.",
                   self.b['pg_on'], [("Within words:", self.b['pg_n'], 26, 1000)])
        self._brow(pad, "No Repeated Words",
                   "Never reuse the same root word (ran/run/running = same).",
                   self.b['nr_on'], [], extra_widgets=self._norepeat_extras)
        self._brow(pad, "Dictionary Validation",
                   "Flag words not found in the bundled 357k-word wordlist.",
                   self.b['dc_on'], [], extra_widgets=self._dict_extras)

        # Feasibility
        self.feas_frame = tk.Frame(pad, bg=BG3)
        self.feas_frame.pack(fill=tk.X, pady=8)
        self.feas_inner = tk.Frame(self.feas_frame, bg=BG3)
        self.feas_inner.pack(fill=tk.X, padx=14, pady=10)
        tk.Label(self.feas_inner,
                 text="Enable constraints above to check feasibility.",
                 fg=DIM2, bg=BG3, font=SERIF_SM).pack(anchor=tk.W)

        # Action buttons
        btn_row = tk.Frame(pad, bg=BG)
        btn_row.pack(anchor=tk.W, pady=(4, 16))
        tk.Button(btn_row, text="APPLY & START SESSION",
                  fg="#000", bg=ACCENT, relief=tk.FLAT,
                  font=("Courier New", 10, "bold"), padx=20, pady=10,
                  cursor="hand2", bd=0,
                  activeforeground="#000", activebackground="#d4920a",
                  command=self._apply_builder).pack(side=tk.LEFT)
        tk.Button(btn_row, text="SAVE AS PRESET",
                  fg=ACCENT, bg=BG3, relief=tk.FLAT,
                  font=("Courier New", 10), padx=16, pady=10,
                  cursor="hand2", bd=0,
                  activeforeground=ACCENT, activebackground=BG3,
                  command=self._save_builder_as_preset).pack(
                      side=tk.LEFT, padx=(10, 0))

        # Frequency chart
        tk.Frame(pad, bg=BORDER, height=1).pack(fill=tk.X, pady=12)
        tk.Label(pad,
                 text="LETTER FREQUENCY  —  % of English words starting with each letter",
                 fg=DIM2, bg=BG, font=("Courier New", 8)).pack(
                     anchor=tk.W, pady=(0, 8))
        chart = tk.Canvas(pad, bg=BG, height=90, highlightthickness=0)
        chart.pack(fill=tk.X)

        def draw_chart(e=None):
            chart.delete("all")
            w = chart.winfo_width()
            if w < 10: return
            bw = w / 26
            for i, l in enumerate(ALPHABET):
                freq  = START_FREQ[l]
                bar_h = max(4, (freq / 12.4) * 58)
                x0    = i * bw + 1
                x1    = (i + 1) * bw - 2
                y0    = 65 - bar_h
                rare  = l in ('x', 'q', 'z')
                chart.create_rectangle(x0, y0, x1, 65,
                    fill="#3a1a1a" if rare else "#1e2a1e", outline="")
                chart.create_rectangle(x0, y0, x1, y0+2,
                    fill=RED if rare else GREEN, outline="")
                chart.create_text(x0+bw/2-1, 75,
                    text=l.upper(), font=("Courier New", 7), fill=DIM2)

        chart.bind("<Configure>", draw_chart)
        pad.after(120, draw_chart)
        tk.Label(pad,
                 text="Red (X, Q, Z) are rare word-starters — plan accordingly.",
                 fg=DIM2, bg=BG, font=("Courier New", 8), pady=4).pack(anchor=tk.W)

    def _brow(self, parent, label, desc, var, spinners, extra_widgets=None):
        card = tk.Frame(parent, bg=BG3)
        card.pack(fill=tk.X, pady=3)
        top  = tk.Frame(card, bg=BG3)
        top.pack(fill=tk.X, padx=14, pady=(10, 4))
        left = tk.Frame(top, bg=BG3)
        left.pack(side=tk.LEFT)
        tk.Label(left, text=label, fg=DIM, bg=BG3,
                 font=("Georgia", 12)).pack(anchor=tk.W)
        tk.Label(left, text=desc,  fg=DIM2, bg=BG3,
                 font=("Courier New", 8)).pack(anchor=tk.W)
        tog = tk.Label(top, text="OFF", fg=DIM2, bg=BG3,
                       font=("Courier New", 9, "bold"),
                       cursor="hand2", padx=9, pady=3)
        tog.pack(side=tk.RIGHT, padx=(8, 0))
        body = tk.Frame(card, bg=BG3)
        if spinners:
            srow = tk.Frame(body, bg=BG3)
            srow.pack(anchor=tk.W, padx=14, pady=(0, 8))
            for lbl_txt, ivar, lo, hi in spinners:
                tk.Label(srow, text=lbl_txt, fg=DIM, bg=BG3,
                         font=("Courier New", 10)).pack(side=tk.LEFT)
                tk.Spinbox(srow, from_=lo, to=hi, textvariable=ivar,
                           width=8, bg="#0a0a0d", fg=TEXT,
                           insertbackground=ACCENT, relief=tk.FLAT,
                           font=("Courier New", 12),
                           buttonbackground=BG2).pack(side=tk.LEFT, padx=(6,16))
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
        tk.Checkbutton(parent, text="Skip X entirely (25-letter cycle)",
                       variable=self.b['ac_skipx'], fg=DIM, bg=BG3,
                       selectcolor=BG, activebackground=BG3,
                       font=("Courier New", 9)).pack(anchor=tk.W, padx=14)
        tk.Checkbutton(parent, text="X turn is optional (any letter accepted)",
                       variable=self.b['ac_xopt'], fg=DIM, bg=BG3,
                       selectcolor=BG, activebackground=BG3,
                       font=("Courier New", 9)).pack(
                           anchor=tk.W, padx=14, pady=(0, 8))

    def _norepeat_extras(self, parent):
        tk.Checkbutton(parent,
                       text="Content words only (ignore: the, and, I, etc.)",
                       variable=self.b['nr_content'], fg=DIM, bg=BG3,
                       selectcolor=BG, activebackground=BG3,
                       font=("Courier New", 9)).pack(
                           anchor=tk.W, padx=14, pady=(0, 4))
        note = ("spaCy active — lemma matching (ran = run = running)."
                if SPACY_AVAILABLE else
                "spaCy not found — exact string matching only.")
        tk.Label(parent, text=note,
                 fg=GREEN if SPACY_AVAILABLE else DIM2,
                 bg=BG3, font=("Courier New", 8)).pack(
                     anchor=tk.W, padx=14, pady=(0, 8))

    def _dict_extras(self, parent):
        note = ("357,325-word SCOWL-80 wordlist loaded."
                if WORDLIST else
                "wordlist.txt not found — place it alongside tether.py")
        tk.Label(parent, text=note,
                 fg=GREEN if WORDLIST else RED,
                 bg=BG3, font=("Courier New", 8)).pack(
                     anchor=tk.W, padx=14, pady=(0, 8))

    # ─────────────────────────────────────────────────────────────
    # VIEW SWITCHING
    # ─────────────────────────────────────────────────────────────

    def _show_view(self, view: str):
        for f in (self.editor_frame, self.history_frame, self.builder_frame):
            f.pack_forget()
        {'editor':  self.editor_frame,
         'history': self.history_frame,
         'builder': self.builder_frame}[view].pack(fill=tk.BOTH, expand=True)
        for v, btn in self.nav_btns.items():
            active = v == view
            btn.config(fg="#000" if active else DIM,
                       bg=ACCENT if active else BG2,
                       activeforeground="#000" if active else DIM,
                       activebackground=ACCENT if active else BG2)
        if view == "history":
            self._refresh_history()
        if view == "editor":
            self.text_widget.focus_set()

    # ─────────────────────────────────────────────────────────────
    # PRESET MANAGEMENT
    # ─────────────────────────────────────────────────────────────

    def _select_preset(self, preset_id: str):
        p = self._find_preset(preset_id)
        if p:
            self.active_preset      = p
            self.custom_constraints = None
            self._reset_session()

    def _delete_user_preset(self, preset_id: str):
        p    = self._find_preset(preset_id)
        name = p['name'] if p else preset_id
        if not messagebox.askyesno("Delete preset",
                                    f'Delete preset "{name}"?'):
            return
        self.user_presets = [x for x in self.user_presets if x['id'] != preset_id]
        save_user_presets(self.user_presets)
        if self.active_preset.get('id') == preset_id:
            self.active_preset = BUILTIN_PRESETS[0]
        self._build_sidebar_contents()
        self._update_preset_highlight()

    def _save_builder_as_preset(self):
        c = self._constraints_from_builder()
        if not c:
            messagebox.showinfo("No constraints",
                                "Enable at least one constraint first.")
            return
        errors = [w for w in check_feasibility(c) if w['level'] == 'error']
        if errors:
            messagebox.showerror("Infeasible", errors[0]['msg'])
            return
        name = simpledialog.askstring(
            "Save Preset", "Name for this preset:", parent=self.root)
        if not name or not name.strip():
            return
        name = name.strip()
        pid  = re.sub(r'[^a-z0-9]', '_', name.lower()) + f"_{int(time.time())}"
        preset = {
            "id": pid, "name": name, "color": ACCENT,
            "desc": constraints_summary(c),
            "constraints": c, "builtin": False,
        }
        self.user_presets.append(preset)
        save_user_presets(self.user_presets)
        self._build_sidebar_contents()
        self._update_preset_highlight()
        messagebox.showinfo("Saved", f'"{name}" added to My Presets.')

    # ─────────────────────────────────────────────────────────────
    # SESSION CONTROL
    # ─────────────────────────────────────────────────────────────

    def _reset_session(self):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_content    = ""
        self.session_started = False
        self.elapsed         = 0
        self.timer_target    = None
        self.timer_running   = False
        self.analysis        = self._empty_analysis()
        self.deep            = {}
        self._update_all()
        self._show_view("editor")
        self.text_widget.focus_set()

    def _constraints(self) -> list:
        return (self.custom_constraints
                if self.custom_constraints is not None
                else self.active_preset['constraints'])

    # ─────────────────────────────────────────────────────────────
    # INPUT & TIMER
    # ─────────────────────────────────────────────────────────────

    def _on_key_press(self, event):
        if self.timer_target and self.elapsed >= self.timer_target:
            return "break"

    def _on_key_release(self, event):
        # In game mode, block write-mode timer entirely
        if self._game_mode == "game" and self._game_state != "active":
            return
        if self._game_state == "active":
            self.text_content = self.text_widget.get("1.0", tk.END)
            constraints = (self._game_challenge['constraints']
                           if self._game_submode == "challenge"
                              and self._game_challenge
                           else (self._game_sa_preset['constraints']
                                 if self._game_sa_preset else []))
            self.analysis = analyze_text(
                self.text_content, constraints, self._game_elapsed)
            self._game_on_text_change(self.analysis)
            return

        if self.timer_target and self.elapsed >= self.timer_target:
            return
        self.text_content = self.text_widget.get("1.0", tk.END)
        if not self.session_started and self.text_content.strip():
            self.session_started = True
            tl = next((c for c in self._constraints()
                        if c['type'] == 'timeLimit'), None)
            self.timer_target  = tl['seconds'] if tl else None
            self.timer_running = True
            self._tick()
        self.analysis = analyze_text(
            self.text_content, self._constraints(), self.elapsed)
        self._update_all()
        if hasattr(self, '_deep_job'):
            self.root.after_cancel(self._deep_job)
        self._deep_job = self.root.after(1500, self._run_deep_analysis)

    def _run_deep_analysis(self):
        if not self.text_content.strip():
            return
        self.deep = deep_analyze(self.text_content)
        self._update_language_panel()
        self._update_violations()

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
        self.analysis = analyze_text(
            self.text_content, self._constraints(), self.elapsed)
        self._update_stats()
        self.root.after(1000, self._tick)

    def _update_timer_label(self):
        done = self.timer_target and self.elapsed >= self.timer_target
        if self.elapsed == 0:
            self.hdr_timer.config(text="", fg=DIM)
        elif self.timer_target and not done:
            self.hdr_timer.config(
                text=fmt_time(self.timer_target - self.elapsed), fg=ACCENT)
        else:
            self.hdr_timer.config(
                text=fmt_time(self.elapsed), fg=RED if done else DIM)

    def _on_timer_done(self):
        messagebox.showinfo("Time's Up!",
            f"Time's up!\n\n"
            f"Words     : {self.analysis['word_count']}\n"
            f"WPM       : {self.analysis['wpm']}\n"
            f"Compliance: {self.analysis['compliance']}%\n"
            f"Violations: {len(self.analysis['violations'])}\n\n"
            "Use  Save  to record this session.")

    # ─────────────────────────────────────────────────────────────
    # SAVE / EXPORT
    # ─────────────────────────────────────────────────────────────

    def _save_session(self):
        if not self.text_content.strip():
            messagebox.showinfo("Nothing to save", "Write something first.")
            return
        self.timer_running = False
        d = deep_analyze(self.text_content)
        session = {
            'id':              int(time.time()),
            'date':            datetime.now().strftime("%Y-%m-%d %H:%M"),
            'preset_name':     "Custom" if self.custom_constraints
                               else self.active_preset['name'],
            'is_custom':       bool(self.custom_constraints),
            'constraints':     list(self._constraints()),
            'excerpt':         self.text_content[:200],
            'word_count':      self.analysis['word_count'],
            'wpm':             self.analysis['wpm'],
            'compliance':      self.analysis['compliance'],
            'violations':      len(self.analysis['violations']),
            'duration':        self.elapsed,
            'lemma_richness':  d.get('lemma_richness'),
            'repeated_lemmas': len(d.get('repeated_lemmas', {})),
            'unknown_words':   d.get('unknown_words', []),
            'readability':     d.get('readability', {}),
        }
        self.history.insert(0, session)
        save_history(self.history)        # ← persist to disk immediately
        self._show_view("history")

    def _export_txt(self):
        content = self.text_widget.get("1.0", tk.END)
        r = self.deep.get('readability', {})
        lines = [
            "TETHER — SESSION EXPORT",
            "=" * 44, "",
            f"Date        : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Mode        : {'Custom' if self.custom_constraints else self.active_preset['name']}",
            f"Duration    : {fmt_time(self.elapsed)}",
            f"Words       : {self.analysis['word_count']}",
            f"WPM         : {self.analysis['wpm']}",
            f"Compliance  : {self.analysis['compliance']}%",
            f"Violations  : {len(self.analysis['violations'])}", "",
            "Linguistic",
            "-" * 20,
            f"Richness    : {self.deep.get('lemma_richness', '—')}",
            f"Repeats     : {len(self.deep.get('repeated_lemmas', {}))}",
            f"Unknown     : {len(self.deep.get('unknown_words', []))}",
            f"Flesch Ease : {r.get('flesch_ease', '—')}",
            f"Grade Level : {r.get('flesch_kincaid', '—')}",
            f"Gunning Fog : {r.get('gunning_fog', '—')}",
            f"Avg Word Len: {r.get('avg_word_len', '—')}", "",
            "Constraints",
            "-" * 20,
        ]
        for c in self._constraints():
            lines.append(f"  {json.dumps(c)}")
        lines += ["", "=" * 44, "", content]

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        os.makedirs(desktop, exist_ok=True)
        path = os.path.join(desktop, f"tether-{int(time.time())}.txt")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            messagebox.showinfo("Exported", f"Saved to Desktop:\n{path}")
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
        a  = self.analysis
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

        gp = a.get('goal_progress')
        if gp:
            pct = min(100, (gp['current'] / gp['target']) * 100)
            self._update_bar(self.goal_bar_frame, pct,
                             f"{gp['current']}/{gp['target']}",
                             GREEN if pct >= 100 else ACCENT)
        else:
            self.goal_bar_frame.pack_forget()

        if self.timer_target:
            pct  = min(100, (self.elapsed / self.timer_target) * 100)
            done = self.elapsed >= self.timer_target
            self._update_bar(self.timer_bar_frame, pct,
                             "DONE" if done
                             else fmt_time(self.timer_target-self.elapsed)+" left",
                             RED if done else BLUE)
        else:
            self.timer_bar_frame.pack_forget()
        self._update_timer_label()

    def _update_language_panel(self):
        d = self.deep
        if not d:
            return
        r        = d.get('readability', {})
        richness = d.get('lemma_richness')
        repeats  = len(d.get('repeated_lemmas', {}))
        unknown  = len(d.get('unknown_words', []))

        if richness is not None:
            col = GREEN if richness > 0.9 else AMBER if richness > 0.7 else RED
            self.lang_vars['richness'][0].set(f"{richness:.2f}")
            self.lang_vars['richness'][1].config(fg=col)
        else:
            self.lang_vars['richness'][0].set("—")

        self.lang_vars['repeats'][0].set(str(repeats))
        self.lang_vars['repeats'][1].config(fg=RED if repeats > 0 else GREEN)
        self.lang_vars['unknown'][0].set(str(unknown))
        self.lang_vars['unknown'][1].config(fg=AMBER if unknown > 0 else DIM)

        fe = r.get('flesch_ease')
        fk = r.get('flesch_kincaid')
        fg = r.get('gunning_fog')
        aw = r.get('avg_word_len')
        self.lang_vars['flesch'][0].set(
            f"{fe} ({score_readability_label(fe)})" if fe is not None else "—")
        self.lang_vars['grade'][0].set(f"Grade {fk}" if fk is not None else "—")
        self.lang_vars['fog'][0].set(str(fg) if fg is not None else "—")
        self.lang_vars['avg_wl'][0].set(
            f"{aw} letters" if aw is not None else "—")

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
                font=("Courier New", 9), anchor=tk.W, padx=16, pady=5)
            lbl.pack(fill=tk.X)
            self.warn_widgets.append(lbl)

    def _update_violations(self):
        all_v = list(self.analysis.get('violations', []))
        for lemma, wlist in list(
                self.deep.get('repeated_lemmas', {}).items())[:4]:
            all_v.append({
                'message': f"'{wlist[0]}' / '{wlist[1]}' share root '{lemma}'",
                'colour': AMBER, 'type': 'lemmaRepeat', 'prefix': '△'})
        for unk in self.deep.get('unknown_words', [])[:3]:
            all_v.append({
                'message': f'"{unk}" not in dictionary',
                'colour': BLUE, 'type': 'unknown', 'prefix': '?'})

        self.viol_text.config(state=tk.NORMAL)
        self.viol_text.delete("1.0", tk.END)
        recent = all_v[-8:]
        if recent:
            self.viol_frame.pack(fill=tk.X, side=tk.BOTTOM)
            for v in recent:
                prefix = v.get('prefix', '✗')
                colour = v.get('colour', RED)
                tag    = {RED:'red', AMBER:'amber', BLUE:'blue'}.get(colour,'red')
                self.viol_text.insert(tk.END,
                    f"{prefix}  {v['message']}\n", tag)
        else:
            self.viol_frame.pack_forget()
        self.viol_text.config(state=tk.DISABLED)

    def _update_context_bar(self):
        if self._game_mode == "game":
            if self._game_state == "active":
                if self._game_submode == "challenge" and self._game_challenge:
                    self.ctx_lbl.config(text=self._game_challenge['name'])
                elif self._game_sa_preset:
                    self.ctx_lbl.config(text=f"Score Attack — {self._game_sa_preset['name']}")
                else:
                    self.ctx_lbl.config(text="Game Mode")
            else:
                self.ctx_lbl.config(text="Game Mode")
            return
        name = "Custom" if self.custom_constraints else self.active_preset['name']
        desc = ("Custom constraints" if self.custom_constraints
                else self.active_preset['desc'])
        self.ctx_lbl.config(text=f"{name}  —  {desc}")

    def _update_preset_highlight(self):
        for pid, (row, lbl, dot) in self.preset_rows.items():
            active = (pid == self.active_preset.get('id')
                      and not self.custom_constraints)
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
    # HISTORY
    # ─────────────────────────────────────────────────────────────

    def _refresh_history(self):
        for w in self.hist_inner.winfo_children():
            w.destroy()
        if not self.history:
            tk.Label(self.hist_inner, text="No sessions saved yet.",
                     fg=DIM2, bg=BG,
                     font=("Georgia", 13, "italic"), pady=60).pack()
            return

        for s in self.history:
            card = tk.Frame(self.hist_inner, bg=BG3)
            card.pack(fill=tk.X, pady=4)
            body = tk.Frame(card, bg=BG3)
            body.pack(fill=tk.X, padx=18, pady=(12, 8))

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
                     fg=DIM2, bg=BG3,
                     font=("Courier New", 8)).pack(anchor=tk.W)

            excerpt = s['excerpt'][:140] + ("…" if len(s['excerpt']) > 140 else "")
            tk.Label(left, text=excerpt, fg="#3a3a3a", bg=BG3,
                     font=("Courier New", 9), wraplength=520,
                     justify=tk.LEFT).pack(anchor=tk.W, pady=(5, 0))

            r    = s.get('readability', {})
            ling = []
            if s.get('lemma_richness') is not None:
                ling.append(f"Richness: {s['lemma_richness']:.2f}")
            if r.get('flesch_ease') is not None:
                ling.append(f"Readability: {r['flesch_ease']} "
                            f"({score_readability_label(r['flesch_ease'])})")
            if r.get('flesch_kincaid') is not None:
                ling.append(f"Grade: {r['flesch_kincaid']}")
            if r.get('avg_word_len') is not None:
                ling.append(f"Avg word: {r['avg_word_len']} letters")
            if s.get('repeated_lemmas') is not None:
                ling.append(f"Repeats: {s['repeated_lemmas']}")
            if ling:
                tk.Label(left, text="  ·  ".join(ling),
                         fg="#2a3a2a", bg=BG3,
                         font=("Courier New", 8),
                         anchor=tk.W).pack(anchor=tk.W, pady=(3, 0))

            right  = tk.Frame(body, bg=BG3)
            right.pack(side=tk.RIGHT, padx=(12, 0))
            co     = s['compliance']
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

            if co < 90:
                self._hist_note(card,
                    "↳  Compliance below 90%. Try again, or switch to a simpler preset.",
                    DIM2)
            elif co >= 98 and s['wpm'] > 0:
                self._hist_note(card,
                    "↳  Near-perfect. Consider adding a time limit or word goal.",
                    "#1a3a2a")
            if s.get('repeated_lemmas') == 0 and s['word_count'] > 50:
                self._hist_note(card,
                    "↳  Zero repeated roots — exceptional lexical discipline.",
                    "#1a2a3a")

        self.hist_canvas.configure(
            scrollregion=self.hist_canvas.bbox("all"))

    def _hist_note(self, parent, text, fg):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, padx=18)
        tk.Label(parent, text=text, fg=fg, bg=BG3,
                 font=("Courier New", 8, "italic"),
                 anchor=tk.W, padx=18, pady=5).pack(fill=tk.X)

    def _clear_history(self):
        if not self.history:
            return
        if not messagebox.askyesno("Clear history",
                                    "Delete all saved sessions?\nThis cannot be undone."):
            return
        self.history = []
        save_history(self.history)
        self._refresh_history()

    # ─────────────────────────────────────────────────────────────
    # BUILDER LOGIC
    # ─────────────────────────────────────────────────────────────

    def _constraints_from_builder(self) -> list:
        c = []
        if self.b['wl_on'].get():
            c.append({'type':'wordLength',     'exact':      self.b['wl_n'].get()})
        if self.b['ac_on'].get():
            c.append({'type':'alphaCycle',
                      'skipX':     self.b['ac_skipx'].get(),
                      'xOptional': self.b['ac_xopt'].get()})
        if self.b['wg_on'].get():
            c.append({'type':'wordGoal',        'target':    self.b['wg_n'].get()})
        if self.b['tl_on'].get():
            c.append({'type':'timeLimit',       'seconds':   self.b['tl_mins'].get()*60})
        if self.b['sl_on'].get():
            c.append({'type':'startLetterMax',  'max':       self.b['sl_n'].get()})
        if self.b['pg_on'].get():
            c.append({'type':'pangram',         'withinWords':self.b['pg_n'].get()})
        if self.b['nr_on'].get():
            c.append({'type':'noRepeat',        'contentOnly':self.b['nr_content'].get()})
        if self.b['dc_on'].get():
            c.append({'type':'dictCheck'})
        return c

    def _on_builder_change(self, *_):
        # Guard: builder view may not be constructed yet during __init__
        if not hasattr(self, 'feas_inner'):
            return
        c  = self._constraints_from_builder()
        ws = check_feasibility(c)
        for w in self.feas_inner.winfo_children():
            w.destroy()
        if not c:
            tk.Label(self.feas_inner,
                     text="Enable constraints above to check feasibility.",
                     fg=DIM2, bg=BG3, font=SERIF_SM).pack(anchor=tk.W)
        elif not ws:
            tk.Label(self.feas_inner, text="✓  Constraints look feasible.",
                     fg=GREEN, bg=BG3,
                     font=("Courier New", 10)).pack(anchor=tk.W)
        else:
            for w in ws:
                is_err = w['level'] == 'error'
                tk.Label(self.feas_inner,
                         text=f"{'⚠  IMPOSSIBLE:' if is_err else '⚡  '} {w['msg']}",
                         fg=RED if is_err else AMBER, bg=BG3,
                         font=("Courier New", 9)).pack(anchor=tk.W, pady=2)

    def _apply_builder(self):
        c = self._constraints_from_builder()
        self.custom_constraints = c if c else None
        self._reset_session()

    # ─────────────────────────────────────────────────────────────
    # UPDATE CHECK
    # ─────────────────────────────────────────────────────────────

    def _start_update_check(self):
        """Check for updates in background thread — never blocks UI."""
        def _worker():
            latest = fetch_latest_version()
            if latest and is_newer(latest, VERSION):
                self.root.after(0, lambda: self._show_update_banner(latest))
        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _show_update_banner(self, latest: str):
        """Show the update notification banner above the main body."""
        self._update_lbl.config(
            text=f"✦  Tether v{latest} is available  —  "
                 f"github.com/{GITHUB_REPO}/releases"
        )
        self._update_banner.pack(fill=tk.X, before=self.body)

    # ─────────────────────────────────────────────────────────────
    # ONBOARDING TOUR
    # ─────────────────────────────────────────────────────────────

    def _show_onboarding(self):
        """Launch the first-run onboarding tooltip tour."""
        TetherOnboarding(self.root, self)

    # ─────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _empty_analysis() -> dict:
        return {
            'word_count': 0, 'wpm': 0, 'violations': [], 'compliance': 100,
            'letter_counts': {}, 'used_letters': set(),
            'pang_progress': None, 'goal_progress': None,
            'next_expected': None,
        }


class TetherOnboarding:
    """
    Step-by-step onboarding overlay for first-time users.
    Each step shows a floating tooltip near a key UI element.
    """

    STEPS = [
        {
            "title": "Welcome to Tether",
            "body": (
                "Tether is a writing constraint engine.\n\n"
                "You choose a rule — every word must be 4 letters, "
                "or you can only use each word once, or you must "
                "cycle through the alphabet — and Tether holds you to it.\n\n"
                "This tour will walk you through the key parts of the app."
            ),
            "anchor": "center",
        },
        {
            "title": "Choose a Mode",
            "body": (
                "The left sidebar lists all available modes.\n\n"
                "Click any mode to activate it. The coloured dot "
                "shows which mode is currently active.\n\n"
                "Start with Free Write if you just want to explore, "
                "or try Alphabet Cycle for your first real constraint."
            ),
            "anchor": "sidebar",
        },
        {
            "title": "Your Stats",
            "body": (
                "Below the mode list you'll find live stats:\n\n"
                "Words — total word count\n"
                "WPM — words per minute (once you start typing)\n"
                "Comply — what percentage of words follow the rule\n"
                "Violations — how many rule breaks so far\n"
                "Time — elapsed session time"
            ),
            "anchor": "sidebar",
        },
        {
            "title": "Next Letter",
            "body": (
                "When you're using Alphabet Cycle mode, the large "
                "letter shown here tells you what letter your next "
                "word must start with.\n\n"
                "It advances automatically as you type each word."
            ),
            "anchor": "sidebar",
        },
        {
            "title": "Language Analysis",
            "body": (
                "After a short pause in typing, Tether analyses your "
                "writing and shows:\n\n"
                "Richness — vocabulary diversity\n"
                "Repeats — overused root words\n"
                "Readability — Flesch score and grade level\n"
                "Fog index — complexity measure\n\n"
                "These update automatically as you write."
            ),
            "anchor": "sidebar",
        },
        {
            "title": "The Writing Area",
            "body": (
                "This is where you write.\n\n"
                "Violations appear as coloured messages below the "
                "text as you type:\n\n"
                "Red — hard rule breaks\n"
                "Amber — warnings\n"
                "Blue — informational\n\n"
                "The timer starts on your very first keystroke."
            ),
            "anchor": "editor",
        },
        {
            "title": "Save, Reset, Export",
            "body": (
                "The three buttons in the top bar:\n\n"
                "↺ Reset — clear the text and start a new session\n"
                "◼ Save — save this session to your history\n"
                "↓ Export — save the text as a .txt file on your Desktop\n\n"
                "Saved sessions are available in the History view."
            ),
            "anchor": "topbar",
        },
        {
            "title": "History and Builder",
            "body": (
                "The top-right navigation has three views:\n\n"
                "✎ Editor — this writing view (you're here now)\n"
                "◷ History — all your saved sessions with stats\n"
                "⊞ Builder — create your own custom constraints "
                "and save them as personal presets\n\n"
                "That's everything. Now write something."
            ),
            "anchor": "nav",
        },
    ]

    def __init__(self, root: tk.Tk, app: "ConstrainedApp"):
        self.root  = root
        self.app   = app
        self.step  = 0
        self.win   = None
        self._show_step()

    def _show_step(self):
        if self.win:
            self.win.destroy()
            self.win = None

        if self.step >= len(self.STEPS):
            mark_onboarding_seen()
            return

        s = self.STEPS[self.step]
        total = len(self.STEPS)

        # Create floating tooltip window
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.configure(bg=BORDER)
        win.attributes("-topmost", True)
        self.win = win

        # Outer frame with accent border
        outer = tk.Frame(win, bg=ACCENT, padx=1, pady=1)
        outer.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(outer, bg=BG2, padx=20, pady=16)
        inner.pack(fill=tk.BOTH, expand=True)

        # Step counter
        tk.Label(inner, text=f"STEP {self.step + 1} OF {total}",
                 fg=ACCENT, bg=BG2,
                 font=("Courier New", 8, "bold")).pack(anchor=tk.W)

        # Title
        tk.Label(inner, text=s["title"], fg=TEXT, bg=BG2,
                 font=("Courier New", 13, "bold"),
                 wraplength=340, justify=tk.LEFT).pack(anchor=tk.W, pady=(4, 0))

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=8)

        # Body text
        tk.Label(inner, text=s["body"], fg=DIM, bg=BG2,
                 font=SERIF_SM, wraplength=340,
                 justify=tk.LEFT).pack(anchor=tk.W)

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=(12, 8))

        # Navigation buttons
        btn_row = tk.Frame(inner, bg=BG2)
        btn_row.pack(fill=tk.X)

        tk.Button(btn_row, text="Skip tour", fg=DIM2, bg=BG2,
                  relief=tk.FLAT, font=("Courier New", 8), bd=0,
                  activebackground=BG2, cursor="hand2",
                  command=self._skip).pack(side=tk.LEFT)

        if self.step > 0:
            tk.Button(btn_row, text="← Back", fg=DIM, bg=BG2,
                      relief=tk.FLAT, font=("Courier New", 9), bd=0,
                      activebackground=BG2, cursor="hand2",
                      command=self._prev).pack(side=tk.RIGHT, padx=(6, 0))

        is_last = (self.step == total - 1)
        next_txt = "Done  ✓" if is_last else "Next →"
        next_fg  = GREEN  if is_last else ACCENT
        tk.Button(btn_row, text=next_txt, fg=next_fg, bg=BG2,
                  relief=tk.FLAT, font=("Courier New", 9, "bold"), bd=0,
                  activebackground=BG2, cursor="hand2",
                  command=self._next).pack(side=tk.RIGHT)

        # Position the tooltip
        self.root.update_idletasks()
        win.update_idletasks()
        self._position(win, s["anchor"])

    def _position(self, win: tk.Toplevel, anchor: str):
        """Position the tooltip near the relevant UI element."""
        rw = self.root.winfo_rootx()
        ry = self.root.winfo_rooty()
        rW = self.root.winfo_width()
        rH = self.root.winfo_height()
        wW = win.winfo_reqwidth()
        wH = win.winfo_reqheight()

        if anchor == "center":
            x = rw + (rW - wW) // 2
            y = ry + (rH - wH) // 2
        elif anchor == "sidebar":
            # Right of the sidebar
            x = rw + 240
            y = ry + 120
        elif anchor == "editor":
            # Centre of the writing area
            x = rw + (rW - wW) // 2
            y = ry + (rH - wH) // 2
        elif anchor == "topbar":
            # Below the top bar, left of centre
            x = rw + rW - wW - 40
            y = ry + 60
        elif anchor == "nav":
            # Below the nav buttons, right side
            x = rw + rW - wW - 20
            y = ry + 60
        else:
            x = rw + (rW - wW) // 2
            y = ry + (rH - wH) // 2

        # Keep on screen
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = max(0, min(x, sw - wW))
        y  = max(0, min(y, sh - wH))
        win.geometry(f"+{x}+{y}")

    def _next(self):
        self.step += 1
        self._show_step()

    def _prev(self):
        self.step = max(0, self.step - 1)
        self._show_step()

    def _skip(self):
        if self.win:
            self.win.destroy()
        mark_onboarding_seen()


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    app  = ConstrainedApp(root)
    root.mainloop()
