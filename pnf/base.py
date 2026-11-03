class Scene:
    """Base class: one screen of the game."""

    music = "menu"   # background track to play while this scene is shown (None = leave as is)

    def __init__(self, app):
        self.app = app
        self.t = 0.0

    def t_(self, key, **kw):
        return self.app.t(key, **kw)

    def handle(self, event):
        pass

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        pass

    def on_enter(self):
        pass

    def on_exit(self):
        pass
