import os


VERSION = "0.4.0"
GITHUB_REPO = "HyperArkStudios/tether"

APP_DIR = os.path.join(os.path.expanduser("~"), ".tether")
HISTORY_FILE = os.path.join(APP_DIR, "history.json")
PRESETS_FILE = os.path.join(APP_DIR, "presets.json")
ONBOARDING_FILE = os.path.join(APP_DIR, "seen_onboarding")
SCORES_FILE = os.path.join(APP_DIR, "scores.json")

BG = "#FFFFFF"
BG2 = "#F5F5F5"
BG3 = "#F0F0F0"
BORDER = "#000000"
ACCENT = "#000000"
TEXT = "#000000"
DIM = "#555555"
DIM2 = "#888888"
RED = "#000000"
GREEN = "#555555"
BLUE = "#555555"
AMBER = "#888888"

SERIF_SM = ("Courier", 9)

HC_BG = "#FFFFFF"
HC_FG = "#000000"
HC_DIM = "#555555"
HC_BOR = "#000000"

ALPHABET = list("abcdefghijklmnopqrstuvwxyz")

START_FREQ = {
    'a': 11.6, 'b': 4.5, 'c': 9.7, 'd': 5.5, 'e': 5.0, 'f': 4.8, 'g': 3.5,
    'h': 4.9, 'i': 4.4, 'j': 0.8, 'k': 1.1, 'l': 4.2, 'm': 5.5, 'n': 2.8,
    'o': 3.8, 'p': 9.0, 'q': 0.4, 'r': 4.9, 's': 12.4, 't': 8.5, 'u': 2.4,
    'v': 2.1, 'w': 4.0, 'x': 0.1, 'y': 0.5, 'z': 0.3,
}

WORDS_PER_LENGTH = {
    2: 80, 3: 900, 4: 3800, 5: 8000, 6: 15000, 7: 23000,
    8: 28000, 9: 24000, 10: 20000, 11: 15000, 12: 10000,
}

BUILTIN_PRESETS = [
    {"id": "free", "name": "Free Write", "color": "#6b7280",
     "desc": "No constraints. Just write.",
     "constraints": [], "builtin": True},
    {"id": "sprint_500", "name": "500-Word Sprint", "color": "#3b82f6",
     "desc": "Write 500 words in 10 minutes (~50 WPM).",
     "constraints": [{"type": "wordGoal", "target": 500},
                    {"type": "timeLimit", "seconds": 600}], "builtin": True},
    {"id": "sprint_1000", "name": "1000-Word Sprint", "color": "#6366f1",
     "desc": "Write 1000 words in 15 minutes (~67 WPM).",
     "constraints": [{"type": "wordGoal", "target": 1000},
                    {"type": "timeLimit", "seconds": 900}], "builtin": True},
]

_AC = {"type": "alphaCycle", "skipX": False, "xOptional": True}

