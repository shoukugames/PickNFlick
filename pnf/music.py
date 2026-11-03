"""Procedural background music.

Every track is an original chiptune composed from a small "recipe" and
synthesized at run time, so the game ships no audio files. A recipe sets the
tempo, key, mode, chord progressions for each song section, instruments, bass
style, arpeggio pattern, drum groove, swing and a melody seed.

Song form (28 bars, loops seamlessly):
    A  (8 bars)  verse: main melody, groove
    B  (8 bars)  chorus: new catchy melody with harmony, fuller drums, pad
    A2 (8 bars)  verse again with a second instrument doubling an octave up
    C  (4 bars)  breakdown: bells + pad + light drums, snare-roll build back to A

Tracks are generated on first use and cached in memory.
"""
import array
import math
import random
import sys
import threading
import time
import warnings

import pygame

try:  # fast C mixing (Python <= 3.12); a slow pure-Python shim is used otherwise
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import audioop
except ImportError:  # pragma: no cover
    audioop = None

VOLUME = 0.40

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
}

# Instrument presets: wave, low-pass (1 = off, smaller = mellower), vibrato (semitones), decay (/s), gate
PRESETS = {
    "bright": ("sq25", 0.45, 0.20, 1.0, 0.92),
    "soft":   ("sq50", 0.22, 0.18, 0.9, 0.92),
    "reed":   ("sq12", 0.38, 0.16, 1.1, 0.90),
    "flute":  ("tri",  1.00, 0.28, 0.6, 0.94),
    "brass":  ("saw",  0.30, 0.14, 0.8, 0.92),
    "bell":   ("sine", 1.00, 0.00, 4.5, 0.98),
    "pluck":  ("sq25", 0.35, 0.00, 7.0, 0.85),
    "bass":   ("sq50", 0.14, 0.00, 2.2, 0.80),
    "tbass":  ("tri",  1.00, 0.00, 1.2, 0.90),
    "pad":    ("tri",  0.60, 0.00, 0.2, 1.00),
}

# Section chord progressions are scale degrees (0 = tonic), one chord per bar.
# A and B are played twice (8 bars each), C once (4 bars).
TRACKS = {
    "menu":    dict(bpm=118, root=60, scale="major",      A=[0, 4, 5, 3], B=[3, 4, 2, 5], C=[3, 4, 3, 4],
                    lead="soft",   lead2="bright", bass="octave", arp="updown",  drums="bounce",  swing=0.0,  seed=11),
    "level1":  dict(bpm=112, root=65, scale="major",      A=[0, 3, 4, 0], B=[5, 3, 0, 4], C=[3, 4, 5, 4],
                    lead="flute",  lead2="pluck",  bass="sync",   arp=None,      drums="light",   swing=0.18, seed=21),
    "level2":  dict(bpm=120, root=67, scale="major",      A=[0, 5, 3, 4], B=[3, 4, 0, 5], C=[1, 4, 1, 4],
                    lead="bright", lead2="soft",   bass="pump",   arp="up",      drums="bounce",  swing=0.0,  seed=32),
    "level3":  dict(bpm=124, root=62, scale="mixolydian", A=[0, 6, 3, 0], B=[3, 0, 6, 4], C=[3, 6, 3, 4],
                    lead="reed",   lead2="bright", bass="octave", arp="alberti", drums="shuffle", swing=0.20, seed=43),
    "level4":  dict(bpm=126, root=57, scale="minor",      A=[0, 5, 2, 6], B=[3, 4, 5, 6], C=[5, 6, 5, 6],
                    lead="brass",  lead2="bell",   bass="sync",   arp="broken",  drums="funk",    swing=0.0,  seed=54),
    "level5":  dict(bpm=130, root=70, scale="major",      A=[0, 5, 1, 4], B=[3, 4, 2, 5], C=[1, 2, 3, 4],
                    lead="soft",   lead2="reed",   bass="octave", arp="up",      drums="disco",   swing=0.0,  seed=65),
    "level6":  dict(bpm=134, root=64, scale="dorian",     A=[0, 3, 0, 3], B=[6, 5, 3, 4], C=[3, 4, 3, 6],
                    lead="bright", lead2="brass",  bass="funk",   arp="broken",  drums="drive",   swing=0.06, seed=76),
    "level7":  dict(bpm=138, root=60, scale="major",      A=[0, 2, 3, 4], B=[5, 3, 1, 4], C=[3, 4, 3, 4],
                    lead="reed",   lead2="flute",  bass="walk",   arp="updown",  drums="gallop",  swing=0.16, seed=87),
    "level8":  dict(bpm=144, root=55, scale="minor",      A=[0, 5, 6, 4], B=[3, 6, 2, 5], C=[5, 6, 5, 6],
                    lead="brass",  lead2="bright", bass="funk",   arp="alberti", drums="funk",    swing=0.0,  seed=98),
    "level9":  dict(bpm=150, root=62, scale="major",      A=[0, 3, 5, 4], B=[3, 4, 2, 5], C=[1, 4, 1, 4],
                    lead="bright", lead2="reed",   bass="octave", arp="up",      drums="disco",   swing=0.0,  seed=109),
    "level10": dict(bpm=158, root=64, scale="minor",      A=[0, 5, 2, 6], B=[3, 6, 0, 4], C=[5, 6, 5, 6],
                    lead="brass",  lead2="bright", bass="gallop", arp="up",      drums="drive",   swing=0.0,  seed=120),
    "victory": dict(bpm=128, root=65, scale="major",      A=[0, 3, 4, 0], B=[3, 4, 5, 4], C=[3, 4, 3, 4],
                    lead="brass",  lead2="bright", bass="octave", arp="updown",  drums="march",   swing=0.0,  seed=131),
}

