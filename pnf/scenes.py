"""Menus and non-gameplay screens."""
import math
import random
import string

import pygame

from . import __version__
from . import config as C
from . import gfx
from .base import Scene
from .belt import Belt
from .words import word_length

ENTER_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER)


def is_enter(e):
    return e.type == pygame.KEYDOWN and e.key in ENTER_KEYS


def is_back(e):
    return e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE) + ENTER_KEYS


class DecorBelts:
    """Animated conveyor belts used as the menu backdrop."""

    def __init__(self, ys=(592, 650, 708)):
        self.belts = []
        for i, b in enumerate(C.BELTS):
            self.belts.append(Belt(i, ys[i], b["speed"] * 0.5, b["dir"], b["mode"], b["spacing"],
                                   self.assign, x0=0, x1=C.W))

    @staticmethod
    def assign(belt, item):
        r = random.random()
        if r < 0.15:
            item.set("empty")
        elif r < 0.22:
            item.set("tissue")
        else:
            item.set("letter", random.choice(string.ascii_uppercase))

    def update(self, dt):
        for b in self.belts:
            b.update(dt)

    def draw(self, surf):
        for i, b in enumerate(self.belts):
            gfx.draw_track(surf, 0, C.W, b.y, b.chain, C.BELT_COLORS[i])
            for it in b.items:
                if it.visible and it.kind == "letter":
                    gfx.draw_tile(surf, int(it.x), b.y, it.char, C.BELT_COLORS[i])
                elif it.visible and it.kind == "tissue":
                    gfx.draw_tissue(surf, int(it.x), b.y)


