# Bug Report

Found a bug in **Pick 'n' Flick**? Thank you for helping! Copy the template below, fill it in, and send it:

- **Email:** info@shoukugames.org (subject: `Pick 'n' Flick bug: <short title>`)
- **Website:** <https://shoukugames.org/>
- Or open an issue in this repository.

Before you report, please check:
1. You are on the latest version (the version number is in the bottom-right of the main menu and on the Credits page).
2. The bug happens more than once, if possible.

---

## Template

```
### Summary
<One sentence: what went wrong?>

### Version & system
- Game version:            (e.g. v0.1.0 - bottom-right of the main menu)
- Package:                 (.deb / Windows .exe / run from source)
- Operating system:        (e.g. Ubuntu 24.04, Debian 12, Windows 11)
- Screen mode:             (window / fullscreen F11)
- Language setting:        (English / 日本語)
- Difficulty:              (Easy 4+ / Medium 8+ / Hard 12+)
- Level when it happened:  (1-10, or menu screen name)

### Steps to reproduce
1.
2.
3.

### What I expected

### What actually happened

### How often?
(every time / sometimes / once)

### Screenshot or video
(attach if you can)

### Save file (optional, very helpful for score/progress bugs)
Linux:   ~/.local/share/PickNFlick/save.json
Windows: %APPDATA%\PickNFlick\save.json

### Error output (optional)
Linux: start the game from a terminal with `picknflick` and paste any text it prints.
Windows: run `PickNFlick-*.exe` from Command Prompt and paste any output.
```

---

## Known limitations

- The Windows `.exe` is unsigned, so SmartScreen may warn the first time you run it ("More info → Run anyway").
- The game is keyboard-only. Gamepad and mouse are not supported yet.
- If no sound device is found, the game runs silently.

## Severity guide (for maintainers)

| Level | Meaning |
|-------|---------|
| Critical | Crash, game won't start, save data lost |
| Major | Can't finish a level, wrong scoring, stuck screen |
| Minor | Visual glitch, translation mistake, typo |
| Suggestion | Ideas and improvements |