# 1-bar rhythms: x = note starts, - = held, . = rest (16 sixteenth-note steps)
RHY_VERSE = [
    "x-x-x--x--x-x---", "x--x--x-x-x-x---", "x-xxx-x-x---x-x-", "x---x-x-x--x-x--",
    "x-x-x-x-x--xx---", "..x-x-x-x--x-x--", "x--x--x---x-xx--", "xx-x-x--x-x-x---",
]
RHY_CHORUS = [
    "x---x---x-x-x---", "x--x--x-x-------", "x-x-x---x---x---", "x---x--x--x-x---",
    "x-----x-x-x-x---", "x--x--x---x-----",
]
RHY_CADENCE = ["x-x-x---x-------", "x--x--x-x-------", "x-x-x-x-x-------", "x---x---x-------"]

GROOVES = {   # per section: instrument -> 16-step pattern
    "light":   {"A": {"k": "x.......x.......", "c": "....x.......x...", "h": "..x...x...x...x."},
                "B": {"k": "x.....x.x.......", "c": "....x.......x...", "h": "x.x.x.x.x.x.x.x."}},
    "bounce":  {"A": {"k": "x.....x.x.......", "s": "....x.......x...", "h": "x.x.x.x.x.x.x.x."},
                "B": {"k": "x...x...x...x...", "c": "....x.......x...", "o": "..x...x...x...x."}},
    "disco":   {"A": {"k": "x...x...x...x...", "c": "....x.......x...", "o": "..x...x...x...x."},
                "B": {"k": "x...x...x...x...", "s": "....x.......x...", "c": "....x.......x...", "h": "xxxxxxxxxxxxxxxx"}},
    "funk":    {"A": {"k": "x..x..x...x..x..", "s": "....x..g.g..x..g", "h": "x.x.x.x.x.x.x.x."},
                "B": {"k": "x..x..x.x..x..x.", "s": "....x.......x...", "c": "....x.......x...", "h": "xxxxxxxxxxxxxxxx"}},
    "shuffle": {"A": {"k": "x.....x.x.......", "s": "....x.......x...", "h": "x.xxx.xxx.xxx.xx"},
                "B": {"k": "x...x...x...x...", "s": "....x.......x..g", "o": "..x...x...x...x."}},
    "drive":   {"A": {"k": "x.x...x.x.x...x.", "s": "....x.......x...", "h": "xxxxxxxxxxxxxxxx"},
                "B": {"k": "x...x...x...x...", "s": "....x.......x...", "c": "....x.......x...",
                      "o": "..x...x...x...x.", "h": "x.x.x.x.x.x.x.x."}},
    "gallop":  {"A": {"k": "x.xx..x.x.xx..x.", "s": "....x.......x...", "h": "x.x.x.x.x.x.x.x."},
                "B": {"k": "x.x.x.x.x.x.x.x.", "s": "....x.......x...", "c": "....x.......x...", "o": "..x...x...x...x."}},
    "march":   {"A": {"k": "x.......x.......", "s": "....x..x....x.xx", "h": "x.x.x.x.x.x.x.x."},
                "B": {"k": "x...x...x...x...", "s": "....x.......x...", "c": "....x.......x...", "o": "..x...x...x...x."}},
}
BREAKDOWN = {"k": "x.........x.....", "c": "....x.......x...", "h": "..x...x...x...x."}
DRUM_VOL = {"k": 0.50, "s": 0.26, "g": 0.09, "c": 0.22, "h": 0.07, "o": 0.06, "x": 0.10}
ARPS = {"up": [0, 1, 2, 3], "updown": [0, 1, 2, 3, 2, 1], "alberti": [0, 2, 1, 2], "broken": [0, 2, 3, 1]}


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def parse_rhythm(r):
    """'x--x.' -> [(start, length), ...]"""
    out = []
    for i, ch in enumerate(r):
        if ch == "x":
            out.append([i, 1])
        elif ch == "-" and out:
            out[-1][1] += 1
    return [tuple(o) for o in out]