def draw_title(surf, app, t, y=66):
    title = app.t("title")
    size = gfx.fit_size(title, 72, C.W - 260)
    bob = math.sin(t * 2.5) * 4
    gfx.text(surf, title, size, C.YELLOW, (C.W // 2, y + bob), outline=6, ocolor=C.INK)
    gfx.text(surf, app.t("subtitle"), 26, C.WHITE, (C.W // 2, y + 52), outline=3, ocolor=C.INK)
    gfx.draw_booger(surf, C.W // 2 - gfx.text_width(title, size) // 2 - 50, y + bob, 18, math.sin(t * 4) * 2)
    gfx.draw_booger(surf, C.W // 2 + gfx.text_width(title, size) // 2 + 50, y - bob, 18, math.cos(t * 4) * 2)


def header(surf, app, key, t):
    gfx.draw_background(surf, t)
    gfx.text(surf, app.t(key), 54, C.YELLOW, (C.W // 2, 56), outline=5, ocolor=C.INK)


def footer(surf, s):
    strip = pygame.Surface((C.W, 44), pygame.SRCALPHA)
    strip.fill((12, 6, 24, 215))
    surf.blit(strip, (0, C.H - 48))
    gfx.text(surf, s, 22, (210, 200, 230), (C.W // 2, C.H - 26), outline=2, ocolor=C.INK)


# =========================================================================== Menu
class MenuScene(Scene):
    ITEMS = ["start", "level_select", "difficulty", "language", "sound", "music", "howto", "scores",
             "parents", "credits", "quit"]

    def __init__(self, app, sel=0):
        super().__init__(app)
        self.sel = sel
        self.decor = DecorBelts()
        self.locked_flash = 0.0

    @property
    def unlocked(self):
        return self.app.store.data["level_select_unlocked"]

    def label(self, item):
        s = self.app.store.settings
        if item == "difficulty":
            return "%s:  %s" % (self.t_("menu_difficulty"), self.t_("diff_" + s["difficulty"]))
        if item == "language":
            return "%s:  %s" % (self.t_("menu_language"), self.t_("lang_name"))
        if item == "sound":
            return "%s:  %s" % (self.t_("menu_sound"), self.t_("on") if s["sound"] else self.t_("off"))
        if item == "music":
            return "%s:  %s" % (self.t_("menu_music"), self.t_("on") if s["music"] else self.t_("off"))
        return self.t_("menu_" + item)

    def change(self, item, step):
        s = self.app.store.settings
        if item == "difficulty":
            i = C.DIFFICULTIES.index(s["difficulty"])
            s["difficulty"] = C.DIFFICULTIES[(i + step) % len(C.DIFFICULTIES)]
        elif item == "language":
            s["lang"] = "ja" if s["lang"] == "en" else "en"
        elif item == "sound":
            s["sound"] = not s["sound"]
            self.app.audio.enabled = s["sound"]
        elif item == "music":
            s["music"] = not s["music"]
            self.app.music.set_enabled(s["music"])
        else:
            return
        self.app.store.save()
        self.app.audio.play("move")

    def handle(self, e):
        if e.type != pygame.KEYDOWN:
            return
        item = self.ITEMS[self.sel]
        if e.key == pygame.K_UP:
            self.sel = (self.sel - 1) % len(self.ITEMS)
            self.app.audio.play("move")
        elif e.key == pygame.K_DOWN:
            self.sel = (self.sel + 1) % len(self.ITEMS)
            self.app.audio.play("move")
        elif e.key == pygame.K_LEFT:
            self.change(item, -1)
        elif e.key == pygame.K_RIGHT:
            self.change(item, 1)
        elif e.key in ENTER_KEYS or e.key == pygame.K_SPACE:
            self.activate(item)
        elif e.key == pygame.K_ESCAPE:
            self.sel = len(self.ITEMS) - 1

    def activate(self, item):
        app = self.app
        if item in ("difficulty", "language", "sound", "music"):
            self.change(item, 1)
            return
        if item == "level_select" and not self.unlocked:
            self.locked_flash = 2.0
            app.audio.play("wrong")
            return
        app.audio.play("select")
        if item == "start":
            from .game import GameScene
            app.set_scene(GameScene(app, 1))
        elif item == "level_select":
            app.set_scene(LevelSelectScene(app))
        elif item == "howto":
            app.set_scene(HowToScene(app))
        elif item == "scores":
            app.set_scene(HighScoresScene(app))
        elif item == "parents":
            app.set_scene(ParentsScene(app))
        elif item == "credits":
            app.set_scene(CreditsScene(app))
        elif item == "quit":
            app.running = False

    def update(self, dt):
        super().update(dt)
        self.decor.update(dt)
        self.locked_flash = max(0.0, self.locked_flash - dt)

    def draw(self, surf):
        gfx.draw_background(surf, self.t)
        self.decor.draw(surf)
        draw_title(surf, self.app, self.t)
        y0, step = 166, 34
        w = 600
        gfx.panel(surf, (C.W // 2 - w // 2 - 10, y0 - 26, w + 20, step * len(self.ITEMS) + 16),
                  (30, 16, 50), C.INK, 18, 3, alpha=210)
        for i, item in enumerate(self.ITEMS):
            y = y0 + i * step
            sel = i == self.sel
            locked = item == "level_select" and not self.unlocked
            s = self.label(item)
            if sel:
                surf.blit(gfx.glow((255, 214, 10), 60, 0.35), (C.W // 2 - w // 2 - 60, y - 60))
                surf.blit(gfx.glow((255, 214, 10), 60, 0.35), (C.W // 2 + w // 2 - 60, y - 60))
                gfx.pill(surf, (C.W // 2 - w // 2, y - 16, w, 32), (255, 214, 10), C.INK, 14, 2)
            col = C.INK if sel else ((140, 130, 160) if locked else C.WHITE)
            size = gfx.fit_size(s, 26, w - 80)
            gfx.text(surf, s, size, col, (C.W // 2, y))
            if locked:
                gfx.draw_lock(surf, C.W // 2 + gfx.text_width(s, size) // 2 + 22, y + 2)
            if sel and item in ("difficulty", "language", "sound", "music"):
                gfx.draw_arrow(surf, C.W // 2 - w // 2 + 22, y, "left", 9, C.INK)
                gfx.draw_arrow(surf, C.W // 2 + w // 2 - 22, y, "right", 9, C.INK)
        if self.locked_flash > 0 or (self.ITEMS[self.sel] == "level_select" and not self.unlocked):
            gfx.text(surf, self.t_("menu_locked"), 22, (255, 160, 160), (C.W // 2, y0 + step * len(self.ITEMS) + 8),
                     outline=2, ocolor=C.INK)
        footer(surf, self.t_("menu_hint"))
        gfx.text(surf, "v" + __version__, 18, (150, 140, 170), (C.W - 12, C.H - 12), anchor="bottomright")


# ===================================================================== Level select
class LevelSelectScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.sel = 0

    def handle(self, e):
        if e.type != pygame.KEYDOWN:
            return
        if e.key == pygame.K_ESCAPE:
            self.app.set_scene(MenuScene(self.app, 1))
        elif e.key == pygame.K_LEFT:
            self.sel = (self.sel - 1) % C.LEVELS
        elif e.key == pygame.K_RIGHT:
            self.sel = (self.sel + 1) % C.LEVELS
        elif e.key in (pygame.K_UP, pygame.K_DOWN):
            self.sel = (self.sel + 5) % C.LEVELS
        elif e.key in ENTER_KEYS or e.key == pygame.K_SPACE:
            from .game import GameScene
            self.app.audio.play("select")
            self.app.set_scene(GameScene(self.app, self.sel + 1))
            return
        else:
            return
        self.app.audio.play("move")

    def draw(self, surf):
        header(surf, self.app, "levelsel_title", self.t)
        diff = self.app.store.settings["difficulty"]
        gfx.text(surf, "%s: %s" % (self.t_("menu_difficulty"), self.t_("diff_" + diff)), 26, C.WHITE,
                 (C.W // 2, 118), outline=2, ocolor=C.INK)
        bw, bh, gap = 190, 150, 30
        sx = C.W // 2 - (5 * bw + 4 * gap) // 2
        for i in range(C.LEVELS):
            col, row = i % 5, i // 5
            r = pygame.Rect(sx + col * (bw + gap), 170 + row * (bh + 40), bw, bh)
            sel = i == self.sel
            if sel:
                surf.blit(gfx.glow((255, 214, 10), 150, 0.5), (r.centerx - 150, r.centery - 150))
            gfx.panel(surf, r, C.YELLOW if sel else C.CREAM, C.INK, 18, 5 if sel else 3)
            gfx.text(surf, str(i + 1), 64, C.INK, (r.centerx, r.centery - 14))
            gfx.text(surf, self.t_("levelsel_letters", n=word_length(i + 1)), 22, (90, 60, 140),
                     (r.centerx, r.bottom - 24))
        footer(surf, self.t_("levelsel_hint"))


# ======================================================================= How to play
class HowToScene(Scene):
    def handle(self, e):
        if is_back(e):
            self.app.set_scene(MenuScene(self.app, 6))

    def draw(self, surf):
        header(surf, self.app, "howto_title", self.t)
        gfx.panel(surf, (110, 110, C.W - 220, 520), (30, 16, 50), C.INK, 18, 3, alpha=220)
        for i, line in enumerate(self.t_("howto")):
            col = C.YELLOW if i in (6, 7) else C.WHITE
            gfx.text(surf, line, gfx.fit_size(line, 26, C.W - 280), col, (150, 150 + i * 48), anchor="midleft")
        # little demo icons
        gfx.draw_tissue(surf, C.W - 190, 455, scale=0.9)
        gfx.draw_booger(surf, C.W - 190, 330, 16)
        footer(surf, self.t_("back_hint"))


# ======================================================================= High scores
class HighScoresScene(Scene):
    def __init__(self, app, highlight=-1):
        super().__init__(app)
        self.highlight = highlight

    def handle(self, e):
        if is_back(e):
            self.app.set_scene(MenuScene(self.app, 7 if self.highlight < 0 else 0))

    def draw(self, surf):
        header(surf, self.app, "scores_title", self.t)
        hs = self.app.store.highscores
        gfx.panel(surf, (110, 105, C.W - 220, 545), (30, 16, 50), C.INK, 18, 3, alpha=220)
        cols = [(150, "col_rank", "midleft"), (230, "col_name", "midleft"), (620, "col_score", "midright"),
                (740, "col_level", "center"), (900, "col_mode", "center"), (1110, "col_date", "midright")]
        for x, key, anchor in cols:
            gfx.text(surf, self.t_(key), 24, C.YELLOW, (x, 135), anchor=anchor)
        pygame.draw.line(surf, C.YELLOW, (140, 156), (C.W - 140, 156), 2)
        if not hs:
            gfx.text(surf, self.t_("no_scores"), 28, C.WHITE, (C.W // 2, 360))
        for i, e in enumerate(hs):
            y = 186 + i * 44
            if i == self.highlight:
                a = 120 + int(80 * math.sin(self.t * 6))
                hl = pygame.Surface((C.W - 260, 40), pygame.SRCALPHA)
                hl.fill((255, 214, 10, a))
                surf.blit(hl, (130, y - 20))
            medal = [(255, 215, 0), (200, 200, 210), (205, 127, 50)]
            col = medal[i] if i < 3 else C.WHITE
            gfx.text(surf, "%d" % (i + 1), 26, col, (150, y), anchor="midleft")
            gfx.text(surf, e["name"], gfx.fit_size(e["name"], 26, 300), C.WHITE, (230, y), anchor="midleft")
            gfx.text(surf, "%d" % e["score"], 26, C.YELLOW, (620, y), anchor="midright")
            gfx.text(surf, "%d" % e["level"], 26, C.WHITE, (740, y))
            gfx.text(surf, self.t_("short_" + e["difficulty"]), 22, C.BELT_COLORS[1], (900, y))
            gfx.text(surf, e["date"], 22, (200, 190, 220), (1110, y), anchor="midright")
        footer(surf, self.t_("back_hint"))


# ========================================================================= Credits
class CreditsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.fw = gfx.Fireworks()

    def handle(self, e):
        if is_back(e):
            self.app.set_scene(MenuScene(self.app, 9))

    def update(self, dt):
        super().update(dt)
        self.fw.update(dt)

    def draw(self, surf):
        header(surf, self.app, "credits_title", self.t)
        self.fw.draw(surf)
        cx = C.W // 2
        gfx.panel(surf, (cx - 440, 110, 880, 510), C.CREAM, C.INK, 22, 4)
        gfx.draw_nose(surf, cx, 200, self.t)
        gfx.text(surf, self.t_("credits_created"), 26, (120, 90, 150), (cx, 300))
        gfx.text(surf, self.t_("credits_names"), 44, C.INK, (cx, 345))
        pygame.draw.line(surf, (200, 180, 160), (cx - 360, 392), (cx + 360, 392), 2)
        gfx.text(surf, self.t_("credits_contact"), 26, (120, 90, 150), (cx, 420))
        gfx.text(surf, self.t_("credits_web") + "  https://shoukugames.org/", 30, (30, 90, 200), (cx, 462))
        gfx.text(surf, self.t_("credits_email") + "  info@shoukugames.org", 30, (30, 90, 200), (cx, 504))
        gfx.text(surf, self.t_("credits_font"), 18, (110, 100, 120), (cx, 556))
        gfx.text(surf, self.t_("credits_license") + "   ·   " + self.t_("version", v=__version__), 18,
                 (110, 100, 120), (cx, 584))
        footer(surf, self.t_("back_hint"))


# ======================================================================= Name entry
class NameEntryScene(Scene):
    MAX_LEN = 12

    def __init__(self, app, score, level, difficulty):
        super().__init__(app)
        self.score, self.level, self.difficulty = score, level, difficulty
        self.name = ""
        self.composing = ""
        pygame.key.start_text_input()
        pygame.key.set_text_input_rect(pygame.Rect(C.W // 2 - 250, 330, 500, 70))

    def finish(self):
        pygame.key.stop_text_input()
        name = self.name.strip() or "PLAYER"
        idx = self.app.store.add_highscore(name, self.score, self.level, self.difficulty)
        self.app.audio.play("select")
        self.app.set_scene(HighScoresScene(self.app, idx))

    def handle(self, e):
        if e.type == pygame.TEXTINPUT:
            for ch in e.text:
                if ch.isprintable() and len(self.name) < self.MAX_LEN:
                    self.name += ch
            self.composing = ""
        elif e.type == pygame.TEXTEDITING:
            self.composing = e.text
        elif e.type == pygame.KEYDOWN:
            if e.key in ENTER_KEYS and not self.composing:
                self.finish()
            elif e.key == pygame.K_BACKSPACE and not self.composing:
                self.name = self.name[:-1]

    def draw(self, surf):
        gfx.draw_background(surf, self.t)
        cx = C.W // 2
        gfx.text(surf, self.t_("new_high"), 66, C.YELLOW, (cx, 130), outline=5, ocolor=C.INK)
        gfx.text(surf, "%s  %d" % (self.t_("score"), self.score), 40, C.WHITE, (cx, 210), outline=3, ocolor=C.INK)
        gfx.text(surf, self.t_("enter_name"), 32, C.WHITE, (cx, 290), outline=2, ocolor=C.INK)
        box = pygame.Rect(cx - 250, 330, 500, 70)
        gfx.panel(surf, box, C.CREAM, C.INK, 14, 4)
        shown = self.name + self.composing
        caret = "|" if int(self.t * 2) % 2 == 0 else " "
        gfx.text(surf, shown + caret, gfx.fit_size(shown + "|", 40, 470), C.INK, box.center)
        gfx.draw_booger(surf, cx - 300, 365, 18)
        gfx.draw_booger(surf, cx + 300, 365, 18)
        footer(surf, self.t_("name_hint"))


# ========================================================================= Victory
class VictoryScene(Scene):
    music = "victory"

    def __init__(self, app, score, level, difficulty):
        super().__init__(app)
        self.score, self.level, self.difficulty = score, level, difficulty
        self.fw = gfx.Fireworks(on_boom=lambda: app.audio.play("boom"))
        app.audio.play("level")

    def handle(self, e):
        if is_enter(e) and self.t > 1.5:
            if self.app.store.qualifies(self.score):
                self.app.set_scene(NameEntryScene(self.app, self.score, self.level, self.difficulty))
            else:
                self.app.set_scene(MenuScene(self.app))

    def update(self, dt):
        super().update(dt)
        self.fw.update(dt)

    def draw(self, surf):
        surf.blit(gfx.vgradient(C.W, C.H, (8, 6, 30), (30, 14, 60)), (0, 0))
        surf.blit(gfx.vignette(C.W, C.H, 200), (0, 0))
        self.fw.draw(surf)
        cx = C.W // 2
        s = 1 + 0.05 * math.sin(self.t * 4)
        gfx.text(surf, self.t_("congrats"), int(84 * s), C.YELLOW, (cx, 180), outline=6, ocolor=C.INK)
        gfx.text(surf, self.t_("congrats_sub"), 38, C.WHITE, (cx, 270), outline=3, ocolor=C.INK)
        gfx.text(surf, self.t_("final_score", s=self.score), 44, C.GREEN, (cx, 345), outline=3, ocolor=C.INK)
        gfx.text(surf, self.t_("thanks"), 52, (255, 143, 171), (cx, 430), outline=4, ocolor=C.INK)
        gfx.text(surf, self.t_("unlocked"), 24, (200, 220, 255), (cx, 500), outline=2, ocolor=C.INK)
        if self.t > 1.5 and int(self.t * 2) % 2 == 0:
            gfx.text(surf, self.t_("to_menu"), 30, C.WHITE, (cx, 600), outline=3, ocolor=C.INK)


# ===================================================================== Parent report
class ParentsScene(Scene):
    PAGES = ["page_overview", "page_sessions", "page_words"]

    def __init__(self, app):
        super().__init__(app)
        self.page = 0
        self.confirm = False

    def handle(self, e):
        if e.type != pygame.KEYDOWN:
            return
        if self.confirm:
            if e.key == pygame.K_y:
                self.app.store.reset_progress()
                self.app.audio.play("splat")
            self.confirm = False
            return
        if e.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE) + ENTER_KEYS:
            self.app.set_scene(MenuScene(self.app, 8))
        elif e.key == pygame.K_LEFT:
            self.page = (self.page - 1) % len(self.PAGES)
            self.app.audio.play("move")
        elif e.key == pygame.K_RIGHT:
            self.page = (self.page + 1) % len(self.PAGES)
            self.app.audio.play("move")
        elif e.key == pygame.K_r:
            self.confirm = True

    def draw(self, surf):
        header(surf, self.app, "parents_title", self.t)
        # tabs
        tw = 300
        sx = C.W // 2 - (tw * 3 + 20) // 2
        for i, key in enumerate(self.PAGES):
            r = pygame.Rect(sx + i * (tw + 10), 100, tw, 40)
            gfx.panel(surf, r, C.YELLOW if i == self.page else (70, 50, 100), C.INK, 12, 3)
            gfx.text(surf, self.t_(key), 22, C.INK if i == self.page else C.WHITE, r.center)
        body = pygame.Rect(70, 150, C.W - 140, 510)
        gfx.panel(surf, body, C.CREAM, C.INK, 18, 3)
        [self.draw_overview, self.draw_sessions, self.draw_words][self.page](surf, body)
        footer(surf, self.t_("parents_hint"))
        if self.confirm:
            gfx.dim(surf, 180)
            gfx.panel(surf, (C.W // 2 - 480, 300, 960, 110), (255, 220, 220), C.RED, 16, 4)
            msg = self.t_("parents_reset_confirm")
            gfx.text(surf, msg, gfx.fit_size(msg, 26, 920), C.INK, (C.W // 2, 355))

    def draw_overview(self, surf, body):
        p = self.app.store.progress
        total = p["letters_correct"] + p["letters_wrong"]
        acc = "%.0f%%" % (100.0 * p["letters_correct"] / total) if total else "-"
        mins = int(p["play_seconds"] // 60)
        rows = [
            ("p_games", str(p["games_played"])),
            ("p_time", self.t_("p_minutes", h=mins // 60, m=mins % 60)),
            ("p_words", str(p["words_completed"])),
            ("p_correct", str(p["letters_correct"])),
            ("p_wrong", str(p["letters_wrong"])),
            ("p_accuracy", acc),
            ("p_tissues", str(p["tissues_hit"])),
            ("p_best", str(p["best_score"])),
        ]
        for i, (key, val) in enumerate(rows):
            y = body.y + 40 + i * 54
            gfx.text(surf, self.t_(key), 26, (90, 70, 110), (body.x + 40, y), anchor="midleft")
            gfx.text(surf, val, 30, C.INK, (body.x + 520, y), anchor="midright")
        x0 = body.x + 600
        gfx.text(surf, self.t_("p_levels"), 26, (90, 70, 110), (x0, body.y + 40), anchor="midleft")
        for j, d in enumerate(C.DIFFICULTIES):
            y = body.y + 110 + j * 120
            gfx.text(surf, self.t_("diff_" + d), 26, C.INK, (x0, y), anchor="midleft")
            best = p["best_level"][d]
            for k in range(C.LEVELS):
                r = pygame.Rect(x0 + k * 46, y + 26, 40, 40)
                pygame.draw.rect(surf, C.GREEN if k < best else (220, 210, 200), r, border_radius=8)
                pygame.draw.rect(surf, C.INK, r, 2, border_radius=8)
                gfx.text(surf, str(k + 1), 18, C.INK, r.center)
            if p["completed"][d]:
                gfx.text(surf, self.t_("p_complete"), 22, (220, 80, 40), (x0 + 460, y), anchor="midright")

    def draw_sessions(self, surf, body):
        sessions = self.app.store.progress["sessions"]
        if not sessions:
            gfx.text(surf, self.t_("p_no_sessions"), 30, C.INK, body.center)
            return
        last = sessions[-10:]
        gfx.text(surf, self.t_("p_acc_chart"), 22, (90, 70, 110), (body.x + 40, body.y + 30), anchor="midleft")
        cx0, cy0, ch = body.x + 80, body.y + 240, 160
        pygame.draw.line(surf, C.INK, (cx0 - 10, cy0), (body.right - 60, cy0), 2)
        for pct in (50, 100):
            y = cy0 - ch * pct // 100
            pygame.draw.line(surf, (220, 210, 200), (cx0 - 10, y), (body.right - 60, y), 1)
            gfx.text(surf, "%d%%" % pct, 16, (120, 110, 130), (cx0 - 16, y), anchor="midright")
        bw = 70
        for i, s in enumerate(last):
            h = int(ch * s["accuracy"] / 100)
            x = cx0 + i * (bw + 26)
            col = C.BELT_COLORS[C.DIFFICULTIES.index(s["difficulty"])]
            pygame.draw.rect(surf, col, (x, cy0 - h, bw, h), border_radius=6)
            pygame.draw.rect(surf, C.INK, (x, cy0 - h, bw, h), 2, border_radius=6)
            gfx.text(surf, "%d" % s["level_reached"], 20, C.INK, (x + bw // 2, cy0 - h - 14))
        # legend
        for j, d in enumerate(C.DIFFICULTIES):
            lx = body.right - 420 + j * 140
            pygame.draw.rect(surf, C.BELT_COLORS[j], (lx, body.y + 20, 18, 18), border_radius=4)
            gfx.text(surf, self.t_("short_" + d), 18, C.INK, (lx + 24, body.y + 29), anchor="midleft")
        # table
        gfx.text(surf, self.t_("p_recent"), 22, (90, 70, 110), (body.x + 40, body.y + 268), anchor="midleft")
        cols = [(body.x + 40, "p_col_date", "midleft"), (body.x + 330, "p_col_mode", "midleft"),
                (body.x + 560, "p_col_level", "center"), (body.x + 740, "p_col_score", "midright"),
                (body.x + 900, "p_col_acc", "midright"), (body.x + 1060, "p_col_time", "midright")]
        for x, key, anchor in cols:
            gfx.text(surf, self.t_(key), 20, (120, 100, 140), (x, body.y + 300), anchor=anchor)
        for i, s in enumerate(reversed(sessions[-5:])):
            y = body.y + 335 + i * 34
            vals = [s["date"], self.t_("short_" + s["difficulty"]),
                    "%d%s" % (s["level_reached"], " ★" if s.get("completed") else ""),
                    str(s["score"]), "%.0f%%" % s["accuracy"],
                    "%d:%02d" % (int(s["seconds"]) // 60, int(s["seconds"]) % 60)]
            for (x, _k, anchor), v in zip(cols, vals):
                gfx.text(surf, v, 20, C.INK, (x, y), anchor=anchor)

    def draw_words(self, surf, body):
        p = self.app.store.progress
        words = sorted(p["words"].items(), key=lambda kv: (-kv[1], kv[0]))[:14]
        gfx.text(surf, self.t_("p_top_words"), 26, (90, 70, 110), (body.x + 40, body.y + 34), anchor="midleft")
        if not words:
            gfx.text(surf, self.t_("p_none"), 24, C.INK, (body.x + 40, body.y + 90), anchor="midleft")
        for i, (w, n) in enumerate(words):
            col, row = i % 2, i // 2
            x = body.x + 40 + col * 300
            y = body.y + 84 + row * 52
            gfx.text(surf, w, gfx.fit_size(w, 26, 220), C.INK, (x, y), anchor="midleft")
            gfx.text(surf, "x%d" % n, 22, (120, 100, 140), (x + 250, y), anchor="midright")
        x0 = body.x + 680
        gfx.text(surf, self.t_("p_trouble"), 26, (90, 70, 110), (x0, body.y + 34), anchor="midleft")
        gfx.text(surf, self.t_("p_trouble_note"), 16, (120, 100, 140), (x0, body.y + 64), anchor="midleft")
        trouble = sorted(p["trouble_letters"].items(), key=lambda kv: (-kv[1], kv[0]))[:6]
        if not trouble:
            gfx.text(surf, self.t_("p_none"), 24, C.INK, (x0, body.y + 110), anchor="midleft")
        mx = max([n for _c, n in trouble] or [1])
        for i, (ch, n) in enumerate(trouble):
            y = body.y + 110 + i * 62
            r = pygame.Rect(x0, y - 24, 48, 48)
            pygame.draw.rect(surf, C.BELT_COLORS[2], r, border_radius=10)
            pygame.draw.rect(surf, C.INK, r, 2, border_radius=10)
            gfx.text(surf, ch, 32, C.INK, r.center)
            bw = int(280 * n / mx)
            pygame.draw.rect(surf, (230, 120, 120), (x0 + 64, y - 10, bw, 20), border_radius=6)
            gfx.text(surf, str(n), 20, C.INK, (x0 + 74 + bw, y), anchor="midleft")
