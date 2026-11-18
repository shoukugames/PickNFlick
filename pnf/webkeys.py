"""Phones and tablets in a web browser (pygbag): an on-screen key bar plus the device keyboard.

Keyboard-only games can't be played on a touch screen, and a game drawn on a canvas can't open
the phone's keyboard by itself. This adds a small bar of keys (Esc, Tab, arrows, Enter...) and a
keyboard button to the page. The button focuses an invisible text box, so the phone's own keyboard
appears (Japanese input methods included); what is typed there, and the bar's keys, reach the game
as ordinary pygame KEYDOWN / KEYUP / TEXTINPUT events.

    keys = WebKeys(["Escape", "Tab", "ArrowUp", "ArrowDown", "Enter"], keyboard=True)
    ...each frame, before pygame.event.get():
    keys.poll()

Only used in the browser, and only on touch screens; desktop browsers keep the real keyboard.
"""
import json

import pygame

_KEYS = {
    "Enter": (pygame.K_RETURN, "\r"), "Backspace": (pygame.K_BACKSPACE, "\b"), "Tab": (pygame.K_TAB, "\t"),
    "Escape": (pygame.K_ESCAPE, "\x1b"), "Space": (pygame.K_SPACE, " "), "Delete": (pygame.K_DELETE, ""),
    "ArrowUp": (pygame.K_UP, ""), "ArrowDown": (pygame.K_DOWN, ""),
    "ArrowLeft": (pygame.K_LEFT, ""), "ArrowRight": (pygame.K_RIGHT, ""),
}
_LABELS = {"Enter": "Enter", "Backspace": "⌫", "Tab": "Tab", "Escape": "Esc", "Space": "Space", "Delete": "Del",
           "ArrowUp": "▲", "ArrowDown": "▼", "ArrowLeft": "◀", "ArrowRight": "▶"}

_JS = r"""
(function (cfg) {
  if (window.shoukuKeys) return;
  var q = [];
  var push = function (kind, value) { q.push([kind, value]); };
  var inp = document.createElement('input');
  ['autocapitalize', 'autocomplete', 'autocorrect'].forEach(function (a) { inp.setAttribute(a, 'off'); });
  inp.spellcheck = false;
  inp.setAttribute('enterkeyhint', 'send');
  inp.style.cssText = 'position:fixed;left:0;bottom:0;width:1px;height:1px;opacity:0;border:0;padding:0;font-size:16px;';
  var composing = false;
  // Keep these events away from the game's own keyboard handling, which would see them twice.
  ['keyup', 'keypress'].forEach(function (t) { inp.addEventListener(t, function (e) { e.stopPropagation(); }); });
  inp.addEventListener('keydown', function (e) {
    e.stopPropagation();
    if (cfg.special.indexOf(e.key) >= 0) { push('key', e.key); e.preventDefault(); }
  });
  inp.addEventListener('beforeinput', function (e) {  // soft keyboards: backspace on an empty box
    if (e.inputType === 'deleteContentBackward') { push('key', 'Backspace'); e.preventDefault(); }
    if (e.inputType === 'insertLineBreak') { push('key', 'Enter'); e.preventDefault(); }
  });
  inp.addEventListener('compositionstart', function () { composing = true; });
  inp.addEventListener('compositionend', function () { composing = false; if (inp.value) push('text', inp.value); inp.value = ''; });
  inp.addEventListener('input', function (e) {
    e.stopPropagation();
    if (composing || e.isComposing) return;
    if (inp.value) push('text', inp.value);
    inp.value = '';
  });
  var bar = document.createElement('div');
  bar.style.cssText = 'position:fixed;left:50%;transform:translateX(-50%);bottom:4px;display:flex;gap:6px;z-index:1000;' +
    'padding:5px;border-radius:14px;background:rgba(10,14,30,.55);touch-action:manipulation;user-select:none;-webkit-user-select:none;';
  var button = function (label, onpress) {
    var b = document.createElement('button');
    b.textContent = label;
    b.style.cssText = 'min-width:46px;height:40px;padding:0 10px;border-radius:10px;border:1px solid rgba(255,255,255,.35);' +
      'background:rgba(255,255,255,.14);color:#fff;font:600 16px system-ui,sans-serif;';
    b.addEventListener('pointerdown', function (e) { e.preventDefault(); e.stopPropagation(); onpress(); });
    bar.appendChild(b);
  };
  if (cfg.keyboard) button('\u2328', function () { if (document.activeElement === inp) inp.blur(); else inp.focus(); });
  cfg.keys.forEach(function (k) { button(cfg.labels[k] || k, function () { push('key', k); }); });
  document.body.appendChild(inp);
  document.body.appendChild(bar);
  // Sit in the empty margin beside the game when there is room (landscape phones), else at the bottom.
  var place = function () {
    var cv = document.querySelector('canvas');
    var r = cv ? cv.getBoundingClientRect() : null;
    var side = r ? window.innerWidth - r.right : 0;
    var col = side >= 58;
    bar.style.flexDirection = col ? 'column' : 'row';
    bar.style.left = col ? 'auto' : '50%';
    bar.style.right = col ? Math.max(2, (side - 54) / 2) + 'px' : 'auto';
    bar.style.bottom = col ? 'auto' : '4px';
    bar.style.top = col ? '50%' : 'auto';
    bar.style.transform = col ? 'translateY(-50%)' : 'translateX(-50%)';
    [].forEach.call(bar.children, function (b) { b.style.minWidth = col ? '50px' : '46px'; b.style.height = col ? '36px' : '40px'; b.style.padding = col ? '0 4px' : '0 10px'; });
  };
  place();
  window.addEventListener('resize', function () { setTimeout(place, 100); });
  setTimeout(place, 1000); setTimeout(place, 4000);
  window.shoukuKeys = {
    take: function () { var s = JSON.stringify(q); q.length = 0; return s; },
    show: function (on) { bar.style.display = on ? 'flex' : 'none'; if (!on) inp.blur(); }
  };
})(__CONFIG__);
"""


class WebKeys:
    def __init__(self, keys=("Escape", "Tab", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter"),
                 keyboard=True):
        import platform  # pygbag's bridge to the page
        self.window = platform.window
        cfg = {"keys": list(keys), "keyboard": bool(keyboard), "labels": _LABELS, "special": list(_KEYS)}
        self.window.eval(_JS.replace("__CONFIG__", json.dumps(cfg)))

    def show(self, on=True):
        self.window.shoukuKeys.show(bool(on))

    def poll(self):
        """Turn what was pressed on the page since the last frame into pygame events."""
        try:
            items = json.loads(str(self.window.shoukuKeys.take()))
        except Exception:  # noqa: BLE001 - the page bridge must never stop the game
            return
        for kind, value in items:
            if kind == "text":
                for ch in value:
                    if ch == "\n":
                        _key(*_KEYS["Enter"])
                    else:
                        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=ch))
            elif value in _KEYS:
                _key(*_KEYS[value])


def _key(key, unicode):
    for kind in (pygame.KEYDOWN, pygame.KEYUP):
        pygame.event.post(pygame.event.Event(kind, key=key, unicode=unicode, mod=0, scancode=0))


def has_touch_screen():
    try:
        import platform  # pygbag's bridge to the page
        return int(platform.window.navigator.maxTouchPoints) > 0
    except Exception:  # noqa: BLE001
        return False
