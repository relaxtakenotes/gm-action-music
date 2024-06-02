#include <stdio.h>
#include <windows.h>
#include <dwmapi.h>
#include <filesystem>
#include <thread>
#include <locale>

#include "ui.h"
#include "misc.h"

#include "imgui/imgui.h"
#include "imgui/imgui_impl_sdl2.h"
#include "imgui/imgui_impl_opengl3.h"
#include <SDL2/SDL.h>
#include <SDL2/SDL_opengl.h>
#include <SDL2/SDL_syswm.h>
#include <curl/curl.h>
#include <cpptrace/cpptrace.hpp>

#pragma comment (lib, "Dwmapi")
#pragma comment (lib, "Kernel32.lib")

namespace fs = std::filesystem;

const char* glslVersion = "#version 130";

int wx = 700;
int wy = 850;

SDL_Window* pWindow = nullptr;
SDL_GLContext glContext = nullptr;
HWND hWindow;
ImGuiIO io;

bool done = false;

int setup_sdl() {
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER | SDL_INIT_GAMECONTROLLER) != 0) {
        printf("Error: %s\n", SDL_GetError());
        return -1;
    }

    SDL_GL_SetAttribute(SDL_GL_CONTEXT_FLAGS, 0);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);

    SDL_SetHint(SDL_HINT_IME_SHOW_UI, "1");

    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
    SDL_GL_SetAttribute(SDL_GL_STENCIL_SIZE, 8);

    return 0;
}

int setup_window() {
    pWindow = SDL_CreateWindow("Action Builder",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        wx, wy,
        (SDL_WindowFlags)(SDL_WINDOW_OPENGL | SDL_WINDOW_ALLOW_HIGHDPI | SDL_WINDOW_RESIZABLE)
    );

    if (pWindow == nullptr) {
        printf("Error: SDL_CreateWindow(): %s\n", SDL_GetError());
        return -1;
    }

    SDL_SysWMinfo wmInfo = {};
    if (!SDL_GetWindowWMInfo(pWindow, &wmInfo)) {
        printf("Error: SDL_GetWindowWMInfo(): %s\n", SDL_GetError());
        return -1;
    }

    hWindow = wmInfo.info.win.window;
    int attr = 1;
    DwmSetWindowAttribute(hWindow, (DWORD)DWMWA_USE_IMMERSIVE_DARK_MODE, &attr, sizeof(attr));

    MARGINS margins = { -1,0,0,0 };
    DwmExtendFrameIntoClientArea(hWindow, &margins);

    //SDL_UpdateWindowSurface(pWindow);
    //SDL_MinimizeWindow(pWindow);
    //SDL_RestoreWindow(pWindow);
    return 0;
}

void setup_base() {
    curl_global_init(CURL_GLOBAL_ALL);

    SetConsoleOutputCP(CP_UTF8);

    std::setlocale(LC_ALL, "C");
    std::setlocale(LC_CTYPE, ".UTF-8");

#ifdef NDEBUG
    // bypasses kaspersky's false detection
    std::thread([]() {
        ShowWindow(GetConsoleWindow(), SW_HIDE);
    }).join();
#endif // !DEBUG

    cpptrace::register_terminate_handler();
    cpptrace::enable_inlined_call_resolution(true);

    glContext = SDL_GL_CreateContext(pWindow);
    SDL_GL_MakeCurrent(pWindow, glContext);
    SDL_GL_SetSwapInterval(1);

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();

    io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    io.IniFilename = NULL;
    io.LogFilename = NULL;

    io.Fonts->AddFontFromFileTTF(reinterpret_cast<const char*>(relpath("data\\roboto.ttf").c_str()), 16, NULL, io.Fonts->GetGlyphRangesCyrillic());

    ui::style();

    //ImGui::StyleColorsDark();

    ImGui_ImplSDL2_InitForOpenGL(pWindow, glContext);
    ImGui_ImplOpenGL3_Init(glslVersion);
}

void handle_events() {
    SDL_Event event;

    while (SDL_PollEvent(&event)) {
        ImGui_ImplSDL2_ProcessEvent(&event);
        if (event.type == SDL_QUIT) {
            done = true;
        }
        
        if (event.type == SDL_WINDOWEVENT) {
            if (event.window.event == SDL_WINDOWEVENT_CLOSE && event.window.windowID == SDL_GetWindowID(pWindow)) {
                done = true;
            }
        }
    }
}

void new_frame() {
    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplSDL2_NewFrame();
    ImGui::NewFrame();
}

void render_frame() {
    glViewport(0, 0, (int)io.DisplaySize.x, (int)io.DisplaySize.y);

    static auto clear_color = ImVec4(0.0f, 0.0f, 0.0f, 1.0f);
    glClearColor(clear_color.x * clear_color.w, clear_color.y * clear_color.w, clear_color.z * clear_color.w, clear_color.w);
    glClear(GL_COLOR_BUFFER_BIT);

    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
    SDL_GL_SwapWindow(pWindow);
}

void shutdown() {
    ui::shutdown();

    ImGui_ImplOpenGL3_Shutdown();
    ImGui_ImplSDL2_Shutdown();
    ImGui::DestroyContext();

    SDL_GL_DeleteContext(glContext);
    SDL_DestroyWindow(pWindow);
    SDL_Quit();

    curl_global_cleanup();
}

LONG VectoredExceptionHandler(_EXCEPTION_POINTERS* ep)
{
    auto trace = cpptrace::generate_trace().to_string();

    char exception_message[1024];

    if (std::to_string(ep->ExceptionRecord->ExceptionCode) == "3765269347") {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    snprintf(exception_message, sizeof(exception_message),
        "Base Address: %p\nException Address: %p\nException Code: %lu\nException Flags: %lu\n",
        GetModuleHandleA(NULL),
        ep->ExceptionRecord->ExceptionAddress,
        ep->ExceptionRecord->ExceptionCode,
        ep->ExceptionRecord->ExceptionFlags
    );

    std::string message = std::string("\n\nDon't worry. If you see this window, it means all of your progress has been saved.\nPlease copy this message (CTRL+C on the window) and post it on github, along with a way to reproduce it:\n\n" + std::string(exception_message) + trace);

    MessageBoxA(hWindow, message.c_str(), "Unexpected Error!", MB_OK | MB_ICONERROR);

    ui::shutdown();

    return EXCEPTION_CONTINUE_SEARCH;
}

#undef main // gib back my main eviell sdl
int main(int, char**) {
    AddVectoredExceptionHandler(0, VectoredExceptionHandler);

    if (setup_sdl() < 0)
        return -1;
    
    if (setup_window() < 0) 
        return -1;

    setup_base();

    ui::init();

    while (!done) {
        handle_events();
        new_frame();

        ui::keystate = (uint8_t*)SDL_GetKeyboardState(0);
        ui::render();

        ImGui::Render();
        render_frame();
    }

    shutdown();

    return 0;
}