GAME_CHALLENGES = [
    {"id": "first-steps", "name": "First Steps",
     "requires": None,
     "description": "Write 50 real dictionary words. A gentle warm-up.",
     "constraints": [{"type": "dictCheck"}],
     "goal": {"type": "word_count", "target": 50},
     "time_limit_seconds": 180, "difficulty_multiplier": 1.0,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 30},
         "three": {"compliance_min": 0.95, "time_remaining_min": 60, "score_min": 160}}},
    {"id": "four-letter-words", "name": "Four-Letter Words",
     "requires": None,
     "description": "Write 100 unique real 4-letter words. You have 6 minutes.",
     "constraints": [{"type": "wordLength", "exact": 4}],
     "goal": {"type": "word_count", "target": 100},
     "time_limit_seconds": 360, "difficulty_multiplier": 1.5,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 30},
         "three": {"compliance_min": 0.95, "time_remaining_min": 60, "score_min": 550}}},
    {"id": "four-letter-sprint", "name": "Four-Letter Sprint",
     "requires": "four-letter-words",
     "description": "150 unique real 4-letter words. Five minutes. This is hard.",
     "constraints": [{"type": "wordLength", "exact": 4}],
     "goal": {"type": "word_count", "target": 150},
     "time_limit_seconds": 300, "difficulty_multiplier": 2.0,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 30},
         "three": {"compliance_min": 0.95, "time_remaining_min": 60, "score_min": 1000}}},
    {"id": "threes-company", "name": "Three's Company",
     "requires": None,
     "description": "Write 100 words — every word exactly 3 letters. You have 5 minutes.",
     "constraints": [{"type": "wordLength", "exact": 3}],
     "goal": {"type": "word_count", "target": 100},
     "time_limit_seconds": 300, "difficulty_multiplier": 1.5,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 30},
         "three": {"compliance_min": 0.95, "time_remaining_min": 90, "score_min": 420}}},
    {"id": "five-alive", "name": "Five Alive",
     "requires": None,
     "description": "Write 120 words of exactly 5 letters each. Six minutes.",
     "constraints": [{"type": "wordLength", "exact": 5}],
     "goal": {"type": "word_count", "target": 120},
     "time_limit_seconds": 360, "difficulty_multiplier": 1.5,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 30},
         "three": {"compliance_min": 0.95, "time_remaining_min": 90, "score_min": 900}}},
    {"id": "alphabet-run", "name": "Alphabet Run",
     "requires": None,
     "description": "Write one full A-to-Z alphabet cycle (26 words). Three minutes.",
     "constraints": [_AC],
     "goal": {"type": "word_count", "target": 26},
     "time_limit_seconds": 180, "difficulty_multiplier": 2.0,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 30},
         "three": {"compliance_min": 1.00, "time_remaining_min": 60, "score_min": 220}}},
    {"id": "double-alphabet", "name": "Double Alphabet",
     "requires": "alphabet-run",
     "description": "Two full A-to-Z cycles (52 words). Five minutes.",
     "constraints": [_AC],
     "goal": {"type": "word_count", "target": 52},
     "time_limit_seconds": 300, "difficulty_multiplier": 2.0,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 30},
         "three": {"compliance_min": 1.00, "time_remaining_min": 90, "score_min": 500}}},
    {"id": "no-repeats", "name": "No Repeats",
     "requires": None,
     "description": "Write 200 words without reusing any root word. Eight minutes.",
     "constraints": [{"type": "noRepeat", "contentOnly": True}],
     "goal": {"type": "word_count", "target": 200},
     "time_limit_seconds": 480, "difficulty_multiplier": 1.5,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 60},
         "three": {"compliance_min": 0.95, "time_remaining_min": 120, "score_min": 1200}}},
    {"id": "pangram-dash", "name": "Pangram Dash",
     "requires": None,
     "description": "Use every letter of the alphabet within 50 words. Write 100 total. Four minutes.",
     "constraints": [{"type": "pangram", "withinWords": 50}],
     "goal": {"type": "word_count", "target": 100},
     "time_limit_seconds": 240, "difficulty_multiplier": 1.5,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 30},
         "three": {"compliance_min": 0.95, "time_remaining_min": 60, "score_min": 500}}},
    {"id": "letter-budget", "name": "Letter Budget",
     "requires": None,
     "description": "Write up to 150 words. Every letter of the alphabet except X must begin at least 2 of your words. 6 minutes.",
     "constraints": [{"type": "startLetterMax", "max": 3}],
     "goal": {"type": "word_count", "target": 150},
     "time_limit_seconds": 360, "difficulty_multiplier": 1.25,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 30},
         "three": {"compliance_min": 0.95, "time_remaining_min": 90, "score_min": 550}}},
    {"id": "short-and-sweet", "name": "Short and Sweet",
     "requires": "threes-company",
     "description": "Write 80 real 3-letter words. Four minutes.",
     "constraints": [{"type": "wordLength", "exact": 3}, {"type": "dictCheck"}],
     "goal": {"type": "word_count", "target": 80},
     "time_limit_seconds": 240, "difficulty_multiplier": 1.5,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 30},
         "three": {"compliance_min": 0.95, "time_remaining_min": 60, "score_min": 360}}},
    {"id": "verbose", "name": "Verbose",
     "requires": "five-alive",
     "description": "Write 60 words of exactly 7 letters each. Five minutes.",
     "constraints": [{"type": "wordLength", "exact": 7}],
     "goal": {"type": "word_count", "target": 60},
     "time_limit_seconds": 300, "difficulty_multiplier": 1.5,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 30},
         "three": {"compliance_min": 0.95, "time_remaining_min": 90, "score_min": 600}}},
    {"id": "marathon", "name": "Marathon",
     "requires": "no-repeats",
     "description": "Write 300 unique real words (no root repeats). Twelve minutes.",
     "constraints": [{"type": "noRepeat", "contentOnly": True}, {"type": "dictCheck"}],
     "goal": {"type": "word_count", "target": 300},
     "time_limit_seconds": 720, "difficulty_multiplier": 1.5,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 60},
         "three": {"compliance_min": 0.95, "time_remaining_min": 180, "score_min": 2200}}},
    {"id": "tight-alphabet", "name": "Tight Alphabet",
     "requires": "double-alphabet",
     "description": "Two alphabet cycles — every word must be a real dictionary word. Four minutes.",
     "constraints": [_AC, {"type": "dictCheck"}],
     "goal": {"type": "word_count", "target": 52},
     "time_limit_seconds": 240, "difficulty_multiplier": 2.0,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 30},
         "three": {"compliance_min": 1.00, "time_remaining_min": 60, "score_min": 500}}},
    {"id": "the-gauntlet", "name": "The Gauntlet",
     "requires": "four-letter-sprint",
     "description": "150 words: 4 letters, alphabet cycle, no repeats. Ten minutes.",
     "constraints": [{"type": "wordLength", "exact": 4},
                    _AC,
                    {"type": "noRepeat", "contentOnly": True}],
     "goal": {"type": "word_count", "target": 150},
     "time_limit_seconds": 600, "difficulty_multiplier": 4.5,
     "star_thresholds": {
         "one": {"compliance_min": 0.70},
         "two": {"compliance_min": 0.85, "time_remaining_min": 60},
         "three": {"compliance_min": 0.95, "time_remaining_min": 180, "score_min": 2500}}},
]

