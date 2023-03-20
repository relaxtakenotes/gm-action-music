python build.py build
mkdir build\exe.win-amd64-3.11\input\
mkdir build\exe.win-amd64-3.11\output\
mkdir build\exe.win-amd64-3.11\tools\
copy SDL2.dll build\exe.win-amd64-3.11\SDL2.dll
sleep 5
python compress.py