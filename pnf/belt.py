"""Conveyor belts for the shooting gallery.

loop     : items travel in one direction and wrap around off-screen.
pingpong : the whole belt slides left-to-right; once it has travelled half the
           gallery width it reverses, then repeats.
Items that leave the visible window get fresh content from the `assign` callback.
"""
import math

from . import config as C


class Item:
    __slots__ = ("u", "x", "kind", "char", "state", "fall_t", "visible")

    def __init__(self, u):
        self.u = u
        self.x = 0.0
        self.kind = "empty"     # "empty" | "letter" | "tissue"
        self.char = ""
        self.state = "up"       # "up" | "falling" | "down"
        self.fall_t = 0.0
        self.visible = False

    def set(self, kind, char=""):
        self.kind = kind
        self.char = char
        self.state = "up"
        self.fall_t = 0.0

    def knock(self):
        self.state = "falling"
        self.fall_t = 0.0

    @property
    def hittable(self):
        return self.state == "up" and self.kind != "empty" and self.visible


class Belt:
    FALL_TIME = 0.3

    def __init__(self, index, y, speed, direction, mode, spacing, assign,
                 x0=C.GAL_X0, x1=C.GAL_X1):
        self.index = index
        self.y = y
        self.speed = speed
        self.dir = direction
        self.mode = mode
        self.spacing = spacing
        self.assign = assign
        self.x0, self.x1 = x0, x1
        self.margin = C.TILE
        self.offset = 0.0
        self.pp_dir = 1
        self.chain = 0.0
        width = x1 - x0
        if mode == "loop":
            n = int(math.ceil((width + 2 * self.margin) / spacing)) + 1
            self.length = n * spacing
            self.start = x0 - self.margin
        else:
            self.amp = width / 2
            n = int(math.ceil((width + 2 * self.margin + self.amp) / spacing)) + 1
            self.start = x0 - self.margin - self.amp
        self.items = [Item(i * spacing) for i in range(n)]
        for it in self.items:
            it.x = self._x(it)
            it.visible = self._visible(it.x)
            self.assign(self, it)

    def _x(self, it):
        if self.mode == "loop":
            return self.start + ((it.u + self.offset) % self.length)
        return self.start + it.u + self.offset

    def _visible(self, x):
        return self.x0 - C.TILE / 2 < x < self.x1 + C.TILE / 2

    @property
    def velocity(self):
        if self.mode == "loop":
            return self.dir * self.speed
        return self.pp_dir * self.speed

    def update(self, dt):
        if self.mode == "loop":
            self.offset = (self.offset + self.dir * self.speed * dt) % self.length
        else:
            self.offset += self.pp_dir * self.speed * dt
            if self.offset >= self.amp:
                self.offset = self.amp
                self.pp_dir = -1
            elif self.offset <= 0:
                self.offset = 0.0
                self.pp_dir = 1
        self.chain += self.velocity * dt
        for it in self.items:
            it.x = self._x(it)
            vis = self._visible(it.x)
            if it.visible and not vis:
                self.assign(self, it)
            it.visible = vis
            if it.state == "falling":
                it.fall_t += dt
                if it.fall_t >= self.FALL_TIME:
                    it.state = "down"

    def hit_test(self, x, tol):
        best, best_d = None, tol
        for it in self.items:
            if it.hittable:
                d = abs(it.x - x)
                if d <= best_d:
                    best, best_d = it, d
        return best

    def reroll(self):
        for it in self.items:
            self.assign(self, it)