GAME_SA_PRESETS = [
    {"id": "sa-blitz", "name": "Blitz",
     "desc": "Write using only 4-letter words. Fast and focused — how many points can you score in 2 minutes?",
     "constraints": [{"type": "wordLength", "exact": 4}],
     "default_duration": 120},
    {"id": "sa-endurance", "name": "Endurance",
     "desc": "No repeated words, and every word must be real. How long can you keep going without repeating yourself?",
     "constraints": [{"type": "noRepeat", "contentOnly": True}, {"type": "dictCheck"}],
     "default_duration": None},
    {"id": "sa-alpha-grind", "name": "Alphabet Grind",
     "desc": "Each word must start with the next letter of the alphabet, and every word must be real. Cycle after cycle — keep the streak alive.",
     "constraints": [_AC, {"type": "dictCheck"}],
     "default_duration": None},
    {"id": "sa-word-hoarder", "name": "Word Hoarder",
     "desc": "Words must be 5+ letters, and use every letter of the alphabet within 100 words. Score big with long, rare words.",
     "constraints": [{"type": "wordLength", "exact": 5}, {"type": "pangram", "withinWords": 100}],
     "default_duration": 300},
    {"id": "sa-freeform", "name": "Free Attack",
     "desc": "No constraints — pure score chasing. Every word counts, longer and rarer words score more.",
     "constraints": [],
     "default_duration": 300},
]

FUNCTION_WORDS = {
    'a', 'an', 'the', 'and', 'but', 'or', 'nor', 'for', 'yet', 'so',
    'in', 'on', 'at', 'to', 'of', 'with', 'by', 'from', 'up', 'about',
    'into', 'through', 'during', 'before', 'after', 'i', 'me', 'my',
    'we', 'our', 'you', 'your', 'he', 'him', 'his', 'she', 'her', 'it',
    'its', 'they', 'them', 'their', 'what', 'which', 'who', 'this',
    'that', 'these', 'those', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'not',
    'no', 'if', 'as', 'us', 'than', 'then', 'when', 'where', 'how',
}