# ----------------------------------------------------------------------------- mixing backend
class _Shim:  # pragma: no cover - only used where the C audioop module is missing
    @staticmethod
    def _a(data, w):
        return array.array("h" if w == 2 else "i", data)

    def add(self, a, b, w):
        x, y = self._a(a, w), self._a(b, w)
        lim = 32767 if w == 2 else 2147483647
        return array.array(x.typecode, (max(-lim - 1, min(lim, p + q)) for p, q in zip(x, y))).tobytes()

    def mul(self, a, w, f):
        x = self._a(a, w)
        lim = 32767 if w == 2 else 2147483647
        return array.array(x.typecode, (max(-lim - 1, min(lim, int(p * f))) for p in x)).tobytes()

    def max(self, a, w):
        x = self._a(a, w)
        return max((abs(p) for p in x), default=0)

    def lin2lin(self, a, w1, w2):
        x = self._a(a, w1)
        if w1 == 2 and w2 == 4:
            return array.array("i", (p << 16 for p in x)).tobytes()
        return array.array("h", (p >> 16 for p in x)).tobytes()

    def tostereo(self, a, w, lf, rf):
        x = self._a(a, w)
        out = array.array(x.typecode, bytes(2 * len(x) * x.itemsize))
        out[0::2] = array.array(x.typecode, (int(p * lf) for p in x))
        out[1::2] = array.array(x.typecode, (int(p * rf) for p in x))
        return out.tobytes()


AO = audioop if audioop is not None else _Shim()


