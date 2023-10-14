import sys
from cx_Freeze import setup, Executable

# base="Win32GUI" should be used only for Windows GUI app
build_exe_options = {"packages": ["OpenGL"], 
                     "excludes": ['cx_Freeze','pydoc_data','setuptools',
                                  'distutils','tkinter','test','Cython',
                                  '_pytest','hypothesis', "Pyinstaller",
                                  'lxml','mypy','pygments',
                                  'pycparser','psutil',
                                  'html','curses'],
                     "include_msvcr": True}

setup(
    name="Action Music",
    version="1.0",
    description="Action Music Pack Builder",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py")],
)

