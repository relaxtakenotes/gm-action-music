#pragma once

//#include <SDL2/SDL.h>

#include "imgui/imgui.h"

struct s_key {
	float time = 0;
	bool pressed = false;
	bool released = false;
};

namespace ui {
	extern uint8_t* keystate;

	s_key is_key_pressed(int key);

	void style();
	void init();
	void shutdown();
	void render();
}