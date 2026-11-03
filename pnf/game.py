"""The shooting-gallery gameplay scene."""
import math
import random
import string
import time

import pygame

from . import config as C
from . import gfx
from .base import Scene
from .belt import Belt
from .words import pick_words, word_length

# Flick animation timeline (seconds): curl the finger against the thumb, strain,
# snap it straight (the booger launches mid-snap), then wobble back to rest.
F_COCK, F_HOLD, F_SNAP, F_SETTLE = 0.07, 0.06, 0.05, 0.24
F_LAUNCH = F_COCK + F_HOLD + F_SNAP * 0.7
F_END = F_COCK + F_HOLD + F_SNAP + F_SETTLE
CURLED = (20.0, 90.0, 80.0)     # joint bends with the fingertip tucked under the thumb
OVERSHOOT = (-16.0, -12.0, -10.0)


def flick_pose(t):
    """-> (joint angles, thumb raise 0..1, hand y offset)"""
    if t >= F_END or t < 0:
        return (0.0, 0.0, 0.0), 0.0, 0.0
    if t < F_COCK:
        u = 1 - (1 - t / F_COCK) ** 2
        return tuple(c * u for c in CURLED), u, 3 * u
    t -= F_COCK
    if t < F_HOLD:
        j = math.sin(t * 110) * 2.0
        return (CURLED[0] + j, CURLED[1] - j, CURLED[2]), 1.0, 3.0
    t -= F_HOLD
    if t < F_SNAP:
        u = (t / F_SNAP) ** 2
        ang = tuple(c + (o - c) * u for c, o in zip(CURLED, OVERSHOOT))
        return ang, 1.0 - u, 3 - 8 * u
    t -= F_SNAP
    k = math.exp(-t * 15) * math.cos(t * 32)
    return tuple(o * k for o in OVERSHOOT), 0.0, -5 * k


class Booger:
    def __init__(self, x, y0, belt):
        self.x = x
        self.y0 = y0
        self.y1 = C.BELT_Y[belt]
        self.belt = belt
        self.t = 0.0
        self.dur = 0.16 + (y0 - self.y1) / 1700.0
        self.spin = random.uniform(-1, 1)

    @property
    def p(self):
        return min(1.0, self.t / self.dur)

    def pos(self):
        p = self.p
        e = 1 - (1 - p) ** 2
        y = self.y0 + (self.y1 - self.y0) * e
        x = self.x + math.sin(p * math.pi) * 10 * self.spin
        return x, y

    def radius(self):
        return 9 - 3 * self.p


