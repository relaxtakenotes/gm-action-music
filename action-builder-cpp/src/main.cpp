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
#include "imgui/imgui_impl_sdlrenderer2.h"
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
SDL_Renderer* renderer = nullptr;
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

    renderer = SDL_CreateRenderer(pWindow, -1, SDL_RENDERER_PRESENTVSYNC | SDL_RENDERER_ACCELERATED);
    if (renderer == nullptr) {
        printf("Error: SDL_CreateRenderer(): %s\n", SDL_GetError());
        return 0;
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

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();

    io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    io.IniFilename = NULL;
    io.LogFilename = NULL;

    io.Fonts->AddFontFromFileTTF(reinterpret_cast<const char*>(relpath("data\\roboto.ttf").c_str()), 16, NULL, io.Fonts->GetGlyphRangesCyrillic());

    ui::style();

    //ImGui::StyleColorsDark();

    ImGui_ImplSDL2_InitForSDLRenderer(pWindow, renderer);
    ImGui_ImplSDLRenderer2_Init(renderer);
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
    ImGui_ImplSDLRenderer2_NewFrame();
    ImGui_ImplSDL2_NewFrame();
    ImGui::NewFrame();
}

void render_frame() {
    static auto clear_color = ImVec4(0.0f, 0.0f, 0.0f, 1.0f);

    ImGui::Render();
    SDL_RenderSetScale(renderer, io.DisplayFramebufferScale.x, io.DisplayFramebufferScale.y);
    SDL_SetRenderDrawColor(renderer, (Uint8)(clear_color.x * 255), (Uint8)(clear_color.y * 255), (Uint8)(clear_color.z * 255), (Uint8)(clear_color.w * 255));
    SDL_RenderClear(renderer);
    ImGui_ImplSDLRenderer2_RenderDrawData(ImGui::GetDrawData(), renderer);
    SDL_RenderPresent(renderer);
}

void shutdown() {
    ui::shutdown();

    ImGui_ImplSDLRenderer2_Shutdown();
    ImGui_ImplSDL2_Shutdown();
    ImGui::DestroyContext();

    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(pWindow);
    SDL_Quit();

    curl_global_cleanup();
}

LONG VectoredExceptionHandler(_EXCEPTION_POINTERS* ep)
{
    if (ep->ExceptionRecord->ExceptionCode == 0xE06D7363) {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    auto trace = cpptrace::generate_trace().to_string();

    char exception_message[1024];

    snprintf(exception_message, sizeof(exception_message),
        "Base Address: %p\nException Address: %p\nException Code: %lu\nException Flags: %lu\n",
        GetModuleHandleA(NULL),
        ep->ExceptionRecord->ExceptionAddress,
        ep->ExceptionRecord->ExceptionCode,
        ep->ExceptionRecord->ExceptionFlags
    );

    std::string message = std::string("Don't worry. If you see this window, it means all of your progress has been saved.\nPlease copy this message (CTRL+C on the window) and post it on github, along with a way to reproduce it:\n\n" + std::string(exception_message) + trace);

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
