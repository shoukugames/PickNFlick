@echo off
REM Native Windows build. Requires Python 3.9+ on PATH.
cd /d "%~dp0"
python -m pip install -r requirements-build.txt || exit /b 1
python tools\make_version_info.py builds\windows\version_info.txt || exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PickNFlick ^
  --icon assets\icon.ico --version-file builds\windows\version_info.txt --add-data "assets;assets" ^
  --distpath builds\windows\dist --workpath builds\windows\work --specpath builds\windows main.py || exit /b 1
copy /y builds\windows\dist\PickNFlick.exe builds\PickNFlick-v0.2.0-windows.exe
echo Built builds\PickNFlick-v0.2.0-windows.exe
