import json
import os
import time

from analyzer import clean_word


def _load_word_rarity() -> dict:
    word_rarity = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "word_rarity.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                word_rarity = json.load(f)
        except Exception:
            pass
    return word_rarity


WORD_RARITY: dict = _load_word_rarity()

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
        self.difficulty = difficulty
        self.diff_mult = (preset_mult if preset_mult is not None
                          else compute_difficulty_mult(constraints))
        self.streak = 0
        self.peak_streak = 0
        self.peak_mult = 1.0
        self.score = 0.0
        self.total_words = 0
        self.compliant_words = 0
        self.unique_compliant_words = 0
        self._seen_raw_words: set = set()
        self._consec_viols = 0
        self._last_viol_time = 0.0
        self.per_word_scores: list = []

    def streak_mult(self) -> float:
        for threshold, m in self._STREAK_TIERS:
            if self.streak >= threshold:
                return m
        return 1.0

    def score_word(self, word: str, compliant: bool,
                   now: float = None, raw_word: str = "") -> float:
        if now is None:
            now = time.monotonic()
        self.total_words += 1
        if compliant:
            self.streak += 1
            self.compliant_words += 1
            raw_key = (raw_word.lower() if raw_word else word)
            if raw_key not in self._seen_raw_words:
                self.unique_compliant_words += 1
                self._seen_raw_words.add(raw_key)
            self.peak_streak = max(self.peak_streak, self.streak)
            self.peak_mult = max(self.peak_mult, self.streak_mult())
            self._consec_viols = 0
            base = len(clean_word(word))
            pts = base * self.diff_mult * self.streak_mult() * \
                WORD_RARITY.get(word.lower(), 1.0)
            self.score += pts
            self.per_word_scores.append(pts)
            return pts
        else:
            self.streak = 0
            if now - self._last_viol_time > 30:
                self._consec_viols = 0
            self._consec_viols += 1
            self._last_viol_time = now
            deduction = 0.0
            if self.difficulty == 'medium':
                deduction = 5.0
            elif self.difficulty == 'hard':
                deduction = min(5.0 * (2 ** (self._consec_viols - 1)), 40.0)
            self.score = max(0.0, self.score - deduction)
            self.per_word_scores.append(-deduction)
            return -deduction

    @property
    def compliance(self) -> float:
        return (self.compliant_words / self.total_words
                if self.total_words else 1.0)

    def int_score(self) -> int:
        return int(self.score)


def append_score(data: dict, category: str, key: str,
                 difficulty: str, entry: dict):
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
