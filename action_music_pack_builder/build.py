import sys
from cx_Freeze import setup, Executable

# base="Win32GUI" should be used only for Windows GUI app
base = "Win32GUI" if sys.platform == "win32" else None
build_exe_options = {"packages": ["OpenGL"], "include_msvcr": True, "zip_include_packages": "*", "zip_exclude_packages": ""}

setup(
    name="AMPB",
    version="0.1",
    description="Action Music Pack Builder",
    options = {"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base)],
)