# ----------------------------------------------------------------------------- composer
class Composer:
    def __init__(self, rate):
        self.rate = rate
        self.note_cache = {}
        self.drums = {}
        self.pause_fn = None   # called between bars so a background render stays polite

    # -- synthesis ---------------------------------------------------------
    TBL = 1024
    BLOCK = 64

    def table(self, preset, midi):
        """One cycle of the (low-passed) waveform as floats, indexed by phase."""
        key = ("tbl", preset, midi)
        hit = self.note_cache.get(key)
        if hit is not None:
            return hit
        wave, lp = PRESETS[preset][:2]
        N = self.TBL
        duty = {"sq12": 0.125, "sq25": 0.25, "sq50": 0.5}.get(wave, 0.5)
        raw = []
        for i in range(N):
            p = i / N
            if wave == "tri":
                v = 4 * p - 1 if p < 0.5 else 3 - 4 * p
            elif wave == "saw":
                v = 2 * p - 1
            elif wave == "sine":
                v = math.sin(6.283185307 * p) + 0.25 * math.sin(12.566370614 * p)
            else:
                v = 1.0 if p < duty else -1.0
            raw.append(v)
        if lp < 1.0:   # steady-state response of a one-pole low-pass at this pitch
            samples_per_step = self.rate / (midi_hz(midi) * N)
            a = 1.0 - (1.0 - lp) ** samples_per_step
            y = 0.0
            out = [0.0] * N
            for _ in range(3):
                for i in range(N):
                    y += a * (raw[i] - y)
                    out[i] = y
            mx = max(abs(v) for v in out) or 1.0
            raw = [v / mx for v in out]
        self.note_cache[key] = raw
        return raw

    def cycle(self, tbl, midi, total):
        """Steady tone: render a few whole cycles that fit an integer sample count, then repeat."""
        period = self.rate / midi_hz(midi)
        k = min(range(1, 65), key=lambda c: abs(c * period - round(c * period)))
        m = max(1, round(k * period))
        step = self.TBL * k / m
        mask = self.TBL - 1
        chunk = array.array("h", [tbl[int(i * step) & mask] for i in range(m)]).tobytes()
        reps = total // m + 1
        return (chunk * reps)[:2 * total]

    def lfo(self, w, n):
        cur = getattr(self, "_lfo", None)
        if cur is None or len(cur) < n:
            m = max(n, int(self.rate * 4))
            cur = self._lfo = [math.cos(w * i) for i in range(m)]
        return cur

    def tone(self, preset, midi, n, vol):
        """One note: n samples of sustain + a short release tail (16-bit mono bytes)."""
        key = (preset, midi, n, vol)
        hit = self.note_cache.get(key)
        if hit is not None:
            return hit
        wave, lp, vib, decay, gate = PRESETS[preset]
        rate = self.rate
        N, B = self.TBL, self.BLOCK
        on = max(1, int(n * gate))
        rel = int(0.045 * rate)
        total = on + rel
        inc = midi_hz(midi) / rate * N
        tbl = [int(v * 32767 * vol) for v in self.table(preset, midi)]
        mask = N - 1
        if vib:
            vk = 2 ** (vib / 12.0) - 1
            vs = min(total, int(0.12 * rate))
            # phase of a sine-vibrato oscillator, integrated analytically:
            # p(i) = inc*i + inc*vk/w * (cos(w*vs) - cos(w*i))   for i >= vs
            w = 6.283185307 * 5.5 / rate
            lfo = self.lfo(w, total)
            A = inc * vk / w
            c0 = lfo[vs] if vs < total else 1.0
            raw = array.array("h", [tbl[int(i * inc) & mask] for i in range(vs)]
                              + [tbl[int(i * inc + A * (c0 - lfo[i])) & mask] for i in range(vs, total)])
            data = raw.tobytes()
        else:
            data = self.cycle(tbl, midi, total)
        # envelope, applied per block: attack, exponential decay, linear release
        att = 0.005 * rate
        parts = []
        mul = AO.mul
        for b0 in range(0, total, B):
            i = b0 + B / 2
            e = math.exp(-decay * i / rate)
            if i < att:
                e *= i / att
            if i >= on:
                e *= max(0.0, 1.0 - (i - on) / rel)
            parts.append(mul(data[2 * b0:2 * (b0 + B)], 2, e))
        data = b"".join(parts)
        self.note_cache[key] = data
        return data

    def drum(self, kind):
        hit = self.drums.get(kind)
        if hit is not None:
            return hit
        rate = self.rate
        rng = random.Random(len(kind) * 977 + ord(kind[0]))
        length = int({"k": 0.25, "s": 0.2, "g": 0.1, "c": 0.22, "h": 0.05, "o": 0.2, "x": 0.9}[kind] * rate)
        buf = array.array("h", bytes(2 * length))
        ph = prev = lpv = 0.0
        for i in range(length):
            t = i / rate
            if kind == "k":
                ph += (48 + 130 * math.exp(-t * 32)) / rate
                s = math.sin(6.283185307 * ph) * math.exp(-t * 11)
                if i < 0.003 * rate:
                    s += rng.uniform(-0.4, 0.4)
            elif kind in "sg":
                ph += 185 / rate
                s = (rng.uniform(-1, 1) * 0.8 + math.sin(6.283185307 * ph) * 0.45) * math.exp(-t * (22 if kind == "s" else 40))
            elif kind == "c":   # clap: three quick bursts, then a tail
                w = rng.uniform(-1, 1)
                hp = w - prev
                prev = w
                burst = t % 0.011 < 0.006 if t < 0.03 else True
                s = hp * 0.9 * (math.exp(-(t - 0.03) * 18) if t >= 0.03 else 1.0) * burst
            else:               # hats / crash: high-passed noise
                w = rng.uniform(-1, 1)
                lpv += 0.5 * (w - lpv)
                s = (w - lpv) * 1.6 * math.exp(-t * {"h": 70, "o": 16, "x": 4.5}[kind])
            buf[i] = int(max(-1.0, min(1.0, s)) * 32767)
        data = buf.tobytes()
        self.drums[kind] = data
        return data

    # -- melody ------------------------------------------------------------
    @staticmethod
    def deg_midi(root, scale, d):
        octave, idx = divmod(d, len(scale))
        return root + 12 * octave + scale[idx]

    @staticmethod
    def chord_tones(chord):
        return {chord % 7, (chord + 2) % 7, (chord + 4) % 7}

    def nearest_tone(self, chord, target, lo=-3, hi=10):
        tones = self.chord_tones(chord)
        best = None
        for d in range(lo, hi + 1):
            if d % 7 in tones and (best is None or abs(d - target) < abs(best - target)):
                best = d
        return best

    def motif(self, rng, pool):
        onsets = parse_rhythm(rng.choice(pool))
        steps = [0] + [rng.choice([-1, -1, 1, 1, 2, -2, 0, 3, -3, 4]) for _ in range(len(onsets) - 1)]
        return onsets, steps

    @staticmethod
    def vary(m, rng):
        onsets, steps = m
        steps = list(steps)
        for i in range(max(1, len(steps) - 2), len(steps)):
            steps[i] = rng.choice([-2, -1, 1, 2, 3])
        return onsets, steps

    def realize(self, m, chord, prev, lift=0):
        onsets, steps = m
        d = self.nearest_tone(chord, prev + lift)
        notes = []
        for (st, ln), dv in zip(onsets, steps):
            d += dv
            if st % 4 == 0:   # strong beat: land on a chord tone
                d = self.nearest_tone(chord, d)
            d = max(-3, min(10, d))
            notes.append((st, d, ln))
        return notes, d

    def cadence(self, rng, chord, prev, final):
        onsets = parse_rhythm(rng.choice(RHY_CADENCE))
        target = self.nearest_tone(chord, prev) if not final else self.nearest_tone(chord, 0 if prev < 5 else 7)
        notes = []
        k = len(onsets)
        for i, (st, ln) in enumerate(onsets):
            left = k - 1 - i
            d = target + (left if prev > target else -left)
            notes.append((st, max(-3, min(10, d)), ln))
        return notes, target

    def compose(self, spec, rng):
        """Return {section: [bar notes, ...]} where bar notes are (step, degree, length)."""
        A, B = spec["A"], spec["B"]
        m = self.motif(rng, RHY_VERSE)
        n = self.motif(rng, RHY_VERSE)
        m2 = self.vary(m, rng)
        p = self.motif(rng, RHY_CHORUS)
        q = self.motif(rng, RHY_CHORUS)
        q2 = self.vary(q, rng)
        plan = {
            "A": [(m, 0), (m, 0), (n, 0), "cad", (m, 0), (m2, 0), (n, 2), "end"],
            "B": [(p, 2), (q, 0), (p, 0), "cad", (p, 2), (q2, 0), (p, 2), "end"],
        }
        out = {}
        for sec, prog in (("A", A * 2), ("B", B * 2)):
            prev = 2 if sec == "A" else 4
            bars = []
            for item, chord in zip(plan[sec], prog):
                if item in ("cad", "end"):
                    notes, prev = self.cadence(rng, chord, prev, item == "end")
                else:
                    notes, prev = self.realize(item[0], chord, prev, item[1])
                bars.append(notes)
            out[sec] = bars
        return out

    # -- rendering ---------------------------------------------------------
    def render(self, name, channels=2):
        spec = TRACKS[name]
        rng = random.Random(spec["seed"])
        rate = self.rate
        L = rate * 60.0 / spec["bpm"] / 4
        swing = spec.get("swing", 0.0)
        scale, root = SCALES[spec["scale"]], spec["root"]
        sections = [("A", spec["A"] * 2), ("B", spec["B"] * 2), ("A2", spec["A"] * 2), ("C", spec["C"])]
        bars = [(sec, ch, i) for sec, prog in sections for i, ch in enumerate(prog)]
        n_steps = 16 * len(bars)

        def pos(st):
            pair, odd = divmod(st, 2)
            return int(pair * 2 * L + odd * L * (1 + swing))

        total = pos(n_steps)
        voices = {k: bytearray(2 * total) for k in ("lead", "lead2", "harm", "bass", "arp", "pad", "drums", "echo")}
        PAN = {"lead": (1.0, 0.8), "lead2": (0.7, 1.0), "harm": (0.55, 1.0), "bass": (1.0, 1.0),
               "arp": (0.55, 1.0), "pad": (0.9, 0.9), "drums": (1.0, 1.0), "echo": (1.0, 0.45)}

        def place(voice, start, data):
            buf = voices[voice]
            start %= total
            a = 2 * start
            b = min(len(buf), a + len(data))
            buf[a:b] = AO.add(bytes(buf[a:b]), data[:b - a], 2)
            rest = data[b - a:]
            if rest:   # tails wrap around so the loop point is seamless
                buf[:len(rest)] = AO.add(bytes(buf[:len(rest)]), rest[:len(buf)], 2)

        def note(voice, preset, midi, st, ln, vol):
            place(voice, pos(st), self.tone(preset, midi, pos(st + ln) - pos(st), vol))

        mel = self.compose(spec, rng)
        grooves = GROOVES[spec["drums"]]
        arp_pat = ARPS.get(spec["arp"] or "up")
        bass_style = spec["bass"]
        lead_root = root + 12
        sec_start = 0
        for b, (sec, chord, i) in enumerate(bars):
            if self.pause_fn:
                self.pause_fn()
            s0 = 16 * b
            last_in_sec = i == (3 if sec == "C" else 7)
            nxt = bars[(b + 1) % len(bars)][1]
            # --- melody
            if sec in ("A", "B", "A2"):
                notes = mel["A" if sec == "A2" else sec][i]
                for st, d, ln in notes:
                    midi = self.deg_midi(lead_root, scale, d)
                    if sec == "A2":
                        note("lead", spec["lead"], midi, s0 + st, ln, 0.15)
                        note("lead2", spec["lead2"], midi + 12, s0 + st, ln, 0.06)
                    else:
                        note("lead", spec["lead"], midi, s0 + st, ln, 0.16)
                    if sec == "B":
                        note("harm", spec["lead2"], self.deg_midi(lead_root, scale, d - 2), s0 + st, ln, 0.07)
                    # dotted-eighth echo
                    place("echo", pos(s0 + st + 3), AO.mul(self.tone(spec["lead"], midi, pos(s0 + st + ln) - pos(s0 + st), 0.15 if sec == "A2" else 0.16), 2, 0.33))
            # --- bass
            r = self.deg_midi(root - 24, scale, chord)
            fifth = self.deg_midi(root - 24, scale, chord + 4)
            third = self.deg_midi(root - 24, scale, chord + 2)
            approach = self.deg_midi(root - 24, scale, nxt - 1 if nxt > chord else nxt + 1) if nxt != chord else fifth
            preset, bvol = ("bass", 0.20)
            if sec == "C":
                pat = [(0, r, 8), (8, fifth, 8)]
                preset, bvol = "tbass", 0.30
            elif bass_style == "octave":
                pat = [(k * 2, r + (12 if k % 2 else 0), 2) for k in range(7)] + [(14, approach, 2)]
            elif bass_style == "sync":
                pat = [(0, r, 3), (3, r, 3), (6, r + 12, 2), (8, fifth, 3), (11, r, 3), (14, approach, 2)]
            elif bass_style == "pump":
                pat = [(k * 2, r, 2) for k in range(7)] + [(14, approach, 2)]
            elif bass_style == "funk":
                pat = [(0, r, 2), (3, r + 12, 1), (4, r, 2), (6, fifth, 1), (8, r, 2), (10, r + 12, 1),
                       (11, r, 2), (13, third, 1), (14, approach, 2)]
            elif bass_style == "gallop":
                pat = []
                for k in range(4):
                    pat += [(k * 4, r if k < 3 else fifth, 2), (k * 4 + 2, r + 12, 1), (k * 4 + 3, r, 1)]
            else:  # walk
                pat = [(0, r, 4), (4, third, 4), (8, fifth, 4), (12, approach, 4)]
                preset, bvol = "tbass", 0.30
            for st, m, ln in pat:
                note("bass", preset, m, s0 + st, ln, bvol)
            # --- arpeggio
            tones = [self.deg_midi(root, scale, chord + k) for k in (0, 2, 4, 7)]
            if sec == "C":
                for k in range(8):
                    note("arp", "bell", tones[arp_pat[k % len(arp_pat)]] + 12, s0 + k * 2, 2, 0.07)
            elif sec == "A2" or (sec == "A" and spec["arp"]):
                for k in range(16):
                    note("arp", "pluck", tones[arp_pat[k % len(arp_pat)]], s0 + k, 1, 0.05)
            elif sec == "B":
                for k in range(8):
                    note("arp", "pluck", tones[arp_pat[k % len(arp_pat)]] + 12, s0 + k * 2, 2, 0.04)
            # --- pad
            if sec in ("B", "C"):
                for k in (0, 2, 4):
                    note("pad", "pad", self.deg_midi(root - 12, scale, chord + k), s0, 16, 0.045)
            # --- drums
            g = BREAKDOWN if sec == "C" else grooves["B" if sec == "B" else "A"]
            hits = {}
            for inst, pat_s in g.items():
                for k, c in enumerate(pat_s):
                    if c == "x" or (inst == "s" and c == "g"):
                        hits.setdefault(k, []).append("g" if c == "g" else inst)
            if sec == "A2" and spec["drums"] != "disco":
                for k in (2, 6, 10, 14):
                    hits.setdefault(k, []).append("o")
            if last_in_sec:   # fill: snare roll into the next section
                roll_from = 8 if sec == "C" else 12
                for k in range(roll_from, 16):
                    hits[k] = ["s"] + (["k"] if k in (roll_from, 14) else [])
            if i == 0 and sec != "C":
                hits.setdefault(0, []).append("x")
            for k, insts in hits.items():
                for inst in insts:
                    vol = DRUM_VOL[inst]
                    if inst == "h" and k % 2:
                        vol *= 0.6
                    if last_in_sec and inst == "s" and k >= 8:
                        vol *= 0.55 + 0.45 * (k - 8) / 7.0
                    place("drums", pos(s0 + k), AO.mul(self.drum(inst), 2, vol))
            sec_start = s0

        # --- stereo mix with headroom, then normalise (in chunks, so a background
        # render never holds the interpreter for long)
        CH = 16384
        chunks = []
        peak = 1
        for a in range(0, total, CH):
            if self.pause_fn:
                self.pause_fn()
            out = None
            for k, buf in voices.items():
                w4 = AO.mul(AO.lin2lin(bytes(buf[2 * a:2 * (a + CH)]), 2, 4), 4, 1 / 16.0)
                if channels == 2:
                    lf, rf = PAN[k]
                    w4 = AO.tostereo(w4, 4, lf, rf)
                out = w4 if out is None else AO.add(out, w4, 4)
            peak = max(peak, AO.max(out, 4))
            chunks.append(out)
        gain = min(16.0, 0.89 * 2147483647 / peak)
        res = []
        for c in chunks:
            res.append(AO.lin2lin(AO.mul(c, 4, gain), 4, 2))
        return b"".join(res)


