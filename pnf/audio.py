"""Tiny synthesizer: every sound effect is generated at start-up (no audio files)."""
import array
import math
import random

import pygame


class Audio:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.ok = False
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 2, 512)
            freq, size, ch = pygame.mixer.get_init()
            if size != -16:
                return
            self.rate, self.ch = freq, ch
            self._build()
            self.ok = True
        except (pygame.error, NotImplementedError):
            self.ok = False

    # -- synthesis helpers ------------------------------------------------
    def _tone(self, f0, f1, dur, wave="sine", vol=0.6, decay=3.0, noise=0.0, attack=0.004):
        n = max(1, int(self.rate * dur))
        out = []
        phase = 0.0
        att = max(1, int(attack * self.rate))
        two_pi = 2 * math.pi
        for i in range(n):
            t = i / n
            f = f0 + (f1 - f0) * t
            phase += two_pi * f / self.rate
            if wave == "square":
                s = 1.0 if math.sin(phase) > 0 else -1.0
            elif wave == "tri":
                s = 2 / math.pi * math.asin(math.sin(phase))
            elif wave == "noise":
                s = random.uniform(-1, 1)
            else:
                s = math.sin(phase)
            if noise:
                s = s * (1 - noise) + random.uniform(-1, 1) * noise
            env = math.exp(-decay * t) * min(1.0, i / att)
            out.append(s * env * vol)
        return out

    @staticmethod
    def _silence(rate, dur):
        return [0.0] * int(rate * dur)

    def _make(self, samples):
        buf = array.array("h")
        for s in samples:
            v = int(max(-1.0, min(1.0, s)) * 32000)
            buf.extend([v] * self.ch)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def _seq(self, notes, dur, wave="tri", vol=0.45, decay=2.5):
        out = []
        for f in notes:
            out += self._tone(f, f, dur, wave, vol, decay)
        return out

    def _build(self):
        r = self.rate
        T = self._tone
        self.sounds = {
            "flick": self._make(T(1300, 260, 0.09, "sine", 0.6, 4, noise=0.25)),
            "splat": self._make(T(180, 60, 0.18, "noise", 0.5, 6)),
            "correct": self._make(T(880, 880, 0.08, "tri", 0.5, 2) + T(1320, 1320, 0.16, "tri", 0.5, 3)),
            "wrong": self._make(T(160, 120, 0.28, "square", 0.25, 2)),
            "tissue": self._make(T(420, 300, 0.22, "square", 0.25, 1) + T(300, 180, 0.4, "square", 0.25, 2)),
            "pick": self._make(T(90, 140, 0.18, "sine", 0.6, 3, noise=0.5)),
            "reload": self._make(T(300, 1000, 0.2, "sine", 0.5, 1) + T(1000, 1000, 0.06, "tri", 0.4, 6)),
            "word": self._make(self._seq([523, 659, 784, 1047], 0.09)),
            "level": self._make(self._seq([523, 659, 784, 659, 784, 1047, 1047], 0.11)),
            "boom": self._make(T(120, 40, 0.5, "noise", 0.55, 5)),
            "move": self._make(T(660, 660, 0.04, "tri", 0.3, 5)),
            "select": self._make(T(520, 1040, 0.09, "tri", 0.4, 3)),
            "tick": self._make(T(1500, 1500, 0.03, "sine", 0.25, 8)),
            "over": self._make(self._seq([392, 330, 262, 196], 0.18, "square", 0.22, 1.5)),
            "empty": self._make(T(220, 200, 0.06, "square", 0.15, 5)),
        }

    def play(self, name):
        if self.ok and self.enabled and name in self.sounds:
            self.sounds[name].play()
