import sys
from cx_Freeze import setup, Executable

# base="Win32GUI" should be used only for Windows GUI app
base = "Win32GUI" if sys.platform == "win32" else None
build_exe_options = {"packages": ["OpenGL", "khinsider"], "excludes": ['cx_Freeze','pydoc_data','setuptools','distutils','tkinter'], "include_msvcr": True, "zip_include_packages": "*", "zip_exclude_packages": ""}

setup(
    name="Action Music",
    version="1.0",
    description="Action Music Pack Builder",
    options = {"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base)],
)