# ----------------------------------------------------------------------------- player
class Music:
    """Plays one looping track at a time on a reserved mixer channel."""

    def __init__(self, audio, enabled=True):
        self.audio = audio
        self.enabled = enabled
        self.current = None
        self.cache = {}
        self.channel = None
        self.paused = False
        self.lock = threading.Lock()
        self._worker = None
        if audio.ok:
            try:
                pygame.mixer.set_reserved(1)
                self.channel = pygame.mixer.Channel(0)
                self.composer = Composer(audio.rate)
            except pygame.error:
                self.channel = None

    @property
    def ok(self):
        return self.channel is not None

    def prepare(self, name, background=False):
        if not self.ok or name not in TRACKS:
            return None
        with self.lock:
            self.composer.pause_fn = (lambda: time.sleep(0.004)) if background else None
            snd = self.cache.get(name)
            if snd is None:
                data = self.composer.render(name, 2 if self.audio.ch == 2 else 1)
                snd = pygame.mixer.Sound(buffer=data)
                self.cache[name] = snd
                self.composer.note_cache.clear()   # notes are tempo-specific; free the memory
        return snd

    def prefetch(self, names):
        """Compose tracks in a background thread so level changes never stall."""
        if not self.ok or (self._worker and self._worker.is_alive()):
            return
        todo = [n for n in names if n not in self.cache]

        def work():
            old = sys.getswitchinterval()
            sys.setswitchinterval(0.0005)   # hand the GIL back to the game loop quickly
            try:
                for n in todo:
                    self.prepare(n, background=True)
            finally:
                sys.setswitchinterval(old)
        self._worker = threading.Thread(target=work, name="music-prefetch", daemon=True)
        self._worker.start()

    def play(self, name):
        if name == self.current and (not self.ok or self.channel.get_busy() or not self.enabled):
            return
        self.current = name
        self.paused = False
        if not (self.ok and self.enabled):
            return
        snd = self.prepare(name)
        if snd is not None:
            self.channel.set_volume(VOLUME)
            self.channel.play(snd, loops=-1, fade_ms=500)
            self.channel.unpause()
            self.prefetch(["level%d" % i for i in range(1, 11)] + ["victory", "menu"])

    def stop(self, fade_ms=500):
        self.current = None
        if self.ok:
            self.channel.fadeout(fade_ms)

    def pause(self):
        if self.ok and not self.paused:
            self.channel.pause()
            self.paused = True

    def resume(self):
        if self.ok and self.paused:
            self.channel.unpause()
            self.paused = False

    def set_enabled(self, on):
        self.enabled = on
        if not self.ok:
            return
        if on:
            name, self.current = self.current, None
            if name:
                self.play(name)
        else:
            self.channel.stop()
