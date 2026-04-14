import re

from constants import (
    ALPHABET,
    AMBER,
    BLUE,
    FUNCTION_WORDS,
    RED,
    WORDS_PER_LENGTH,
)
from wordlist import WORDLIST, check_dictionary


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

LEMMA_CACHE: dict = {}


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


def score_readability_label(score: float) -> str:
    if score >= 80:
        return "easy"
    if score >= 60:
        return "standard"
    if score >= 40:
        return "difficult"
    return "very difficult"


def constraints_summary(constraints: list) -> str:
    parts = []
    for c in constraints:
        t = c['type']
        if t == 'wordLength':
            parts.append(f"{c['exact']}-letter words")
        elif t == 'alphaCycle':
            parts.append("alphabet cycle")
        elif t == 'wordGoal':
            parts.append(f"{c['target']} words")
        elif t == 'timeLimit':
            parts.append(f"{c['seconds']//60} min")
        elif t == 'startLetterMax':
            parts.append(f"max {c['max']}/letter")
        elif t == 'pangram':
            parts.append(f"pangram/{c['withinWords']}")
        elif t == 'noRepeat':
            parts.append("no repeats")
        elif t == 'dictCheck':
            parts.append("dict check")
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
                'flesch_ease': round(_textstat.flesch_reading_ease(text), 1),
                'flesch_kincaid': round(_textstat.flesch_kincaid_grade(text), 1),
                'gunning_fog': round(_textstat.gunning_fog(text), 1),
                'avg_word_len': round(
                    sum(len(clean_word(w)) for w in words_raw if clean_word(w))
                    / max(1, len([w for w in words_raw if clean_word(w)])), 1),
            }
        except Exception:
            pass

    if not SPACY_AVAILABLE or NLP is None:
        return result

    content_pos = {'NOUN', 'VERB', 'ADJ', 'ADV'}
    doc = NLP(text)
    content_tokens = [
        (token.text, token.lemma_.lower(), token.pos_)
        for token in doc
        if token.pos_ in content_pos and not token.is_stop
        and not token.is_punct and token.is_alpha
    ]
    if content_tokens:
        unique_lemmas = {lemma for _, lemma, _ in content_tokens}
        result['lemma_richness'] = round(len(unique_lemmas) / len(content_tokens), 3)
        result['content_word_count'] = len(content_tokens)
    lemma_map: dict = {}
    for word, lemma, _ in content_tokens:
        lemma_map.setdefault(lemma, []).append(word)
    result['repeated_lemmas'] = {k: v for k, v in lemma_map.items() if len(v) > 1}
    return result


