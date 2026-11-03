#!/usr/bin/env bash
# Build a standalone Linux binary with PyInstaller and wrap it in a .deb package.
# Output: builds/picknflick_v<version>_amd64.deb
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
VERSION="$(python3 -c 'import pnf; print(pnf.__version__)')"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
OUT="$ROOT/builds"
WORK="$OUT/linux"
PY="${PYTHON:-python3}"

mkdir -p "$OUT"
"$PY" tools/make_icons.py

"$PY" -m PyInstaller --noconfirm --clean --onefile --windowed \
    --name picknflick \
    --add-data "$ROOT/assets:assets" \
    --icon "$ROOT/assets/icon.png" \
    --distpath "$WORK/dist" --workpath "$WORK/work" --specpath "$WORK" \
    "$ROOT/main.py"

PKG="$WORK/deb/picknflick_${VERSION}_${ARCH}"
rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN" "$PKG/opt/picknflick" "$PKG/usr/bin" \
         "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/256x256/apps" \
         "$PKG/usr/share/pixmaps" "$PKG/usr/share/doc/picknflick"
install -m 755 "$WORK/dist/picknflick" "$PKG/opt/picknflick/picknflick"
ln -s /opt/picknflick/picknflick "$PKG/usr/bin/picknflick"
install -m 644 packaging/linux/picknflick.desktop "$PKG/usr/share/applications/picknflick.desktop"
install -m 644 assets/icon.png "$PKG/usr/share/icons/hicolor/256x256/apps/picknflick.png"
install -m 644 assets/icon.png "$PKG/usr/share/pixmaps/picknflick.png"
install -m 644 README.md "$PKG/usr/share/doc/picknflick/README.md"
install -m 644 LICENSE "$PKG/usr/share/doc/picknflick/copyright"
install -m 644 assets/fonts/OFL.txt "$PKG/usr/share/doc/picknflick/FONT-LICENSE-OFL.txt"

SIZE_KB="$(du -sk "$PKG" | cut -f1)"
cat > "$PKG/DEBIAN/control" <<CTRL
Package: picknflick
Version: ${VERSION}
Section: games
Priority: optional
Architecture: ${ARCH}
Installed-Size: ${SIZE_KB}
Maintainer: Shouku Games <info@shoukugames.org>
Homepage: https://shoukugames.org/
Description: Booger-flicking spelling shooting gallery for kids
 Pick 'n' Flick is a carnival shooting-gallery spelling game. Pick the nose,
 flick boogers at letters riding three conveyor belts and spell the word
 under the gallery. 10 levels, three age-based difficulties (4+, 8+, 12+),
 English and Japanese, top-10 scores and a parent progress report.
 Created by Shawn Rapaz and Claude Code.
CTRL
cat > "$PKG/DEBIAN/postinst" <<'POST'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
exit 0
POST
chmod 755 "$PKG/DEBIAN/postinst"

dpkg-deb --root-owner-group --build "$PKG" "$OUT/picknflick_v${VERSION}_${ARCH}.deb"
echo "Built $OUT/picknflick_v${VERSION}_${ARCH}.deb"
