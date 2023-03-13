python build.py build
mkdir build\exe.win-amd64-3.11\input\
mkdir build\exe.win-amd64-3.11\output\
mkdir build\exe.win-amd64-3.11\tools\
mkdir build\exe.win-amd64-3.11\tools\yt-dlp\
mkdir build\exe.win-amd64-3.11\tools\mpv\
copy tools\mpv\updater.bat build\exe.win-amd64-3.11\tools\mpv\updater.bat
copy tools\mpv\updater.ps1 build\exe.win-amd64-3.11\tools\mpv\updater.ps1
copy SDL2.dll build\exe.win-amd64-3.11\SDL2.dll