def analyze_text(text: str, constraints: list, elapsed: int) -> dict:
    raw_words = get_words(text)
    words_clean = [clean_word(w) for w in raw_words]
    words = [w for w in words_clean if w]
    word_count = len(words)
    minutes = elapsed / 60
    wpm = round(word_count / minutes) if minutes > 0.1 else 0

    violations: list = []
    letter_counts: dict = {}
    used_letters: set = set()
    seen_lemmas: dict = {}

    wl = next((c for c in constraints if c['type'] == 'wordLength'), None)
    cyc = next((c for c in constraints if c['type'] == 'alphaCycle'), None)
    sl_max = next((c for c in constraints if c['type'] == 'startLetterMax'), None)
    pangram = next((c for c in constraints if c['type'] == 'pangram'), None)
    goal_c = next((c for c in constraints if c['type'] == 'wordGoal'), None)
    no_rep = next((c for c in constraints if c['type'] == 'noRepeat'), None)
    dict_c = next((c for c in constraints if c['type'] == 'dictCheck'), None)

    alpha = cycle_alpha(cyc.get('skipX', False)) if cyc else []

    clean_pos = 0
    for raw_idx, raw_w in enumerate(raw_words):
        word = words_clean[raw_idx]
        if not word:
            continue
        i = clean_pos
        raw = raw_w
        first = word[0]
        letter_counts[first] = letter_counts.get(first, 0) + 1
        for ch in word:
            used_letters.add(ch)

        alpha_len = sum(1 for c in word if c.isalpha())
        if wl and wl.get('exact') and alpha_len != wl['exact']:
            violations.append({
                'word_index': raw_idx, 'word': raw, 'type': 'wordLength',
                'message': f'"{raw}" is {alpha_len} letters (need {wl["exact"]})',
                'colour': RED})

        if cyc and alpha:
            expected = alpha[i % len(alpha)]
            x_optional = cyc.get('xOptional', True)
            if not (expected == 'x' and x_optional) and first != expected:
                violations.append({
                    'word_index': raw_idx, 'word': raw, 'type': 'alphaCycle',
                    'message': f'Word {i+1}: expected "{expected.upper()}", got "{first.upper()}"',
                    'colour': RED})

        if sl_max and letter_counts[first] > sl_max['max']:
            violations.append({
                'word_index': raw_idx, 'word': raw, 'type': 'startLetterMax',
                'message': f'"{first.upper()}" used {letter_counts[first]}x (max {sl_max["max"]})',
                'colour': RED})

        if no_rep:
            skip = no_rep.get('contentOnly', True) and word in FUNCTION_WORDS
            if not skip:
                lemma = get_lemma(word)
                if lemma in seen_lemmas and seen_lemmas[lemma] != raw:
                    violations.append({
                        'word_index': raw_idx, 'word': raw, 'type': 'noRepeat',
                        'message': f'"{raw}" repeats "{seen_lemmas[lemma]}" (same root)',
                        'colour': AMBER})
                else:
                    seen_lemmas[lemma] = raw

        if dict_c and WORDLIST and not check_dictionary(word):
            violations.append({
                'word_index': raw_idx, 'word': raw, 'type': 'dictCheck',
                'message': f'"{raw}" not found in dictionary',
                'colour': BLUE})

        clean_pos += 1

    pang_progress = None
    if pangram:
        window = words[:pangram['withinWords']]
        window_used = {ch for w in window for ch in w}
        pang_progress = {
            'window_missing': [l for l in ALPHABET if l not in window_used],
            'all_missing': [l for l in ALPHABET if l not in used_letters],
            'target': pangram['withinWords']}

    goal_progress = (
        {'current': word_count, 'target': goal_c['target']} if goal_c else None)

    next_expected = None
    if cyc and alpha:
        nxt = alpha[word_count % len(alpha)]
        next_expected = ('X*' if nxt == 'x' and cyc.get('xOptional', True)
                         else nxt.upper())

    structural_types = {'wordLength', 'alphaCycle', 'startLetterMax', 'noRepeat'}
    sv = [v for v in violations if v['type'] in structural_types]
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
    wl = next((c for c in constraints if c['type'] == 'wordLength'), None)
    goal = next((c for c in constraints if c['type'] == 'wordGoal'), None)
    time_c = next((c for c in constraints if c['type'] == 'timeLimit'), None)
    sl_max = next((c for c in constraints if c['type'] == 'startLetterMax'), None)
    cyc = next((c for c in constraints if c['type'] == 'alphaCycle'), None)
    no_rep = next((c for c in constraints if c['type'] == 'noRepeat'), None)

    if wl and wl.get('exact'):
        n = wl['exact']
        avail = WORDS_PER_LENGTH.get(n, 0)
        if avail == 0:
            warnings.append({'level': 'error',
                'msg': f'No common English words of exactly {n} letters.'})
        elif avail < 200:
            warnings.append({'level': 'warn',
                'msg': f'Only ~{avail} words of length {n} — very limited.'})

    if goal and sl_max:
        ceiling = sl_max['max'] * 26
        if goal['target'] > ceiling:
            warnings.append({'level': 'error',
                'msg': (f'Impossible: {goal["target"]} words but ceiling is '
                        f'{ceiling} ({sl_max["max"]} per letter).')})

    if goal and time_c:
        req_wpm = round(goal['target'] / (time_c['seconds'] / 60))
        if req_wpm > 120:
            warnings.append({'level': 'error',
                'msg': f'Requires {req_wpm} WPM — near-impossible.'})
        elif req_wpm > 80:
            warnings.append({'level': 'warn',
                'msg': f'Requires {req_wpm} WPM — fast typist territory.'})

    if cyc and not cyc.get('skipX') and not cyc.get('xOptional'):
        warnings.append({'level': 'warn',
            'msg': 'X is very rare as a word-starter. Consider making it optional.'})

    if cyc and wl and wl.get('exact') == 3:
        warnings.append({'level': 'warn',
            'msg': 'Cycle + 3-letter words: Q, X, Z have very few options.'})

    if no_rep and goal and goal['target'] > 500:
        warnings.append({'level': 'warn',
            'msg': f'No-repeat + {goal["target"]} words is very demanding.'})

    return warnings


def fmt_time(s: int) -> str:
    return f"{s // 60}:{s % 60:02d}"
