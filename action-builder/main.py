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

import win32gui, win32con

width, height = 720, 850

done = False

def win_enum_handler(hwnd, ctx):
    global done
    if done:
        return
    if win32gui.IsWindowVisible(hwnd):
        text = win32gui.GetWindowText(hwnd)
        if "Action Builder" in text:
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            done = True

def main():
    win32gui.EnumWindows(win_enum_handler, None)
    
    c_ui = None
    try:
        c_ui = gui()
        window, gl_context = impl_pysdl2_init()
        imgui.create_context()
        impl = SDL2Renderer(window)

        running = True
        event = SDL_Event()

        w_width, w_height = ctypes.c_int(), ctypes.c_int()
        SDL_GetWindowSize(window, ctypes.byref(w_width), ctypes.byref(w_height))
        
        d_width, d_height = ctypes.c_int(), ctypes.c_int()
        SDL_GL_GetDrawableSize(window, ctypes.byref(d_width), ctypes.byref(d_height))
        
        w_width = w_width.value
        w_height = w_height.value
        d_width = d_width.value
        d_height = d_height.value
        
        font_scaling_factor = max(float(d_width) / w_width, float(d_height) / w_height)
        font_size_in_pixels = 16

        io = imgui.get_io()
        custom_font = io.fonts.add_font_from_file_ttf(r"roboto.ttf", font_size_in_pixels * font_scaling_factor)
        io.font_global_scale /= font_scaling_factor
        
        impl.refresh_font_texture()

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

            with imgui.font(custom_font):
                #imgui.show_style_editor()
                c_ui.render(width=w.value, height=h.value, mx=mx.value, my=my.value, buttonstate=sdl2.ext.mouse.ButtonState(button_state))

            gl.glClearColor(0, 0, 0, 1)
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

    DWMWA_USE_IMMERSIVE_DARK_MODE = ctypes.c_int(20)

    wminfo = SDL_SysWMinfo()
    SDL_VERSION(wminfo)
    SDL_GetWindowWMInfo(window, ctypes.byref(wminfo))

    wm_window = wminfo.info.win.window

    state = ctypes.c_int(2)
    ctypes.windll.dwmapi.DwmSetWindowAttribute(wm_window, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(state), ctypes.sizeof(state))

    SDL_UpdateWindowSurface(window)
    SDL_MinimizeWindow(window)
    SDL_RestoreWindow(window)

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