class GameScene(Scene):
    music = None   # each level starts its own track

    def __init__(self, app, start_level=1):
        gfx.warm_finger()
        super().__init__(app)
        self.diff = app.store.settings["difficulty"]
        self.dp = C.DIFF[self.diff]
        self.start_level = start_level
        self.level = start_level
        self.score = 0
        self.lives = C.START_LIVES
        self.continue_used = False
        self.stats = {"correct": 0, "wrong": 0, "tissues": 0, "words": 0, "flicks": 0}
        self.play_seconds = 0.0
        self.recorded = False

        self.aim_x = float(C.GAL_CX)
        self.belt_sel = 1
        self.hand_x = self.aim_x
        self.hand_y = float(C.REST_TIP_Y)
        self.ammo = C.MAX_AMMO
        self.pick_t = 0.0
        self.pick_sfx_t = 0.0
        self.space_down = False
        self.need_press = False
        self.flick_t = 9.0
        self.launch_pending = False
        self.launch_belt = 0

        self.boogers = []
        self.splats = []           # [x, y, size, life]
        self.particles = gfx.Particles()
        self.popups = gfx.Popups()
        self.state = "intro"
        self.prev_state = None
        self.state_t = 0.0
        self.pause_sel = 0
        self.cont_t = 0.0
        self.bonus_left = 0
        self.bonus_total = 0
        self.last_tick = 99
        self.starve_t = 0.0
        self.belts = []
        self.setup_level()

    # ------------------------------------------------------------------ setup
    def setup_level(self):
        self.words = pick_words(self.diff, self.level, C.WORDS_PER_LEVEL)
        self.word_idx = 0
        self.timer = C.LEVEL_TIME
        self.last_tick = 99
        self.set_word(0, reroll=False)
        speed_mult = self.dp["speed"] * (1 + C.LEVEL_SPEEDUP * (self.level - 1))
        self.belts = []
        for i, b in enumerate(C.BELTS):
            self.belts.append(Belt(i, C.BELT_Y[i], b["speed"] * speed_mult, b["dir"], b["mode"],
                                   b["spacing"], self.assign_item))
        self.boogers.clear()
        self.ammo = C.MAX_AMMO
        self.pick_t = 0.0
        self.prepared_next = False
        self.app.music.play("level%d" % self.level)
        self.change_state("intro")

    def set_word(self, idx, reroll=True):
        self.word_idx = idx
        self.word, self.meaning = self.words[idx]
        self.spelled = 0
        self.starve_t = 0.0
        if reroll:
            for belt in self.belts:
                for it in belt.items:
                    if it.visible and it.state == "up" and it.kind != "empty":
                        self.particles.burst(it.x, belt.y, (255, 255, 255), n=8, speed=120, life=0.4, gravity=0)
                belt.reroll()

    @property
    def needed(self):
        return self.word[self.spelled] if self.spelled < len(self.word) else None

    def tissue_chance(self):
        return self.dp["tissue"] + self.dp["tissue_step"] * (self.level - 1)

    def assign_item(self, belt, item):
        """Choose what appears on a belt slot when it re-enters the gallery."""
        need = self.needed
        if need and self.starve_t > self.dp["starve"]:
            item.set("letter", need)
            self.starve_t = 0.0
            return
        r = random.random()
        tissue = self.tissue_chance() if self.state in ("play", "word_clear", "intro") else 0.0
        if r < C.EMPTY_CHANCE:
            item.set("empty")
        elif r < C.EMPTY_CHANCE + tissue:
            item.set("tissue")
        else:
            r2 = random.random()
            if need and r2 < self.dp["needed"]:
                ch = need
            elif r2 < self.dp["needed"] + 0.3:
                ch = random.choice(self.word)
            else:
                ch = random.choice(string.ascii_uppercase)
            item.set("letter", ch)

    def change_state(self, s):
        self.state = s
        self.state_t = 0.0

    # ------------------------------------------------------------------ input
    def handle(self, e):
        if e.type == pygame.KEYUP and e.key == pygame.K_SPACE:
            self.space_down = False
            return
        if e.type != pygame.KEYDOWN:
            return
        k = e.key
        if k == pygame.K_SPACE:
            self.space_down = True
        st = self.state
        if st in ("play", "intro", "word_clear"):
            if k in (pygame.K_ESCAPE, pygame.K_p):
                self.prev_state = st
                self.pause_sel = 0
                self.app.music.pause()
                self.space_down = False
                self.change_state("paused")
                self.app.audio.play("select")
            elif k == pygame.K_UP:
                if self.belt_sel > 0:
                    self.belt_sel -= 1
                    self.app.audio.play("move")
            elif k == pygame.K_DOWN:
                if self.belt_sel < 2:
                    self.belt_sel += 1
                    self.app.audio.play("move")
            elif k == pygame.K_SPACE:
                self.need_press = False
                if st == "play":
                    if self.ammo > 0 and self.pick_t == 0:
                        self.flick()
                    elif self.ammo == 0:
                        self.popups.add(self.t_("pick_hint"), C.NOSE_CX - 140, C.NOSE_CY + 140, C.YELLOW, 22, 0.8)
        elif st == "paused":
            if k in (pygame.K_UP, pygame.K_DOWN):
                self.pause_sel = 1 - self.pause_sel
                self.app.audio.play("move")
            elif k == pygame.K_ESCAPE:
                self.app.music.resume()
                self.change_state(self.prev_state)
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if self.pause_sel == 0:
                    self.app.music.resume()
                    self.change_state(self.prev_state)
                else:
                    self.record_session(False)
                    from .scenes import MenuScene
                    self.app.set_scene(MenuScene(self.app))
                self.space_down = False
                self.need_press = True
        elif st == "level_clear":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.state_t > 0.8:
                self.score += self.bonus_left
                self.bonus_left = 0
                if self.level >= C.LEVELS:
                    self.finish_victory()
                else:
                    self.level += 1
                    self.setup_level()
        elif st == "gameover":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER) and not self.continue_used:
                self.do_continue()
            elif k == pygame.K_ESCAPE or (self.continue_used and k in (pygame.K_RETURN, pygame.K_KP_ENTER)):
                self.change_state("final")
                self.record_session(False)
        elif st == "final":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.state_t > 0.6:
                self.go_after_game()

    def flick(self):
        if self.launch_pending:      # quick double tap: fire the previous one right now
            self.launch()
        self.ammo -= 1
        self.flick_t = 0.0
        self.launch_pending = True
        self.launch_belt = self.belt_sel
        self.stats["flicks"] += 1
        if self.ammo == 0:
            self.need_press = True

    def launch(self):
        self.launch_pending = False
        self.boogers.append(Booger(self.hand_x, self.hand_y - 4, self.launch_belt))
        self.particles.burst(self.hand_x, self.hand_y - 8, C.BOOGER, n=5, speed=90)
        self.app.audio.play("flick")

    # ------------------------------------------------------------------ update
    def update(self, dt):
        super().update(dt)
        self.state_t += dt
        self.particles.update(dt)
        self.popups.update(dt)
        for s in self.splats:
            s[3] -= dt
        self.splats = [s for s in self.splats if s[3] > 0]
        if self.state == "paused":
            return
        if self.state in ("intro", "play", "word_clear", "level_clear"):
            self.play_seconds += dt
        for b in self.belts:
            b.update(dt)
        self.update_hand(dt)
        self.update_boogers(dt)

        if self.state == "intro":
            if self.state_t > 2.2:
                self.change_state("play")
        elif self.state == "play":
            self.update_play(dt)
        elif self.state == "word_clear":
            if self.state_t > 1.4:
                if self.word_idx + 1 < len(self.words):
                    self.set_word(self.word_idx + 1)
                    self.change_state("play")
                else:
                    self.begin_level_clear()
        elif self.state == "level_clear":
            if not self.prepared_next and self.state_t > 0.4 and self.level < C.LEVELS:
                self.prepared_next = True
                self.app.music.prefetch(["level%d" % (self.level + 1)])
            if self.bonus_left > 0 and self.state_t > 0.6:
                step = max(1, int(self.bonus_total * dt * 1.5))
                step = min(step, self.bonus_left)
                self.bonus_left -= step
                self.score += step
        elif self.state == "gameover":
            if not self.continue_used:
                self.cont_t -= dt
                if self.cont_t <= 0:
                    self.change_state("final")
                    self.record_session(False)

    def update_play(self, dt):
        # keep the next letter showing up regularly
        need = self.needed
        seen = any(it.hittable and it.kind == "letter" and it.char == need
                   for b in self.belts for it in b.items)
        self.starve_t = 0.0 if seen else self.starve_t + dt

        self.timer -= dt
        sec = int(math.ceil(self.timer))
        if sec <= 10 and sec != self.last_tick and sec > 0:
            self.last_tick = sec
            self.app.audio.play("tick")
        if self.timer <= 0:
            self.timer = C.LEVEL_TIME
            self.last_tick = 99
            self.lose_life(self.t_("time_up"))

    def update_hand(self, dt):
        keys = pygame.key.get_pressed()
        if self.state in ("play", "intro", "word_clear"):
            move = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * C.AIM_SPEED * dt
            self.aim_x = max(C.AIM_MIN, min(C.AIM_MAX, self.aim_x + move))

        picking = (self.state == "play" and self.ammo == 0 and self.space_down and not self.need_press)
        if picking:
            self.pick_t += dt
            self.pick_sfx_t -= dt
            if self.pick_sfx_t <= 0:
                self.pick_sfx_t = 0.45
                self.app.audio.play("pick")
            if self.pick_t >= C.PICK_TIME:
                self.ammo = C.MAX_AMMO
                self.pick_t = 0.0
                self.need_press = True
                nx, ny = gfx.nostril_pos()
                self.particles.burst(nx, ny, C.BOOGER, n=14, speed=160)
                self.popups.add(self.t_("reloaded"), C.NOSE_CX, C.NOSE_CY - 100, C.GREEN, 26)
                self.app.audio.play("reload")
        else:
            self.pick_t = 0.0
            self.pick_sfx_t = 0.0

        if self.pick_t > 0:
            nx, ny = gfx.nostril_pos()
            tx, ty = nx + 14, ny - 6
            close = math.hypot(self.hand_x - tx, self.hand_y - ty) < 30
            if close:
                tx += math.sin(self.t * 30) * 4
                ty += math.sin(self.t * 21) * 7
        else:
            tx, ty = self.aim_x, C.REST_TIP_Y
        k = min(1.0, dt * 16)
        self.hand_x += (tx - self.hand_x) * k
        self.hand_y += (ty - self.hand_y) * k
        self.flick_t += dt
        if self.launch_pending and (self.flick_t >= F_LAUNCH or self.state != "play"):
            self.launch()

    def update_boogers(self, dt):
        alive = []
        for b in self.boogers:
            b.t += dt
            if b.p >= 1.0:
                self.resolve(b)
            else:
                alive.append(b)
        self.boogers = alive

    def resolve(self, b):
        belt = self.belts[b.belt]
        x, y = b.pos()
        target = belt.hit_test(x, C.TILE / 2 + 8)
        if target is None or self.state != "play":
            self.splats.append([x, y + random.uniform(-18, 18), random.randint(8, 13), 2.5])
            self.particles.burst(x, y, C.BOOGER, n=8, speed=140, life=0.5)
            self.app.audio.play("splat")
            return
        target.knock()
        self.particles.burst(target.x, belt.y, C.BOOGER, n=14, speed=200)
        if target.kind == "tissue":
            self.stats["tissues"] += 1
            self.particles.burst(target.x, belt.y, (255, 255, 255), n=20, speed=260)
            self.lose_life(self.t_("tissue_hit"))
        elif target.char == self.needed:
            self.spelled += 1
            self.stats["correct"] += 1
            pts = int(C.BELTS[b.belt]["points"] * self.level * self.dp["mult"])
            self.score += pts
            self.popups.add("+%d" % pts, target.x, belt.y - 40, C.YELLOW, 30)
            self.app.audio.play("correct")
            if self.spelled >= len(self.word):
                self.complete_word()
        else:
            self.stats["wrong"] += 1
            tl = self.app.store.progress["trouble_letters"]
            tl[self.needed] = tl.get(self.needed, 0) + 1
            pen = int(self.dp["penalty"] * self.level)
            self.score = max(0, self.score - pen)
            msg = self.t_("oops") + (" -%d" % pen if pen else "")
            self.popups.add(msg, target.x, belt.y - 40, (255, 140, 140), 26)
            self.app.audio.play("wrong")

    def complete_word(self):
        self.stats["words"] += 1
        bonus = int(50 * self.level * self.dp["mult"])
        self.score += bonus
        words = self.app.store.progress["words"]
        words[self.word] = words.get(self.word, 0) + 1
        self.popups.add(self.t_("word_done") + "  +%d" % bonus, C.GAL_CX, C.BOARD_TOP - 20, C.GREEN, 36, 1.4)
        self.app.audio.play("word")
        self.boogers.clear()
        self.change_state("word_clear")

    def begin_level_clear(self):
        self.bonus_total = int(math.ceil(self.timer) * 2 * self.level * self.dp["mult"])
        self.bonus_left = self.bonus_total
        p = self.app.store.progress
        p["best_level"][self.diff] = max(p["best_level"][self.diff], self.level)
        self.app.store.save()
        self.app.audio.play("level")
        self.change_state("level_clear")

    def lose_life(self, msg):
        self.lives -= 1
        self.app.shake(0.45)
        self.app.audio.play("tissue")
        self.popups.add(msg, C.GAL_CX, C.GAL_TOP + 150, (255, 120, 120), 40, 1.6)
        if self.lives <= 0:
            self.lives = 0
            self.boogers.clear()
            self.space_down = False
            self.cont_t = 10.0
            self.app.music.stop(300)
            self.app.audio.play("over")
            self.change_state("gameover")

    def do_continue(self):
        self.continue_used = True
        self.lives = C.START_LIVES
        self.timer = C.LEVEL_TIME
        self.ammo = C.MAX_AMMO
        self.need_press = True
        self.app.audio.play("select")
        self.app.music.play("level%d" % self.level)
        self.change_state("play")

    # ------------------------------------------------------------------ results
    def record_session(self, completed):
        if self.recorded:
            return
        self.recorded = True
        st = self.stats
        p = self.app.store.progress
        p["words_completed"] += st["words"]
        p["letters_correct"] += st["correct"]
        p["letters_wrong"] += st["wrong"]
        p["tissues_hit"] += st["tissues"]
        p["flicks"] += st["flicks"]
        total = st["correct"] + st["wrong"]
        self.app.store.record_session({
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "difficulty": self.diff,
            "start_level": self.start_level,
            "level_reached": self.level,
            "score": self.score,
            "correct": st["correct"],
            "wrong": st["wrong"],
            "accuracy": round(100.0 * st["correct"] / total, 1) if total else 0.0,
            "words": st["words"],
            "seconds": round(self.play_seconds, 1),
            "completed": completed,
        })

    def finish_victory(self):
        store = self.app.store
        store.progress["completed"][self.diff] = True
        store.data["level_select_unlocked"] = True
        self.record_session(True)
        from .scenes import VictoryScene
        self.app.set_scene(VictoryScene(self.app, self.score, self.level, self.diff))

    def go_after_game(self):
        from .scenes import MenuScene, NameEntryScene
        if self.app.store.qualifies(self.score):
            self.app.set_scene(NameEntryScene(self.app, self.score, self.level, self.diff))
        else:
            self.app.set_scene(MenuScene(self.app))

    # ------------------------------------------------------------------ drawing
    def draw(self, surf):
        gfx.draw_background(surf, self.t)
        self.draw_gallery(surf)
        self.draw_board(surf)
        self.draw_panel(surf)
        show_booger = self.ammo > 0 and self.state in ("play", "intro", "word_clear")
        angles, thumb, dy = flick_pose(self.flick_t)
        if self.flick_t < F_LAUNCH:
            show_booger = True           # the booger rides the fingertip until release
        elif self.flick_t < F_END:
            show_booger = False
        if self.pick_t > 0:
            show_booger = False
        gfx.draw_hand(surf, self.hand_x, self.hand_y + dy, angles, thumb, booger=show_booger)
        snap0 = F_COCK + F_HOLD
        if snap0 < self.flick_t < F_END - 0.1:   # swoosh along the fingertip's path
            bx, by = self.hand_x, self.hand_y + dy + gfx.KNUCKLE_DY
            now = min(self.flick_t, snap0 + F_SNAP)
            pts = []
            for k in range(9):
                tt = snap0 + (now - snap0) * k / 8
                pts.append(gfx.finger_joints(bx, by, flick_pose(tt)[0])[-1])
            fade = 1.0 if self.flick_t < snap0 + F_SNAP else max(0.0, 1 - (self.flick_t - snap0 - F_SNAP) / 0.14)
            gfx.draw_flick_trail(surf, pts, fade)
        self.draw_nose_layer(surf)
        self.draw_hud(surf)
        self.particles.draw(surf)
        self.popups.draw(surf)
        self.draw_overlay(surf)

    def draw_gallery(self, surf):
        x0, x1, top, bot = C.GAL_X0, C.GAL_X1, C.GAL_TOP, C.GAL_BOTTOM
        gfx.draw_gallery_back(surf)
        for s in self.splats:
            gfx.draw_splat(surf, int(s[0]), int(s[1]), s[2], int(200 * min(1.0, s[3])))
        guide = self.dp["guide"] and self.state == "play" and self.pick_t == 0
        surf.set_clip(pygame.Rect(x0, top, x1 - x0, bot - top))
        for i, belt in enumerate(self.belts):
            y = belt.y
            if i == self.belt_sel:
                gfx.draw_belt_glow(surf, y, self.t)
            gfx.draw_track(surf, x0, x1, y, belt.chain, C.BELT_COLORS[i])
            for it in belt.items:
                if not it.visible or it.state == "down" or it.kind == "empty":
                    continue
                squash = 1.0 if it.state == "up" else max(0.05, 1 - it.fall_t / Belt.FALL_TIME)
                x = int(it.x)
                if it.kind == "tissue":
                    gfx.draw_tissue(surf, x, y, squash)
                else:
                    gfx.draw_tile(surf, x, y, it.char, C.BELT_COLORS[i], squash)
        if guide:
            gfx.draw_aim(surf, int(self.hand_x), int(self.hand_y) - 14, C.BELT_Y[self.belt_sel], self.t)
        for b in self.boogers:
            bx, by = b.pos()
            gfx.draw_booger(surf, bx, by, int(b.radius()))
        surf.set_clip(None)
        gfx.draw_gallery_front(surf, self.t)
        gfx.draw_arrow(surf, x0 - 26, C.BELT_Y[self.belt_sel], "right", 12)

    def draw_board(self, surf):
        r = pygame.Rect(C.GAL_X0 - 8, C.BOARD_TOP + 6, C.GAL_X1 - C.GAL_X0 + 16, C.BOARD_BOTTOM - C.BOARD_TOP - 6)
        gfx.draw_board_bg(surf, r)
        gfx.text(surf, self.t_("spell"), 24, C.CREAM, (r.x + 18, r.y + 34), anchor="midleft", outline=2, ocolor=C.INK)
        n = len(self.word)
        box = min(62, int(820 / n) - 6)
        gap = 6
        total = n * box + (n - 1) * gap
        sx = C.GAL_CX + 50 - total // 2
        y = r.y + 8
        for i, ch in enumerate(self.word):
            br = pygame.Rect(sx + i * (box + gap), y, box, 54)
            if i < self.spelled:
                col, tcol = (110, 196, 56), C.WHITE
            elif i == self.spelled and self.state == "play":
                col, tcol = (255, 210, 30), C.INK
            else:
                col, tcol = (250, 240, 216), (130, 118, 140)
            gfx.pill(surf, br, col, C.INK, 9, 3)
            gfx.text(surf, ch, min(38, box - 14), tcol, (br.centerx, br.centery + 1),
                     outline=2 if i < self.spelled else 0, ocolor=(40, 90, 20))
            if i == self.spelled and self.state == "play" and int(self.t * 3) % 2 == 0:
                pygame.draw.rect(surf, C.INK, (br.x + 8, br.bottom - 9, br.w - 16, 4), border_radius=2)
        meaning = self.t_("meaning", m=self.meaning)
        if meaning:
            gfx.text(surf, meaning, 20, C.CREAM, (C.GAL_CX + 50, r.bottom - 13), outline=2, ocolor=C.INK)

    def draw_panel(self, surf):
        px, py, pw, ph = C.PANEL
        gfx.panel(surf, (px, py, pw, ph), (60, 36, 96), C.INK, 14, 3)
        gfx.text(surf, self.t_("nose"), gfx.fit_size(self.t_("nose"), 22, pw - 10), C.YELLOW,
                 (px + pw // 2, py + 22), outline=2, ocolor=C.INK)

    def draw_nose_layer(self, surf):
        px, py, pw, ph = C.PANEL
        wig = math.sin(self.t * 40) * 2 if self.pick_t > 0 else 0
        gfx.draw_nose(surf, C.NOSE_CX, C.NOSE_CY, self.t, wig)
        if self.pick_t > 0:
            p = self.pick_t / C.PICK_TIME
            rect = pygame.Rect(0, 0, 124, 124)
            rect.center = (C.NOSE_CX, C.NOSE_CY + 8)
            pygame.draw.arc(surf, (60, 60, 80), rect, 0, math.tau, 8)
            pygame.draw.arc(surf, C.GREEN, rect, math.pi / 2, math.pi / 2 + math.tau * p, 8)
            n = int(math.ceil(C.PICK_TIME - self.pick_t))
            gfx.text(surf, str(n), 44, C.WHITE, (C.NOSE_CX + 50, C.NOSE_CY - 66), outline=3, ocolor=C.INK)
            gfx.text(surf, self.t_("picking"), gfx.fit_size(self.t_("picking"), 20, pw - 8), C.GREEN,
                     (C.NOSE_CX, C.NOSE_CY + 112), outline=2, ocolor=C.INK)
        # ammo
        y = py + ph - 46
        gfx.text(surf, self.t_("boogers"), 18, C.CREAM, (px + pw // 2, y - 30), outline=2, ocolor=C.INK)
        for i in range(C.MAX_AMMO):
            x = px + 34 + i * 36
            if i < self.ammo:
                gfx.draw_booger(surf, x, y, 11)
            else:
                pygame.draw.circle(surf, (110, 90, 130), (x, y), 11, 2)
        if self.ammo == 0 and self.pick_t == 0 and self.state == "play" and int(self.t * 2.5) % 2 == 0:
            hint = self.t_("pick_hint")
            gfx.text(surf, hint, gfx.fit_size(hint, 18, 250), C.YELLOW, (C.NOSE_CX - 30, py + ph + 18),
                     outline=2, ocolor=C.INK)
            gfx.draw_arrow(surf, C.NOSE_CX, C.NOSE_CY + 100, "up", 10)

    def draw_hud(self, surf):
        cx = C.W // 2
        gfx.text(surf, "%s  %06d" % (self.t_("score"), self.score), 30, C.YELLOW, (cx, 22), outline=3, ocolor=C.INK)
        sec = max(0, int(math.ceil(self.timer)))
        tcol = C.WHITE
        if sec <= 20 and self.state == "play":
            tcol = C.RED if int(self.t * 4) % 2 == 0 else C.WHITE
        tstr = "%d:%02d" % (sec // 60, sec % 60)
        gfx.panel(surf, (cx - 92, 46, 290, 42), (40, 22, 70), C.INK, 21, 2)
        gfx.draw_clock(surf, cx - 62, 66, 13, tcol)
        gfx.text(surf, tstr, 34, tcol, (cx - 40, 66), anchor="midleft", outline=3, ocolor=C.INK)
        # lives (fingers) to the right of the timer
        for i in range(C.START_LIVES):
            gfx.draw_life_finger(surf, cx + 90 + i * 30, 66, i < self.lives)
        # level & word info
        lv = "%s %d/%d" % (self.t_("level"), self.level, C.LEVELS)
        gfx.text(surf, lv, 26, C.WHITE, (C.GAL_X0, 26), anchor="midleft", outline=3, ocolor=C.INK)
        gfx.text(surf, self.t_("short_" + self.diff), 20, C.BELT_COLORS[1], (C.GAL_X0, 62), anchor="midleft",
                 outline=2, ocolor=C.INK)
        wd = "%s %d/%d" % (self.t_("word"), min(self.word_idx + 1, C.WORDS_PER_LEVEL), C.WORDS_PER_LEVEL)
        gfx.text(surf, wd, 26, C.WHITE, (C.W - 20, 26), anchor="midright", outline=3, ocolor=C.INK)
        snd = self.t_("on") if self.app.audio.enabled else self.t_("off")
        bgm = self.t_("on") if self.app.music.enabled else self.t_("off")
        hint = "M: %s %s   B: %s %s" % (self.t_("menu_sound"), snd, self.t_("bgm_short"), bgm)
        gfx.text(surf, hint, 16, (190, 180, 210), (C.W - 20, 62), anchor="midright")

    def draw_overlay(self, surf):
        st = self.state
        cx = C.W // 2
        if st == "intro":
            a = 255 if self.state_t < 1.8 else int(255 * max(0.0, (2.2 - self.state_t) / 0.4))
            gfx.text(surf, self.t_("level_intro", n=self.level), 80, C.YELLOW, (C.GAL_CX, 230), outline=5,
                     ocolor=C.INK, alpha=a)
            gfx.text(surf, self.t_("level_intro_sub", n=word_length(self.level)), 36, C.WHITE, (C.GAL_CX, 305),
                     outline=3, ocolor=C.INK, alpha=a)
            gfx.text(surf, self.t_("get_ready"), 28, C.GREEN, (C.GAL_CX, 360), outline=3, ocolor=C.INK, alpha=a)
        elif st == "paused":
            gfx.dim(surf)
            gfx.panel(surf, (cx - 220, 200, 440, 300))
            gfx.text(surf, self.t_("paused"), 56, C.INK, (cx, 260))
            for i, key in enumerate(("resume", "quit_menu")):
                sel = i == self.pause_sel
                y = 350 + i * 70
                if sel:
                    pygame.draw.rect(surf, C.YELLOW, (cx - 180, y - 26, 360, 52), border_radius=14)
                gfx.text(surf, self.t_(key), 32, C.INK, (cx, y))
        elif st == "level_clear":
            gfx.dim(surf, 120)
            gfx.panel(surf, (cx - 330, 170, 660, 340))
            gfx.text(surf, self.t_("level_clear", n=self.level), 58, (230, 80, 60), (cx, 235), outline=3,
                     ocolor=C.INK)
            gfx.text(surf, self.t_("time_bonus", b=self.bonus_total), 32, C.INK, (cx, 310))
            gfx.text(surf, "%s  %06d" % (self.t_("score"), self.score), 40, C.INK, (cx, 370))
            if self.state_t > 0.8 and int(self.t * 2) % 2 == 0:
                key = "next_level" if self.level < C.LEVELS else "press_enter"
                gfx.text(surf, self.t_(key), 26, (90, 60, 140), (cx, 450))
        elif st == "gameover":
            gfx.dim(surf, 170)
            gfx.text(surf, self.t_("game_over"), 84, C.RED, (cx, 220), outline=5, ocolor=C.INK)
            if not self.continue_used:
                gfx.text(surf, self.t_("continue_q", n=max(0, int(math.ceil(self.cont_t)))), 48, C.YELLOW,
                         (cx, 330), outline=3, ocolor=C.INK)
                gfx.text(surf, self.t_("continue_hint"), 30, C.WHITE, (cx, 400), outline=2, ocolor=C.INK)
                gfx.text(surf, self.t_("continue_used"), 22, (200, 190, 220), (cx, 450))
            else:
                gfx.text(surf, self.t_("press_enter"), 30, C.WHITE, (cx, 360), outline=2, ocolor=C.INK)
        elif st == "final":
            gfx.dim(surf, 190)
            gfx.text(surf, self.t_("game_over"), 84, C.RED, (cx, 230), outline=5, ocolor=C.INK)
            gfx.text(surf, self.t_("final_score", s=self.score), 44, C.YELLOW, (cx, 340), outline=3, ocolor=C.INK)
            if self.state_t > 0.6 and int(self.t * 2) % 2 == 0:
                gfx.text(surf, self.t_("press_enter"), 30, C.WHITE, (cx, 430), outline=2, ocolor=C.INK)
