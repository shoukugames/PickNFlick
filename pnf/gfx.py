"""Procedural art.

Everything is drawn in code. Sprites are rendered once at 3x resolution with
gradients, gloss and outlines, then smooth-scaled down (super-sampling gives
clean anti-aliased edges) and cached. Soft drop shadows come from a blurred
silhouette, and lights and fireworks use additive glow sprites.
"""
import math
import random

import pygame

from . import config as C
from .resources import resource_path

SS = 3
SRCALPHA = pygame.SRCALPHA
FONT_FILE = resource_path("assets", "fonts", "MPLUSRounded1c-Bold.ttf")
_fonts = {}
_text_cache = {}
_sprites = {}


def cached(key, make):
    s = _sprites.get(key)
    if s is None:
        s = make()
        _sprites[key] = s
    return s


# =========================================================================== colour
def lerp_c(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(min(len(a), len(b))))


def lighten(c, a):
    return tuple(int(v + (255 - v) * a) for v in c[:3])


def darken(c, a):
    return tuple(int(v * (1 - a)) for v in c[:3])


def rgba(c, a=255):
    return (c[0], c[1], c[2], a)


# ========================================================================= surfaces
def surface(w, h, fill=(255, 255, 255, 0)):
    s = pygame.Surface((max(1, int(w)), max(1, int(h))), SRCALPHA)
    s.fill(fill)
    return s


def grad(w, h, stops, horizontal=False):
    """Linear gradient through evenly spaced colour stops."""
    s = surface(w, h)
    n = int(w if horizontal else h)
    segs = len(stops) - 1
    for i in range(n):
        t = i / max(1, n - 1)
        k = min(segs - 1, int(t * segs)) if segs > 0 else 0
        c = stops[0] if segs == 0 else lerp_c(stops[k], stops[k + 1], t * segs - k)
        c = rgba(c, c[3] if len(c) > 3 else 255)
        if horizontal:
            pygame.draw.line(s, c, (i, 0), (i, h - 1))
        else:
            pygame.draw.line(s, c, (0, i), (w - 1, i))
    return s


def shaped(w, h, stops, shape, horizontal=False):
    """Gradient clipped to a shape drawn by shape(mask, white)."""
    g = grad(w, h, stops, horizontal)
    m = surface(w, h)
    shape(m, (255, 255, 255, 255))
    g.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return g


def radial(w, h, center, radius, c_in, c_out, steps=48):
    s = surface(w, h, rgba(c_out))
    for i in range(steps, 0, -1):
        t = i / steps
        pygame.draw.circle(s, rgba(lerp_c(c_in, c_out, t)), center, max(1, int(radius * t)))
    return s


def clip_to(src, shape_mask):
    out = src.copy()
    out.blit(shape_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


def down(s, w, h):
    return pygame.transform.smoothscale(s, (max(1, int(w)), max(1, int(h))))


def silhouette(sprite, color=(0, 0, 0)):
    s = sprite.copy()
    s.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGB_MULT)
    if color != (0, 0, 0):
        s.fill(rgba(color, 0), special_flags=pygame.BLEND_RGB_ADD)
    return s


