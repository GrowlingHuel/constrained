import os
import re


def _clean_word(word: str) -> str:
    return re.sub(r'[^a-zA-Z]', '', word).lower()


def _load_wordlist() -> set:
    wordlist = set()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wordlist.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            wordlist = {line.strip().lower() for line in f if line.strip()}
    return wordlist


WORDLIST: set = _load_wordlist()


def check_dictionary(word: str) -> bool:
    if not WORDLIST:
        return True
    return _clean_word(word) in WORDLIST
