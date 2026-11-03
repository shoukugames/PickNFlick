"""Run with:  python3 -m unittest discover -s tests"""
import os
import sys
import tempfile
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pnf import config as C  # noqa: E402
from pnf.belt import Belt  # noqa: E402
from pnf.i18n import STRINGS  # noqa: E402
from pnf.storage import Store  # noqa: E402
from pnf.words import WORDS, pick_words, word_length  # noqa: E402


class WordTests(unittest.TestCase):
    def test_every_level_has_enough_words_of_right_length(self):
        for diff in C.DIFFICULTIES:
            for level in range(1, C.LEVELS + 1):
                n = word_length(level)
                pool = WORDS[diff][n]
                self.assertGreaterEqual(len(pool), C.WORDS_PER_LEVEL, (diff, level))
                for w, meaning in pool:
                    self.assertEqual(len(w), n, w)
                    self.assertTrue(w.isalpha() and w.isascii(), w)
                    self.assertTrue(meaning, w)

    def test_pick_words_unique_and_upper(self):
        words = pick_words("easy", 3, 3)
        self.assertEqual(len({w for w, _ in words}), 3)
        self.assertTrue(all(w.isupper() for w, _ in words))


class I18nTests(unittest.TestCase):
    def test_same_keys(self):
        self.assertEqual(set(STRINGS["en"]), set(STRINGS["ja"]))


class StoreTests(unittest.TestCase):
    def test_top10_sorted_and_capped(self):
        with tempfile.TemporaryDirectory() as d:
            s = Store(os.path.join(d, "save.json"))
            for i in range(15):
                s.add_highscore("P%d" % i, i * 100, 1, "easy")
            self.assertEqual(len(s.highscores), 10)
            self.assertEqual(s.highscores[0]["score"], 1400)
            self.assertFalse(s.qualifies(100))
            self.assertTrue(s.qualifies(10000))
            s2 = Store(os.path.join(d, "save.json"))
            self.assertEqual(s2.highscores, s.highscores)

    def test_corrupt_file_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "save.json")
            with open(p, "w") as f:
                f.write("{not json")
            s = Store(p)
            self.assertEqual(s.settings["lang"], "en")


class BeltTests(unittest.TestCase):
    def assign(self, belt, item):
        item.set("letter", "A")
        self.assigned += 1

    def test_pingpong_reverses_at_half(self):
        self.assigned = 0
        b = Belt(2, 400, 100.0, 1, "pingpong", 200, self.assign)
        for _ in range(60 * 12):
            b.update(1 / 60)
            self.assertGreaterEqual(b.offset, 0)
            self.assertLessEqual(b.offset, (C.GAL_X1 - C.GAL_X0) / 2 + 1e-6)
        self.assertEqual(b.pp_dir in (1, -1), True)

    def test_loop_directions_and_refill(self):
        self.assigned = 0
        top = Belt(0, 180, 240.0, 1, "loop", 168, self.assign)
        mid = Belt(1, 290, 150.0, -1, "loop", 186, self.assign)
        start = self.assigned
        self.assertGreater(top.velocity, 0)
        self.assertLess(mid.velocity, 0)
        for _ in range(60 * 10):
            top.update(1 / 60)
            mid.update(1 / 60)
        self.assertGreater(self.assigned, start)

    def test_hit_test(self):
        self.assigned = 0
        b = Belt(0, 180, 0.0, 1, "loop", 168, self.assign)
        it = next(i for i in b.items if i.visible)
        self.assertIs(b.hit_test(it.x + 5, 39), it)
        it.knock()
        self.assertIsNot(b.hit_test(it.x, 5), it)



class ScoringTests(unittest.TestCase):
    def test_belt_points_top_middle_bottom(self):
        self.assertEqual([b["points"] for b in C.BELTS], [50, 30, 20])


class MusicTests(unittest.TestCase):
    def test_every_track_renders_without_clipping(self):
        import array
        from pnf.music import TRACKS, Composer
        comp = Composer(22050)
        self.assertEqual({"level%d" % i for i in range(1, 11)} - set(TRACKS), set())
        for name in TRACKS:
            data = comp.render(name)
            self.assertGreater(len(data), 22050 * 2 * 8, name)      # > 8 seconds
            peak = max(abs(v) for v in array.array("h", data))
            self.assertLess(peak, 32767, name)
            self.assertGreater(peak, 5000, name)

    def test_levels_have_distinct_recipes(self):
        from pnf.music import TRACKS
        recipes = {tuple(sorted((k, str(v)) for k, v in TRACKS["level%d" % i].items() if k != "seed"))
                   for i in range(1, 11)}
        self.assertEqual(len(recipes), 10)


if __name__ == "__main__":
    unittest.main()