def soft_shadow(sprite, blur=6, alpha=110, color=(0, 0, 0)):
    w, h = sprite.get_size()
    pad = blur * 2
    s = surface(w + pad * 2, h + pad * 2, rgba(color, 0))
    s.blit(silhouette(sprite, color), (pad, pad))
    s.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    f = max(2, blur)
    small = down(s, s.get_width() // f, s.get_height() // f)
    return pygame.transform.smoothscale(small, s.get_size()), pad


def outline(sprite, color, width):
    """Return sprite with a solid outline of `width` px around its silhouette."""
    w, h = sprite.get_size()
    out = surface(w + 2 * width, h + 2 * width, rgba(color, 0))
    sil = silhouette(sprite, color)
    n = 16
    for i in range(n):
        a = math.tau * i / n
        out.blit(sil, (width + round(math.cos(a) * width), width + round(math.sin(a) * width)))
    out.blit(sprite, (width, width))
    return out


def glow(color, radius, strength=1.0):
    """Alpha glow (normal blending)."""
    def make():
        n = 64
        s = surface(n, n, rgba(color, 0))
        for i in range(32, 0, -1):
            t = i / 32
            pygame.draw.circle(s, rgba(color, int(255 * strength * (1 - t) ** 2)), (32, 32), max(1, int(32 * t)))
        return down(s, radius * 2, radius * 2)
    return cached(("glow", color, radius, strength), make)


def glow_add(color, radius, strength=1.0):
    """Premultiplied glow for BLEND_ADD."""
    def make():
        n = 64
        s = pygame.Surface((n, n))
        s.fill((0, 0, 0))
        for i in range(32, 0, -1):
            t = i / 32
            k = strength * (1 - t) ** 2
            pygame.draw.circle(s, tuple(int(v * k) for v in color[:3]), (32, 32), max(1, int(32 * t)))
        return pygame.transform.smoothscale(s, (radius * 2, radius * 2))
    return cached(("glowadd", color, radius, strength), make)


def dot(color, r):
    """Small anti-aliased disc."""
    def make():
        d = r * 2 + 2
        s = surface(d * SS, d * SS, rgba(color, 0))
        pygame.draw.circle(s, rgba(color), (d * SS // 2, d * SS // 2), r * SS)
        return down(s, d, d)
    return cached(("dot", color, r), make)


# ============================================================================= text
def font(size):
    f = _fonts.get(size)
    if f is None:
        try:
            f = pygame.font.Font(FONT_FILE, size)
        except (OSError, FileNotFoundError):
            f = pygame.font.Font(None, size)
        _fonts[size] = f
    return f


def render(s, size, color, outline_w=0, ocolor=(0, 0, 0)):
    key = (s, size, color, outline_w, ocolor)
    surf = _text_cache.get(key)
    if surf is not None:
        return surf
    if len(_text_cache) > 800:
        _text_cache.clear()
    f = font(size)
    base = f.render(s, True, color)
    if outline_w:
        o = f.render(s, True, ocolor)
        w, h = base.get_width() + outline_w * 2, base.get_height() + outline_w * 2
        surf = surface(w, h, rgba(ocolor, 0))
        steps = max(12, outline_w * 6)
        for i in range(steps):
            a = math.tau * i / steps
            for rr in (outline_w, outline_w * 0.6):
                surf.blit(o, (outline_w + round(math.cos(a) * rr), outline_w + round(math.sin(a) * rr)))
        surf.blit(base, (outline_w, outline_w))
        if outline_w >= 3:
            sh, pad = soft_shadow(surf, blur=max(3, size // 12), alpha=150)
            out = surface(sh.get_width(), sh.get_height() + outline_w)
            out.blit(sh, (0, outline_w))
            out.blit(surf, (pad, pad))
            surf = out
    else:
        surf = base
    _text_cache[key] = surf
    return surf


def text(surf, s, size, color, pos, anchor="center", outline=0, ocolor=(0, 0, 0), alpha=255):
    img = render(s, size, color, outline, ocolor)
    rect = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    surf.blit(img, rect)
    return rect


def text_width(s, size):
    return font(size).size(s)[0]


def fit_size(s, size, max_w, min_size=12):
    while size > min_size and text_width(s, size) > max_w:
        size -= 2
    return size


# ====================================================================== backgrounds
def vgradient(w, h, top, bottom):
    def make():
        g = pygame.Surface((w, h))
        for y in range(h):
            pygame.draw.line(g, lerp_c(top, bottom, y / max(1, h - 1)), (0, y), (w, y))
        return g
    return cached(("vgrad", w, h, top, bottom), make)


def vignette(w, h, strength=200, power=2.2):
    def make():
        lw, lh = 64, 36
        s = surface(lw, lh, (0, 0, 0, 0))
        for y in range(lh):
            for x in range(lw):
                dx = (x + 0.5) / lw * 2 - 1
                dy = (y + 0.5) / lh * 2 - 1
                d = min(1.0, math.sqrt(dx * dx * 0.8 + dy * dy) / 1.25)
                s.set_at((x, y), (0, 0, 0, int(strength * d ** power)))
        return pygame.transform.smoothscale(s, (w, h))
    return cached(("vignette", w, h, strength, power), make)


def _background():
    bg = vgradient(C.W, C.H, C.BG_TOP, C.BG_BOTTOM).copy()
    # circus-tent stripes fanning out from the top
    stripes = surface(C.W, C.H)
    for i in range(-6, 22):
        x0 = C.W / 2 + i * 70 - 10 * 70 + 380
        top_x = C.W / 2 + (x0 - C.W / 2) * 0.35
        pts = [(top_x, -10), (top_x + 24, -10), (x0 + 70, C.H), (x0, C.H)]
        if i % 2 == 0:
            pygame.draw.polygon(stripes, (255, 255, 255, 12), pts)
    bg.blit(stripes, (0, 0))
    for x, y, r, col, s in [(200, 80, 360, (140, 60, 200), 0.35), (1080, 120, 380, (60, 90, 220), 0.30),
                            (640, 760, 520, (200, 60, 120), 0.25)]:
        bg.blit(glow(col, r, s), (x - r, y - r))
    bg.blit(vignette(C.W, C.H, 210), (0, 0))
    return bg


BOKEH = [(random.Random(i).uniform(0, C.W), random.Random(i * 7).uniform(0, C.H),
          random.Random(i * 13).randint(14, 40), random.Random(i * 17).uniform(4, 14)) for i in range(16)]
BOKEH_COLORS = [(255, 200, 90), (255, 120, 170), (120, 200, 255), (190, 140, 255)]


def draw_background(surf, t=0.0):
    surf.blit(cached("background", _background), (0, 0))
    for i, (x, y, r, sp) in enumerate(BOKEH):
        xx = (x + t * sp) % (C.W + 2 * r) - r
        yy = y + math.sin(t * 0.5 + i) * 10
        g = glow(BOKEH_COLORS[i % 4], r, 0.25)
        surf.blit(g, (xx - r, yy - r))


def _panel_sprite(w, h, color, border, radius, width):
    s = surface(w * 2, h * 2)
    top = lighten(color, 0.14)
    bot = darken(color, 0.10)
    body = shaped(w * 2, h * 2, [top, color, bot],
                  lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=radius * 2))
    s.blit(body, (0, 0))
    gloss = surface(w * 2, h * 2)
    pygame.draw.rect(gloss, (255, 255, 255, 34), (width * 2 + 4, width * 2 + 4, w * 2 - width * 4 - 8,
                                                  min(h, 60)), border_radius=radius * 2)
    s.blit(gloss, (0, 0))
    if width:
        pygame.draw.rect(s, rgba(border), s.get_rect(), width * 2, border_radius=radius * 2)
    spr = down(s, w, h)
    sh, pad = soft_shadow(spr, blur=8, alpha=120)
    return spr, sh, pad


def panel(surf, rect, color=(255, 246, 222), border=(34, 24, 48), radius=18, width=4, alpha=None, shadow=True):
    rect = pygame.Rect(rect)
    spr, sh, pad = cached(("panel", rect.w, rect.h, tuple(color), tuple(border), radius, width),
                          lambda: _panel_sprite(rect.w, rect.h, color, border, radius, width))
    if alpha is not None:
        spr = spr.copy()
        spr.set_alpha(alpha)
    if shadow and alpha is None:
        surf.blit(sh, (rect.x - pad + 2, rect.y - pad + 6))
    surf.blit(spr, rect)


def pill(surf, rect, color, border=C.INK, radius=10, width=3):
    panel(surf, rect, color, border, radius, width, shadow=False)


def dim(surf, alpha=150):
    s = cached(("dim", alpha), lambda: surface(C.W, C.H, (10, 4, 20, alpha)))
    surf.blit(s, (0, 0))


# ========================================================================== gallery
GW, GH = C.GAL_X1 - C.GAL_X0, C.GAL_BOTTOM - C.GAL_TOP


def _gallery_back():
    s = grad(GW, GH, [(36, 52, 110), (22, 30, 70), (12, 14, 36)])
    # star wallpaper
    pat = surface(GW, GH)
    for row in range(0, GH, 46):
        for col in range(0, GW, 46):
            x = col + (23 if (row // 46) % 2 else 0)
            y = row + 20
            pts = []
            for k in range(10):
                a = -math.pi / 2 + k * math.pi / 5
                r = 7 if k % 2 == 0 else 3
                pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
            pygame.draw.polygon(pat, (255, 255, 255, 16), pts)
    s.blit(pat, (0, 0))
    s.blit(glow((120, 160, 255), 420, 0.35), (GW // 2 - 420, -300))
    s.blit(vignette(GW, GH, 170, 2.6), (0, 0))
    # shelf boards behind each belt
    for y in C.BELT_Y:
        yy = y - C.GAL_TOP + C.TILE // 2 + 4
        pygame.draw.rect(s, (8, 10, 26, 120), (0, yy, GW, 24))
    return s


def _curtain(w, h, flip):
    S = 2
    s = surface(w * S, h * S)
    for x in range(w * S):
        u = x / (w * S)
        k = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(u * math.tau * 2.5 + 0.6))
        top = tuple(int(v * k) for v in (200, 30, 56))
        bot = tuple(int(v * k) for v in (110, 10, 30))
        for yseg in range(0, h * S, 8):
            pygame.draw.line(s, rgba(lerp_c(top, bot, yseg / (h * S))), (x, yseg), (x, min(h * S - 1, yseg + 8)))
    # drape shape: pinched at the tie-back
    mask = surface(w * S, h * S)
    tie = int(h * S * 0.58)
    pts = [(0, 0), (w * S, 0)]
    for i in range(21):
        y = i / 20 * h * S
        d = abs(y - tie) / (h * S)
        pts.append((w * S * (0.62 + 0.38 * min(1.0, d * 2.4)), y))
    pts.append((0, h * S))
    pygame.draw.polygon(mask, (255, 255, 255, 255), pts)
    s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    rw = int(w * S * 0.62) + 10
    rope = shaped(rw, 22, [(255, 236, 150), (220, 170, 50), (150, 100, 20)],
                  lambda m, c: pygame.draw.ellipse(m, c, m.get_rect()))
    s.blit(rope, (-6, tie - 11))
    pygame.draw.circle(s, (255, 220, 110, 255), (rw - 10, tie + 14), 6)
    pygame.draw.line(s, (220, 170, 50, 255), (rw - 10, tie + 8), (rw - 10, tie + 34), 4)
    s = down(s, w, h)
    return pygame.transform.flip(s, True, False) if flip else s


def _awning(w):
    S = 2
    h = 44
    s = surface(w * S, h * S)
    stripe = 44 * S
    for i in range(w * S // stripe + 1):
        sx = i * stripe
        red = i % 2 == 0
        stops = [(250, 86, 96), (214, 48, 62), (170, 24, 42)] if red else [(255, 252, 240), (244, 232, 210),
                                                                           (214, 196, 168)]
        piece = shaped(stripe, h * S, stops, lambda m, c: (
            pygame.draw.rect(m, c, (0, 0, stripe, 26 * S)),
            pygame.draw.ellipse(m, c, (0, 14 * S, stripe, 24 * S))))
        s.blit(piece, (sx, 0))
        pygame.draw.line(s, (0, 0, 0, 40), (sx, 0), (sx, 26 * S), 2)
    trim = grad(w * S, 9 * S, [(255, 236, 150), (230, 180, 60), (170, 120, 30)])
    s.blit(trim, (0, 0))
    spr = down(s, w, h)
    return spr


def _gallery_front():
    s = surface(C.W, C.GAL_BOTTOM + 20)
    x0, x1, top, bot = C.GAL_X0, C.GAL_X1, C.GAL_TOP, C.GAL_BOTTOM
    # wooden/gold frame around the window
    outer = pygame.Rect(x0 - 12, top - 8, (x1 - x0) + 24, (bot - top) + 18)
    frame = shaped(outer.w, outer.h, [(196, 130, 70), (140, 84, 40), (96, 54, 24)],
                   lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=12))
    hole = pygame.Rect(12, 8, x1 - x0, bot - top)
    frame.fill((0, 0, 0, 0), hole)
    pygame.draw.rect(frame, (255, 210, 140, 160), (2, 2, outer.w - 4, outer.h - 4), 2, border_radius=11)
    pygame.draw.rect(frame, C.INK + (255,), frame.get_rect(), 3, border_radius=12)
    pygame.draw.rect(frame, (20, 10, 10, 255), hole.inflate(4, 4), 3)
    s.blit(frame, outer.topleft)
    # curtains
    s.blit(_curtain(40, bot - top, False), (x0 - 2, top))
    s.blit(_curtain(40, bot - top, True), (x1 - 38, top))
    # awning + its shadow
    aw = _awning(x1 - x0 + 24)
    sh, pad = soft_shadow(aw, blur=6, alpha=140)
    s.blit(sh, (x0 - 12 - pad, top - 8 - pad + 8))
    s.blit(aw, (x0 - 12, top - 8))
    return s


def bulb_positions():
    return [(x, C.GAL_TOP - 4) for x in range(C.GAL_X0 + 10, C.GAL_X1, 44)]


def draw_gallery_back(surf):
    surf.blit(cached("gallery_back", _gallery_back), (C.GAL_X0, C.GAL_TOP))


def draw_gallery_front(surf, t):
    surf.blit(cached("gallery_front", _gallery_front), (0, 0))
    phase = int(t * 5)
    for i, (x, y) in enumerate(bulb_positions()):
        lit = (i + phase) % 3 != 0
        if lit:
            g = glow_add((255, 190, 90), 16, 0.9)
            surf.blit(g, (x - 16, y - 16), special_flags=pygame.BLEND_ADD)
            surf.blit(dot((255, 246, 200), 4), (x - 5, y - 5))
        else:
            surf.blit(dot((140, 96, 50), 4), (x - 5, y - 5))


def draw_belt_glow(surf, y, t):
    h = C.TILE + 34

    def make():
        g = surface(GW, h, (255, 214, 10, 0))
        for i in range(h):
            k = 1 - abs(i - h / 2) / (h / 2)
            pygame.draw.line(g, (255, 214, 10, int(110 * k ** 0.8)), (0, i), (GW, i))
        pygame.draw.line(g, (255, 230, 120, 230), (0, 0), (GW, 0), 2)
        pygame.draw.line(g, (255, 230, 120, 230), (0, h - 1), (GW, h - 1), 2)
        return g
    g = cached("beltglow", make)
    a = 170 + int(70 * math.sin(t * 6))
    img = g.copy()
    img.set_alpha(a)
    surf.blit(img, (C.GAL_X0, y - C.TILE // 2 - 12))


def _track(width, color):
    S = 2
    s = shaped(width * S, 16 * S, [(200, 204, 222), (120, 124, 146), (60, 62, 80), (38, 38, 52)],
               lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=8 * S))
    pygame.draw.rect(s, rgba(C.INK), s.get_rect(), 2 * S, border_radius=8 * S)
    pygame.draw.line(s, rgba(color), (6 * S, 2 * S), (width * S - 6 * S, 2 * S), 2 * S)
    return down(s, width, 16)


def _rivet():
    S = SS
    s = radial(8 * S, 8 * S, (3 * S, 3 * S), 5 * S, (240, 240, 250), (90, 90, 110))
    m = surface(8 * S, 8 * S)
    pygame.draw.circle(m, (255, 255, 255, 255), (4 * S, 4 * S), 3 * S)
    return down(clip_to(s, m), 8, 8)


def draw_track(surf, x0, x1, y, chain, color):
    ty = y + C.TILE // 2 + 5
    surf.blit(cached(("track", x1 - x0, color), lambda: _track(x1 - x0, color)), (x0, ty))
    rv = cached("rivet", _rivet)
    step = 28
    x = x0 - step + chain % step
    while x < x1 - 6:
        if x > x0 + 4:
            surf.blit(rv, (int(x) - 4, ty + 5))
        x += step


# ====================================================================== tiles etc.
def _tile(ch, color):
    s = C.TILE
    S = s * SS
    r = 15 * SS
    img = surface(S, S)
    body = shaped(S, S, [lighten(color, 0.45), color, darken(color, 0.30)],
                  lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=r))
    img.blit(body, (0, 0))
    inset = 7 * SS
    fw = S - 2 * inset
    face = shaped(fw, fw, [(255, 254, 248), (250, 240, 218), (232, 216, 184)],
                  lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=10 * SS))
    img.blit(face, (inset, inset))
    pygame.draw.rect(img, rgba(darken(color, 0.4)), (inset, inset, fw, fw), 1 * SS, border_radius=10 * SS)
    gloss = surface(S, S)
    pygame.draw.ellipse(gloss, (255, 255, 255, 90), (4 * SS, 2 * SS, S - 8 * SS, 9 * SS))
    img.blit(gloss, (0, 0))
    f = font(40 * SS)
    sh = f.render(ch, True, (0, 0, 0))
    sh.set_alpha(45)
    img.blit(sh, sh.get_rect(center=(S // 2 + SS, S // 2 + 3 * SS)))
    lt = f.render(ch, True, C.INK)
    img.blit(lt, lt.get_rect(center=(S // 2, S // 2 + SS)))
    pygame.draw.rect(img, rgba(C.INK), img.get_rect(), 3 * SS, border_radius=r)
    spr = down(img, s, s)
    sh, pad = soft_shadow(spr, blur=5, alpha=130)
    return spr, sh, pad


def _post():
    return down(shaped(10 * SS, 40 * SS, [(150, 110, 50), (255, 226, 140), (170, 120, 50), (100, 70, 30)],
                       lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=2 * SS), True), 10, 40)


def draw_tile(surf, cx, cy, ch, color, squash=1.0, highlight=False):
    s = C.TILE
    spr, sh, pad = cached(("tile", ch, tuple(color)), lambda: _tile(ch, color))
    surf.blit(cached("post", _post), (cx - 5, cy + 8))
    bottom = cy + s // 2
    if squash >= 0.999:
        surf.blit(sh, (cx - s // 2 - pad + 3, bottom - s - pad + 6))
        surf.blit(spr, (cx - s // 2, bottom - s))
    else:
        h = max(2, int(s * squash))
        surf.blit(pygame.transform.smoothscale(spr, (s, h)), (cx - s // 2, bottom - h))
    if highlight:
        pygame.draw.rect(surf, C.YELLOW, (cx - s // 2 - 4, bottom - s - 4, s + 8, s + 8), 3, border_radius=16)


def _tissue():
    w, h = C.TILE, 92
    W, H = w * SS, h * SS
    img = surface(W, H)
    box_h = 50 * SS
    by = H - box_h
    box = shaped(W, box_h, [(196, 230, 255), (120, 180, 236), (70, 128, 200)],
                 lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=9 * SS))
    deco = surface(W, box_h)
    for i in range(6):
        for j in range(3):
            pygame.draw.circle(deco, (255, 255, 255, 70), (int((i + 0.5 * (j % 2)) * W / 5), int((j + 0.6) * box_h / 3)),
                               3 * SS)
    box.blit(deco, (0, 0), special_flags=0)
    m = surface(W, box_h)
    pygame.draw.rect(m, (255, 255, 255, 255), m.get_rect(), border_radius=9 * SS)
    box = clip_to(box, m)
    img.blit(box, (0, by))
    pygame.draw.ellipse(img, (40, 70, 120, 255), (W // 2 - 18 * SS, by + 4 * SS, 36 * SS, 10 * SS))
    pygame.draw.rect(img, rgba(C.INK), (0, by, W, box_h), 3 * SS, border_radius=9 * SS)
    # puffy tissue
    puff = surface(W, H)
    c = (255, 255, 255, 255)
    prof = [(0.20, 9), (0.24, -6), (0.30, -18), (0.37, -24), (0.43, -20), (0.50, -27), (0.58, -36),
            (0.64, -33), (0.70, -22), (0.76, -10), (0.80, 9)]
    pts = [(W * u, by + v * SS) for u, v in prof]
    pygame.draw.polygon(puff, c, pts)
    shade = grad(W, H, [(255, 255, 255), (250, 252, 255), (205, 215, 232)])
    shade.blit(puff, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    shade = outline(shade, (140, 150, 175), 2 * SS)
    img.blit(shade, (-2 * SS, -2 * SS))
    for x0, y0, x1, y1 in ((0.44, 2, 0.50, -20), (0.58, 2, 0.60, -28), (0.33, 2, 0.36, -16)):
        pygame.draw.line(img, (185, 196, 220, 255), (W * x0, by + y0 * SS), (W * x1, by + y1 * SS), 2 * SS)
    spr = down(img, w, h)
    sh, pad = soft_shadow(spr, blur=5, alpha=120)
    return spr, sh, pad


def draw_tissue(surf, cx, cy, squash=1.0, scale=1.0):
    spr, sh, pad = cached("tissue", _tissue)
    if scale != 1.0:
        spr = pygame.transform.smoothscale(spr, (int(spr.get_width() * scale), int(spr.get_height() * scale)))
    w, h = spr.get_size()
    surf.blit(cached("post", _post), (cx - 5, cy + 8))
    bottom = cy + C.TILE // 2
    if squash >= 0.999:
        if scale == 1.0:
            surf.blit(sh, (cx - w // 2 - pad + 3, bottom - h - pad + 6))
        surf.blit(spr, (cx - w // 2, bottom - h))
    else:
        hh = max(2, int(h * squash))
        surf.blit(pygame.transform.smoothscale(spr, (w, hh)), (cx - w // 2, bottom - hh))


def _booger(r):
    d = r * 2 + 10
    D = d * SS
    c = D // 2
    R = r * SS
    blobs = [(0, 0, 1.0), (0.6, -0.4, 0.7), (-0.5, 0.5, 0.6), (0.35, 0.6, 0.45)]
    m = surface(D, D)
    for bx, by, br in blobs:
        pygame.draw.circle(m, (255, 255, 255, 255), (int(c + bx * R), int(c + by * R)), int(br * R))
    body = radial(D, D, (int(c - 0.35 * R), int(c - 0.4 * R)), int(R * 1.9), (196, 236, 110), (72, 120, 26))
    body = clip_to(body, m)
    spec = surface(D, D)
    pygame.draw.ellipse(spec, (255, 255, 255, 190), (c - 0.62 * R, c - 0.68 * R, 0.55 * R, 0.36 * R))
    pygame.draw.circle(spec, (255, 255, 255, 220), (int(c + 0.15 * R), int(c - 0.55 * R)), max(2, int(0.1 * R)))
    body.blit(spec, (0, 0))
    body = outline(body, (48, 80, 18), max(2, int(1.6 * SS)))
    return down(body, d + 4, d + 4)


def draw_booger(surf, x, y, r=9, wobble=0.0):
    r = max(2, int(r))
    spr = cached(("booger", r), lambda: _booger(r))
    surf.blit(spr, (int(x) - spr.get_width() // 2, int(y) - spr.get_height() // 2))


def _splats():
    out = []
    for v in range(6):
        rnd = random.Random(v * 97 + 5)
        n = 40 * SS
        s = surface(n, n, rgba(C.BOOGER, 0))
        c = n // 2
        base = 10 * SS
        col = (126, 182, 44, 255)
        pygame.draw.circle(s, col, (c, c), base)
        for _ in range(9):
            a = rnd.uniform(0, math.tau)
            d = rnd.uniform(base * 0.6, base * 1.6)
            pygame.draw.circle(s, col, (int(c + math.cos(a) * d), int(c + math.sin(a) * d)),
                               rnd.randint(2 * SS, 5 * SS))
        hl = surface(n, n)
        pygame.draw.circle(hl, (220, 255, 160, 120), (c - 3 * SS, c - 3 * SS), 4 * SS)
        s.blit(hl, (0, 0))
        out.append(down(s, 40, 40))
    return out


def draw_splat(surf, x, y, size, alpha):
    variants = cached("splats", _splats)
    spr = variants[int(x * 7 + y * 3) % len(variants)]
    k = size / 10.0
    img = pygame.transform.smoothscale(spr, (int(40 * k), int(40 * k)))
    img.set_alpha(alpha)
    surf.blit(img, (int(x - 20 * k), int(y - 20 * k)))


# ===================================================================== hand & nose
SKIN_HI = (255, 224, 198)
SKIN_LINE = (160, 100, 80)


def _palm():
    """Palm + curled fingers + thumb + sleeve. Origin = (tip_x - 60, palm_top - 30)."""
    S = 2
    W, H = 190, 660
    s = surface(W * S, H * S)

    def P(*v):
        return [int(a * S) for a in v]
    # sleeve
    sleeve = shaped(150 * S, 540 * S, [(40, 80, 190), (92, 140, 245), (66, 110, 220), (36, 70, 170)],
                    lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=10 * S), True)
    s.blit(sleeve, P(14, 122))
    cuff = shaped(156 * S, 22 * S, [(30, 60, 150), (70, 110, 220), (30, 60, 150)],
                  lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=8 * S), True)
    s.blit(cuff, P(11, 120))
    for x in range(20, 160, 10):
        pygame.draw.line(s, (200, 220, 255, 160), P(x, 131), P(x + 5, 131), S)
    pygame.draw.rect(s, rgba(C.INK), P(11, 120, 156, 22), 2 * S, border_radius=8 * S)
    # palm
    palm = shaped(124 * S, 112 * S, [SKIN_HI, C.SKIN, C.SKIN_DARK],
                  lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=34 * S))
    palm = outline(palm, C.INK, 2 * S)
    s.blit(palm, P(26 - 2, 30 - 2))
    # curled fingers
    for i in range(3):
        kx = 90 + i * 22
        k = radial(34 * S, 34 * S, (13 * S, 11 * S), 26 * S, SKIN_HI, C.SKIN_DARK)
        m = surface(34 * S, 34 * S)
        pygame.draw.circle(m, (255, 255, 255, 255), (17 * S, 17 * S), 15 * S)
        k = outline(clip_to(k, m), SKIN_LINE, S * 2)
        s.blit(k, P(kx - 19, 38 - 19))
    return down(s, W, H)


def _thumb():
    """Thumb drawn separately so it can hold the cocked finger before a flick."""
    S = 2
    th = shaped(40 * S, 64 * S, [C.SKIN_DARK, SKIN_HI, C.SKIN], lambda m, c: pygame.draw.ellipse(m, c, m.get_rect()), True)
    th = outline(th, SKIN_LINE, 2 * S)
    pygame.draw.arc(th, rgba(SKIN_LINE), (16 * S, 14 * S, 20 * S, 30 * S), 1.2, 2.6, S * 2)
    pygame.draw.ellipse(th, (255, 236, 222, 255), (12 * S, 6 * S, 12 * S, 10 * S))   # thumbnail
    pygame.draw.ellipse(th, rgba(SKIN_LINE), (12 * S, 6 * S, 12 * S, 10 * S), S)
    return down(th, th.get_width() // S, th.get_height() // S)


# The pointing finger is three jointed segments (knuckle -> tip) so it can curl
# up against the thumb and snap straight when it flicks.
FINGER_W = 30
PHALANX = (36, 26, 24)            # proximal, middle, distal lengths (sum = C.FINGER_LEN - 6)
KNUCKLE_DY = sum(PHALANX)         # rest fingertip sits this far above the knuckle


def _phalanx(idx):
    fw, L = FINGER_W, PHALANX[idx]
    W, H = fw * SS, (L + fw) * SS
    s = surface(W, H)
    body = shaped(W, H, [(206, 140, 110), (250, 206, 172), SKIN_HI, (240, 190, 156), (200, 134, 104)],
                  lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=fw // 2 * SS), True)
    s.blit(body, (0, 0))
    if idx == 2:   # fingernail + shine
        nail = shaped(18 * SS, 22 * SS, [(255, 240, 236), (248, 206, 198), (236, 180, 172)],
                      lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=8 * SS))
        s.blit(nail, (6 * SS, 4 * SS))
        pygame.draw.rect(s, (220, 150, 140, 255), (6 * SS, 4 * SS, 18 * SS, 22 * SS), SS, border_radius=8 * SS)
        gl = surface(W, H)
        pygame.draw.ellipse(gl, (255, 255, 255, 200), (10 * SS, 7 * SS, 5 * SS, 11 * SS))
        s.blit(gl, (0, 0))
    else:          # knuckle wrinkles near the top joint
        for k in (0, 5):
            pygame.draw.arc(s, rgba(SKIN_LINE, 150), (8 * SS, (fw // 2 - 6 + k) * SS, 14 * SS, 7 * SS),
                            math.pi * 1.15, math.pi * 1.85, SS * 2)
    s = outline(s, SKIN_LINE, 2 * SS)
    return down(s, fw + 4, L + fw + 4)


def _phalanx_rot(idx, angle):
    return pygame.transform.rotozoom(cached(("phalanx", idx), lambda: _phalanx(idx)), angle, 1.0)


def warm_finger(lo=-40, hi=200):
    """Pre-rotate the finger segments so the first flick doesn't stutter."""
    for i in range(3):
        for q in range(lo // 2 * 2, hi + 2, 2):
            cached(("phalanx_rot", i, q), lambda i=i, q=q: _phalanx_rot(i, q))


def finger_joints(bx, by, angles):
    """Joint positions from the knuckle (bx, by); angles are relative bends in degrees, + = curl left."""
    pts = [(bx, by)]
    cum = 0.0
    x, y = bx, by
    for L, a in zip(PHALANX, angles):
        cum += a
        r = math.radians(cum)
        x -= L * math.sin(r)
        y -= L * math.cos(r)
        pts.append((x, y))
    return pts


def draw_hand(surf, tip_x, tip_y, angles=(0.0, 0.0, 0.0), thumb=0.0, booger=False):
    """Hand whose fingertip rests at (tip_x, tip_y) when straight. Returns the actual fingertip."""
    tip_x, tip_y = int(tip_x), int(tip_y)
    palm_top = tip_y + C.FINGER_LEN - 14
    surf.blit(cached("palm", _palm), (tip_x - 60, palm_top - 30))
    bx, by = tip_x, tip_y + KNUCKLE_DY
    pts = finger_joints(bx, by, angles)
    cum = 0.0
    for i, a in enumerate(angles):
        cum += a
        q = int(round(cum / 2.0)) * 2
        img = cached(("phalanx_rot", i, q), lambda i=i, q=q: _phalanx_rot(i, q))
        r = math.radians(q)
        half = PHALANX[i] / 2.0
        cx = pts[i][0] - half * math.sin(r)
        cy = pts[i][1] - half * math.cos(r)
        surf.blit(img, (int(cx - img.get_width() / 2), int(cy - img.get_height() / 2)))
    # thumb: slides up and in to pin the curled fingertip
    th = cached("thumb", _thumb)
    surf.blit(th, (int(tip_x - 58 + 8 * thumb), int(palm_top + 26 - 22 * thumb)))
    tx, ty = pts[-1]
    if booger:
        r = math.radians(cum)
        draw_booger(surf, tx - 5 * math.sin(r), ty - 5 * math.cos(r), 7)
    return tx, ty


def draw_flick_trail(surf, points, strength):
    """Fading swoosh along the path the fingertip just travelled."""
    if len(points) < 2 or strength <= 0:
        return
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    pad = 12
    x0, y0 = int(min(xs)) - pad, int(min(ys)) - pad
    w, h = int(max(xs)) - x0 + pad, int(max(ys)) - y0 + pad
    layer = surface(w, h)
    n = len(points)
    for i in range(1, n):
        k = i / (n - 1)
        a = int(200 * strength * k)
        width = max(1, int(2 + 7 * k))
        p0 = (points[i - 1][0] - x0, points[i - 1][1] - y0)
        p1 = (points[i][0] - x0, points[i][1] - y0)
        pygame.draw.line(layer, (255, 255, 255, a), p0, p1, width)
    surf.blit(layer, (x0, y0))


def nostril_pos(cx=C.NOSE_CX, cy=C.NOSE_CY):
    return (cx - 20, cy + 52)


NOSE_W, NOSE_H, NOSE_OX, NOSE_OY = 200, 190, 100, 90   # sprite size and where (cx, cy) sits


def _nose():
    S = SS
    W, H = NOSE_W * S, NOSE_H * S
    ox, oy = NOSE_OX * S, NOSE_OY * S

    def p(x, y):
        return (int(ox + x * S), int(oy + y * S))
    m = surface(W, H)
    white = (255, 255, 255, 255)
    pygame.draw.polygon(m, white, [p(-16, -70), p(16, -70), p(30, 10), p(-30, 10)])
    pygame.draw.circle(m, white, p(-40, 33), 26 * S)
    pygame.draw.circle(m, white, p(40, 33), 26 * S)
    pygame.draw.circle(m, white, p(0, 22), 38 * S)
    pygame.draw.ellipse(m, white, (*p(-24, -82), 48 * S, 20 * S))
    skin = radial(W, H, p(-14, 4), 120 * S, (255, 226, 204), (210, 140, 110))
    skin = clip_to(skin, m)
    shade = surface(W, H)
    for sx in (-40, 40):
        pygame.draw.ellipse(shade, (150, 80, 60, 70), (*p(sx - 24, 40), 48 * S, 18 * S))
    pygame.draw.ellipse(shade, (150, 80, 60, 50), (*p(-30, 46), 60 * S, 16 * S))
    shade.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    skin.blit(shade, (0, 0))
    hl = glow((255, 255, 255), 22 * S, 0.9)
    skin.blit(hl, (p(-12, 6)[0] - 22 * S, p(-12, 6)[1] - 22 * S))
    for nx in (-34, 6):
        nos = shaped(28 * S, 16 * S, [(40, 14, 18), (100, 46, 46)], lambda mm, c: pygame.draw.ellipse(mm, c, mm.get_rect()))
        skin.blit(nos, p(nx, 44))
    line = rgba((150, 86, 66))
    pygame.draw.line(skin, line, p(-14, -64), p(-26, 2), 2 * S)
    pygame.draw.line(skin, line, p(14, -64), p(26, 2), 2 * S)
    pygame.draw.arc(skin, line, (*p(-64, 8), 48 * S, 48 * S), math.pi * 0.5, math.pi * 1.2, 2 * S)
    pygame.draw.arc(skin, line, (*p(16, 8), 48 * S, 48 * S), -math.pi * 0.2, math.pi * 0.5, 2 * S)
    skin = outline(skin, C.INK, 3 * S)
    spr = down(skin, NOSE_W + 6, NOSE_H + 6)
    sh, pad = soft_shadow(spr, blur=7, alpha=110)
    return spr, sh, pad


def draw_nose(surf, cx=C.NOSE_CX, cy=C.NOSE_CY, t=0.0, wiggle=0.0, shadow=True):
    spr, sh, pad = cached("nose", _nose)
    x = int(cx + wiggle) - NOSE_OX - 3
    y = int(cy) - NOSE_OY - 3
    if shadow:
        surf.blit(sh, (x - pad + 4, y - pad + 7))
    surf.blit(spr, (x, y))
    drip = (math.sin(t * 2) + 1) * 3
    dr = cached(("drip", int(drip)), lambda: _drip(int(drip)))
    surf.blit(dr, (int(cx + wiggle) + 12, int(cy) + 53))


def _drip(extra):
    w, h = 11, 11 + extra
    s = surface(w * SS, h * SS, rgba(C.BOOGER, 0))
    body = shaped(w * SS, h * SS, [(190, 235, 110), (100, 160, 40)], lambda m, c: pygame.draw.ellipse(m, c, m.get_rect()))
    s.blit(body, (0, 0))
    pygame.draw.circle(s, (255, 255, 255, 200), (3 * SS, 4 * SS), SS + 1)
    return down(s, w, h)


# ========================================================================== HUD bits
def _life(alive):
    w, h = 18, 36
    W, H = w * SS, h * SS
    s = surface(W, H)
    if alive:
        b = shaped(W, H, [(206, 140, 110), SKIN_HI, (206, 140, 110)],
                   lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=w // 2 * SS), True)
        s.blit(b, (0, 0))
        pygame.draw.rect(s, (255, 230, 226, 255), (4 * SS, 3 * SS, 10 * SS, 11 * SS), border_radius=4 * SS)
        pygame.draw.rect(s, rgba(C.INK), s.get_rect(), 2 * SS, border_radius=w // 2 * SS)
    else:
        pygame.draw.rect(s, (110, 100, 120, 200), s.get_rect(), 2 * SS, border_radius=w // 2 * SS)
        pygame.draw.line(s, rgba(C.RED), (2 * SS, 4 * SS), (W - 2 * SS, H - 4 * SS), 3 * SS)
        pygame.draw.line(s, rgba(C.RED), (W - 2 * SS, 4 * SS), (2 * SS, H - 4 * SS), 3 * SS)
    return down(s, w, h)


def draw_life_finger(surf, x, y, alive=True, scale=1.0):
    spr = cached(("life", alive), lambda: _life(alive))
    surf.blit(spr, (x - spr.get_width() // 2, y - spr.get_height() // 2))


def draw_clock(surf, x, y, r=13, color=C.WHITE):
    def make():
        d = (r + 3) * 2
        s = surface(d * SS, d * SS, rgba(color, 0))
        c = d * SS // 2
        pygame.draw.circle(s, rgba(color), (c, c), r * SS, 3 * SS)
        pygame.draw.line(s, rgba(color), (c, c), (c, c - (r - 5) * SS), 3 * SS)
        pygame.draw.line(s, rgba(color), (c, c), (c + (r - 6) * SS, c), 3 * SS)
        return down(s, d, d)
    spr = cached(("clock", r, color), make)
    surf.blit(spr, (x - spr.get_width() // 2, y - spr.get_height() // 2))


def draw_arrow(surf, x, y, direction, size=14, color=C.YELLOW):
    def make():
        d = size * 2 + 6
        s = surface(d * SS, d * SS)
        c = d * SS / 2
        k = size * SS
        pts = {"right": [(c - k, c - k), (c + k, c), (c - k, c + k)],
               "left": [(c + k, c - k), (c - k, c), (c + k, c + k)],
               "up": [(c - k, c + k), (c, c - k), (c + k, c + k)],
               "down": [(c - k, c - k), (c, c + k), (c + k, c - k)]}[direction]
        pygame.draw.polygon(s, rgba(color), pts)
        pygame.draw.polygon(s, rgba(C.INK), pts, 2 * SS)
        return down(s, d, d)
    spr = cached(("arrow", direction, size, color), make)
    surf.blit(spr, (x - spr.get_width() // 2, y - spr.get_height() // 2))


def draw_lock(surf, x, y, s=1.0):
    def make():
        w, h = 26, 30
        img = surface(w * SS, h * SS)
        pygame.draw.arc(img, (210, 210, 220, 255), (6 * SS, 1 * SS, 14 * SS, 20 * SS), 0, math.pi, 3 * SS)
        pygame.draw.line(img, (210, 210, 220, 255), (7 * SS, 11 * SS), (7 * SS, 15 * SS), 3 * SS)
        pygame.draw.line(img, (210, 210, 220, 255), (19 * SS, 11 * SS), (19 * SS, 15 * SS), 3 * SS)
        body = shaped(22 * SS, 16 * SS, [(255, 220, 110), (200, 150, 40)],
                      lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=3 * SS))
        img.blit(body, (2 * SS, 13 * SS))
        pygame.draw.circle(img, rgba(C.INK), (13 * SS, 20 * SS), 2 * SS)
        return down(img, w, h)
    spr = cached("lock", make)
    surf.blit(spr, (x - 13, y - 17))


# ======================================================================== particles
class Particles:
    def __init__(self):
        self.items = []

    def burst(self, x, y, color, n=16, speed=220, life=0.7, size=4, gravity=500):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(speed * 0.3, speed)
            self.items.append([x, y, math.cos(a) * v, math.sin(a) * v, life, life, color, size, gravity])

    def update(self, dt):
        alive = []
        for p in self.items:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += p[8] * dt
            p[2] *= 0.99
            p[4] -= dt
            if p[4] > 0:
                alive.append(p)
        self.items = alive

    def draw(self, surf, additive=False):
        for x, y, _vx, _vy, life, maxlife, color, size, _g in self.items:
            r = max(1, int(size * (life / maxlife) + 0.5))
            if additive:
                g = glow_add(color, r * 5, 1.0)
                surf.blit(g, (int(x) - r * 5, int(y) - r * 5), special_flags=pygame.BLEND_ADD)
                core = glow_add(lighten(color, 0.6), r * 2, 1.0)
                surf.blit(core, (int(x) - r * 2, int(y) - r * 2), special_flags=pygame.BLEND_ADD)
            else:
                d = dot(color, r)
                surf.blit(d, (int(x) - r - 1, int(y) - r - 1))


class Fireworks:
    COLORS = [(255, 89, 94), (255, 202, 58), (138, 201, 38), (25, 130, 196),
              (160, 110, 230), (255, 255, 255), (255, 143, 171), (110, 210, 240)]

    def __init__(self, on_boom=None):
        self.rockets = []
        self.sparks = Particles()
        self.trails = Particles()
        self.flashes = []
        self.timer = 0.0
        self.on_boom = on_boom

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.timer = random.uniform(0.25, 0.7)
            self.rockets.append([random.uniform(150, C.W - 150), C.H + 10,
                                 random.uniform(-60, 60), random.uniform(-720, -560),
                                 random.choice(self.COLORS)])
        alive = []
        for r in self.rockets:
            r[0] += r[2] * dt
            r[1] += r[3] * dt
            r[3] += 420 * dt
            self.trails.items.append([r[0], r[1], random.uniform(-20, 20), 40, 0.4, 0.4, (255, 210, 150), 2, 0])
            if r[3] >= -40:
                self.sparks.burst(r[0], r[1], r[4], n=80, speed=330, life=1.5, size=3, gravity=150)
                self.sparks.burst(r[0], r[1], (255, 255, 255), n=18, speed=160, life=0.8, size=2, gravity=90)
                self.flashes.append([r[0], r[1], 0.35, r[4]])
                if self.on_boom:
                    self.on_boom()
            else:
                alive.append(r)
        self.rockets = alive
        self.sparks.update(dt)
        self.trails.update(dt)
        for f in self.flashes:
            f[2] -= dt
        self.flashes = [f for f in self.flashes if f[2] > 0]

    def draw(self, surf):
        for x, y, life, col in self.flashes:
            r = int(140 * (1.4 - life / 0.35))
            g = glow_add(col, max(8, r), life / 0.35 * 0.6)
            surf.blit(g, (int(x) - g.get_width() // 2, int(y) - g.get_height() // 2), special_flags=pygame.BLEND_ADD)
        self.trails.draw(surf, additive=True)
        for r in self.rockets:
            g = glow_add(r[4], 10, 1.0)
            surf.blit(g, (int(r[0]) - 10, int(r[1]) - 10), special_flags=pygame.BLEND_ADD)
        self.sparks.draw(surf, additive=True)


class Popups:
    def __init__(self):
        self.items = []

    def add(self, s, x, y, color=C.WHITE, size=30, life=1.1):
        self.items.append([s, x, y, color, size, life, life])

    def update(self, dt):
        for p in self.items:
            p[2] -= 50 * dt
            p[5] -= dt
        self.items = [p for p in self.items if p[5] > 0]

    def draw(self, surf):
        for s, x, y, color, size, life, maxlife in self.items:
            a = int(255 * min(1.0, life / (maxlife * 0.5)))
            pop = 1.0 + 0.25 * max(0.0, (life - maxlife + 0.15) / 0.15)
            text(surf, s, int(size * pop), color, (x, y), outline=3, ocolor=C.INK, alpha=a)


# ============================================================================= icon
def make_icon(size=256):
    S = 2
    s = surface(256 * S, 256 * S)
    bg = radial(256 * S, 256 * S, (100 * S, 90 * S), 200 * S, (255, 236, 120), (240, 160, 0))
    m = surface(256 * S, 256 * S)
    pygame.draw.circle(m, (255, 255, 255, 255), (128 * S, 128 * S), 122 * S)
    s.blit(clip_to(bg, m), (0, 0))
    pygame.draw.circle(s, rgba(C.INK), (128 * S, 128 * S), 122 * S, 8 * S)
    s = down(s, 256, 256)
    draw_nose(s, 128, 92, 0.0, shadow=True)
    big = pygame.transform.smoothscale(_booger(20), (64, 64))
    s.blit(big, (146, 166))
    if size != 256:
        s = pygame.transform.smoothscale(s, (size, size))
    return s


# ============================================================================ board
def _board(w, h):
    S = 2
    s = shaped(w * S, h * S, [(176, 112, 60), (146, 90, 44), (112, 66, 30)],
               lambda m, c: pygame.draw.rect(m, c, m.get_rect(), border_radius=12 * S))
    grain = surface(w * S, h * S)
    rnd = random.Random(42)
    for _ in range(70):
        y = rnd.uniform(0, h * S)
        x = rnd.uniform(-100, w * S)
        ln = rnd.uniform(80, 400) * S
        pts = [(x + k * ln / 10, y + math.sin(k * 0.9 + y) * 2 * S) for k in range(11)]
        pygame.draw.lines(grain, (70, 36, 12, rnd.randint(25, 60)), False, pts, S)
    for i in range(1, 4):
        y = int(i * h * S / 4)
        pygame.draw.line(grain, (60, 30, 10, 140), (8 * S, y), (w * S - 8 * S, y), 2 * S)
        pygame.draw.line(grain, (230, 170, 110, 60), (8 * S, y + 2 * S), (w * S - 8 * S, y + 2 * S), S)
    m = surface(w * S, h * S)
    pygame.draw.rect(m, (255, 255, 255, 255), m.get_rect(), border_radius=12 * S)
    grain.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(grain, (0, 0))
    pygame.draw.line(s, (240, 190, 130, 200), (14 * S, 4 * S), (w * S - 14 * S, 4 * S), 2 * S)
    pygame.draw.rect(s, rgba(C.INK), s.get_rect(), 3 * S, border_radius=12 * S)
    spr = down(s, w, h)
    sh, pad = soft_shadow(spr, blur=8, alpha=140)
    return spr, sh, pad


def draw_board_bg(surf, rect):
    rect = pygame.Rect(rect)
    spr, sh, pad = cached(("board", rect.w, rect.h), lambda: _board(rect.w, rect.h))
    surf.blit(sh, (rect.x - pad, rect.y - pad + 6))
    surf.blit(spr, rect)


def draw_aim(surf, x, y0, y1, t):
    d = dot((255, 255, 255), 2)
    yy = y0
    k = 0
    while yy > y1 + 12:
        d.set_alpha(120 + int(100 * (0.5 + 0.5 * math.sin(t * 8 - k * 0.6))))
        surf.blit(d, (x - 3, yy - 3))
        yy -= 16
        k += 1
    d.set_alpha(255)

    def ring():
        n = 32 * SS
        s = surface(n, n, rgba(C.YELLOW, 0))
        pygame.draw.circle(s, rgba(C.YELLOW), (n // 2, n // 2), 13 * SS, 3 * SS)
        for a in range(4):
            ang = a * math.pi / 2
            p0 = (n / 2 + math.cos(ang) * 8 * SS, n / 2 + math.sin(ang) * 8 * SS)
            p1 = (n / 2 + math.cos(ang) * 16 * SS, n / 2 + math.sin(ang) * 16 * SS)
            pygame.draw.line(s, rgba(C.YELLOW), p0, p1, 3 * SS)
        return down(s, 32, 32)
    surf.blit(cached("aimring", ring), (x - 16, y1 - 16))
