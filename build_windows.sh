#!/usr/bin/env bash
# Cross-build the Windows .exe from Linux using Wine + a private Windows Python.
# (On Windows itself, run build_windows.bat instead.)
# Output: builds/PickNFlick-v<version>-windows.exe
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
VERSION="$(python3 -c 'import pnf; print(pnf.__version__)')"
OUT="$ROOT/builds"
WORK="$OUT/windows"
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine-picknflick}"
export WINEDEBUG=-all
PYVER="3.11.9"
WINPY='C:\Python311\python.exe'

mkdir -p "$OUT" "$WORK"
python3 tools/make_icons.py

# One-time setup: unpack the official Python NuGet package (no installer GUI needed).
if [ ! -f "$WINEPREFIX/drive_c/Python311/python.exe" ]; then
    echo "Setting up Windows Python $PYVER in $WINEPREFIX ..."
    wineboot -i >/dev/null 2>&1 || true
    curl -sL -o "$WORK/python.nupkg" "https://www.nuget.org/api/v2/package/python/$PYVER"
    rm -rf "$WORK/nupkg" && mkdir -p "$WORK/nupkg"
    (cd "$WORK/nupkg" && unzip -q "$WORK/python.nupkg")
    mkdir -p "$WINEPREFIX/drive_c/Python311"
    cp -r "$WORK/nupkg/tools/"* "$WINEPREFIX/drive_c/Python311/"
    wine "$WINPY" -m ensurepip < /dev/null 2>&1 | cat
    wine "$WINPY" -m pip install --no-warn-script-location -r requirements-build.txt < /dev/null 2>&1 | cat
fi

W() { winepath -w "$1"; }
python3 tools/make_version_info.py "$WORK/version_info.txt"
wine "$WINPY" -m PyInstaller --noconfirm --clean --onefile --windowed \
    --name "PickNFlick" \
    --icon "$(W "$ROOT/assets/icon.ico")" \
    --version-file "$(W "$WORK/version_info.txt")" \
    --add-data "$(W "$ROOT/assets");assets" \
    --distpath "$(W "$WORK/dist")" --workpath "$(W "$WORK/work")" --specpath "$(W "$WORK")" \
    "$(W "$ROOT/main.py")" < /dev/null 2>&1 | cat

cp "$WORK/dist/PickNFlick.exe" "$OUT/PickNFlick-v${VERSION}-windows.exe"
echo "Built $OUT/PickNFlick-v${VERSION}-windows.exe"
