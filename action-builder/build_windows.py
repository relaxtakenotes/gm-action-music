import subprocess
import os
from pathlib import Path
import shutil
import traceback
try:
    print("Freezing...")
    subprocess.run("python _freeze_windows.py build", shell=True)

    print("Creating directories...")
    os.mkdir("build\\exe.win-amd64-3.11\\tools")
    os.mkdir("build\\exe.win-amd64-3.11\\input")
    os.mkdir("build\\exe.win-amd64-3.11\\output")

    print("Copying files...")
    shutil.copyfile("SDL2.dll", "build\\exe.win-amd64-3.11\\SDL2.dll")
    shutil.copyfile("roboto.ttf", "build\\exe.win-amd64-3.11\\roboto.ttf")

    print("Compressing binaries...")
    for path in Path('build\\exe.win-amd64-3.11\\').rglob('*.dll'):
        print(f"upx --best \"{os.path.abspath(path)}\"")
        subprocess.run(f"upx -3 \"{os.path.abspath(path)}\"")
    for path in Path('build\\exe.win-amd64-3.11\\').rglob('*.pyd'):
        print(f"upx --best \"{os.path.abspath(path)}\"")
        subprocess.run(f"upx -3 \"{os.path.abspath(path)}\"")
                
    os.rename('build\\exe.win-amd64-3.11\\main.exe', 'build\\exe.win-amd64-3.11\\Action Builder.exe')

    print("Packaging...")
    if os.path.isfile("build\\release.7z"):
        os.remove("build\\release.7z")
    subprocess.run("7z a -t7z -mx9 build\\release.7z build\\exe.win-amd64-3.11\\")
except Exception as e:
    print(traceback.format_exc())
    input()
