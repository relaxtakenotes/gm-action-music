import os
import sys

os.environ["PYSDL2_DLL_PATH"] = os.path.abspath(".")
sys.stdout = open("output.log", "w+")

from sdl2 import *
import sdl2.ext.mouse
import ctypes
import OpenGL.GL as gl
import imgui
from imgui.integrations.sdl2 import SDL2Renderer
from ui import gui
import traceback

width, height = 720, 800

def main():
    c_ui = None
    try:
        c_ui = gui()
        window, gl_context = impl_pysdl2_init()
        imgui.create_context()
        impl = SDL2Renderer(window)

        running = True
        event = SDL_Event()

        while running:
            while SDL_PollEvent(ctypes.byref(event)) != 0:
                if event.type == SDL_QUIT:
                    running = False
                    break
                impl.process_event(event)
            impl.process_inputs()

            imgui.new_frame()

            w, h = ctypes.c_int(), ctypes.c_int()
            SDL_GetWindowSize(window, w, h)

            mx, my = ctypes.c_int(0), ctypes.c_int(0)
            button_state = mouse.SDL_GetMouseState(ctypes.byref(mx), ctypes.byref(my))
                
            c_ui.render(width=w.value, height=h.value, mx=mx.value, my=my.value, buttonstate=sdl2.ext.mouse.ButtonState(button_state))

            gl.glClearColor(0.2, 0.2, 0.2, 1)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)

            imgui.render()
            impl.render(imgui.get_draw_data())
            SDL_GL_SwapWindow(window)

        c_ui.stop()
        impl.shutdown()
        SDL_GL_DeleteContext(gl_context)
        SDL_DestroyWindow(window)
        SDL_Quit()
    except Exception:
        c_ui.stop()
        print(traceback.format_exc())

def dark_title_bar(window):
    ''' 
        These variable names are completely wrong.
        However it works like I want it to and when I change it to be more correct it all fails.
        So lets keep the spaghetti this way... 
    '''

    DWMWA_BORDER_COLOR = ctypes.c_int(20)

    SDL_UpdateWindowSurface(window)
    wminfo = SDL_SysWMinfo()
    SDL_VERSION(wminfo.version)
    SDL_GetWindowWMInfo(window, ctypes.byref(wminfo))
    hwnd = wminfo.info.win.window
    color = ctypes.c_ulong(0x000000FF)
    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_BORDER_COLOR, ctypes.byref(color), ctypes.sizeof(color))

    SDL_UpdateWindowSurface(window)
    SDL_MinimizeWindow(window)
    SDL_RestoreWindow(window)

def impl_pysdl2_init():
    global width, height
    window_name = "Action Music"

    if SDL_Init(SDL_INIT_EVERYTHING) < 0:
        print("Error: SDL could not initialize! SDL Error: " + SDL_GetError().decode("utf-8"))
        exit(1)

    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1)
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24)
    SDL_GL_SetAttribute(SDL_GL_STENCIL_SIZE, 8)
    SDL_GL_SetAttribute(SDL_GL_ACCELERATED_VISUAL, 1)
    SDL_GL_SetAttribute(SDL_GL_MULTISAMPLEBUFFERS, 1)
    SDL_GL_SetAttribute(SDL_GL_MULTISAMPLESAMPLES, 16)
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_FLAGS, SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG)
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 4)
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1)
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE)

    SDL_SetHint(SDL_HINT_MAC_CTRL_CLICK_EMULATE_RIGHT_CLICK, b"1")
    SDL_SetHint(SDL_HINT_VIDEO_HIGHDPI_DISABLED, b"1")

    window = SDL_CreateWindow(window_name.encode('utf-8'),
                              SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                              width, height,
                              SDL_WINDOW_OPENGL|SDL_WINDOW_RESIZABLE)

    dark_title_bar(window)

    if window is None:
        print("Error: Window could not be created! SDL Error: " + SDL_GetError().decode("utf-8"))
        exit(1)

    gl_context = SDL_GL_CreateContext(window)
    if gl_context is None:
        print("Error: Cannot create OpenGL Context! SDL Error: " + SDL_GetError().decode("utf-8"))
        exit(1)

    SDL_GL_MakeCurrent(window, gl_context)
    if SDL_GL_SetSwapInterval(1) < 0:
        print("Warning: Unable to set VSync! SDL Error: " + SDL_GetError().decode("utf-8"))
        exit(1)

    return window, gl_context

if __name__ == "__main__":
    main()