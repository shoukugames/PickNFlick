"""Window, main loop and scene switching."""
import os
import random

os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "1")   # smooth (linear) scaling when the window is resized

import pygame  # noqa: E402

from . import config as C
from . import gfx
from .audio import Audio
from .music import Music
from .i18n import tr
from .storage import Store


class App:
    def __init__(self, store_path=None):
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption("Pick 'n' Flick")
        try:
            pygame.display.set_icon(gfx.make_icon(64))
        except pygame.error:
            pass
        self.screen = pygame.display.set_mode((C.W, C.H), pygame.SCALED | pygame.RESIZABLE)
        self.canvas = pygame.Surface((C.W, C.H))
        self.clock = pygame.time.Clock()
        self.store = Store(store_path)
        self.audio = Audio(self.store.settings.get("sound", True))
        self.music = Music(self.audio, self.store.settings.get("music", True))
        self.running = True
        self._shake = 0.0
        pygame.key.stop_text_input()
        from .scenes import MenuScene
        self.scene = MenuScene(self)
        self.music.play(self.scene.music)

    # -- helpers ----------------------------------------------------------
    def t(self, key, **kw):
        return tr(self.store.settings.get("lang", "en"), key, **kw)

    def set_scene(self, scene):
        self.scene.on_exit()
        self.scene = scene
        if scene.music:
            self.music.play(scene.music)
        scene.on_enter()

    def shake(self, amount):
        self._shake = max(self._shake, amount)

    def toggle_music(self):
        s = self.store.settings
        s["music"] = not s["music"]
        self.music.set_enabled(s["music"])
        self.store.save()

    def toggle_sound(self):
        s = self.store.settings
        s["sound"] = not s["sound"]
        self.audio.enabled = s["sound"]
        self.store.save()

    # -- loop -------------------------------------------------------------
    def step(self, dt, events):
        from .scenes import NameEntryScene
        for e in events:
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            elif (e.type == pygame.KEYDOWN and e.key == pygame.K_m
                  and not isinstance(self.scene, NameEntryScene)):
                self.toggle_sound()
            elif (e.type == pygame.KEYDOWN and e.key == pygame.K_b
                  and not isinstance(self.scene, NameEntryScene)):
                self.toggle_music()
            else:
                self.scene.handle(e)
        self.scene.update(dt)
        self.scene.draw(self.canvas)
        ox = oy = 0
        if self._shake > 0:
            self._shake = max(0.0, self._shake - dt)
            m = int(14 * self._shake / 0.45)
            ox, oy = random.randint(-m, m), random.randint(-m, m)
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.canvas, (ox, oy))
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(C.FPS) / 1000.0, 0.05)
            self.step(dt, pygame.event.get())
        self.store.save()
        pygame.quit()
