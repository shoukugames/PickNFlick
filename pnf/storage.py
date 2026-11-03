"""Persistent settings, top-10 scores and parent progress data (JSON)."""
import copy
import json
import os
import time

from .resources import data_dir

MAX_SESSIONS = 30
MAX_SCORES = 10

DEFAULT = {
    "settings": {"lang": "en", "difficulty": "easy", "sound": True, "music": True},
    "level_select_unlocked": False,
    "highscores": [],
    "progress": {
        "games_played": 0,
        "play_seconds": 0.0,
        "words_completed": 0,
        "letters_correct": 0,
        "letters_wrong": 0,
        "tissues_hit": 0,
        "flicks": 0,
        "best_score": 0,
        "best_level": {"easy": 0, "medium": 0, "hard": 0},
        "completed": {"easy": False, "medium": False, "hard": False},
        "sessions": [],
        "trouble_letters": {},
        "words": {},
    },
}


def _merge(default, loaded):
    """Fill missing keys from `default` so older save files keep working."""
    if not isinstance(default, dict) or not isinstance(loaded, dict):
        return loaded if type(loaded) is type(default) else copy.deepcopy(default)
    out = copy.deepcopy(default)
    for k, v in loaded.items():
        out[k] = _merge(default[k], v) if k in default else v
    return out


class Store:
    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), "save.json")
        self.data = copy.deepcopy(DEFAULT)
        self.load()

    # -- io -------------------------------------------------------------
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = _merge(DEFAULT, json.load(f))
        except (OSError, ValueError):
            self.data = copy.deepcopy(DEFAULT)

    def save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except OSError:
            pass

    # -- accessors ------------------------------------------------------
    @property
    def settings(self):
        return self.data["settings"]

    @property
    def progress(self):
        return self.data["progress"]

    @property
    def highscores(self):
        return self.data["highscores"]

    # -- high scores ----------------------------------------------------
    def qualifies(self, score):
        if score <= 0:
            return False
        hs = self.highscores
        return len(hs) < MAX_SCORES or score > hs[-1]["score"]

    def add_highscore(self, name, score, level, difficulty):
        entry = {
            "name": name[:12] or "PLAYER",
            "score": int(score),
            "level": int(level),
            "difficulty": difficulty,
            "date": time.strftime("%Y-%m-%d"),
        }
        hs = self.highscores
        hs.append(entry)
        hs.sort(key=lambda e: e["score"], reverse=True)
        del hs[MAX_SCORES:]
        self.save()
        return hs.index(entry) if entry in hs else -1

    # -- progress -------------------------------------------------------
    def record_session(self, session):
        p = self.progress
        p["games_played"] += 1
        p["play_seconds"] += session["seconds"]
        p["best_score"] = max(p["best_score"], session["score"])
        p["sessions"].append(session)
        del p["sessions"][:-MAX_SESSIONS]
        self.save()

    def reset_progress(self):
        self.data["progress"] = copy.deepcopy(DEFAULT["progress"])
        self.save()
