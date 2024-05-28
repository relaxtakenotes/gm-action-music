#pragma once

#include "miniaudio.h"


namespace playback {
	extern ma_decoder decoder;
	extern ma_device device;
	extern ma_device_config deviceConfig;

	extern int index;
	extern bool playing;
	extern bool loaded;

	void init(std::string path, float volume);
	void shutdown();

	float get_visual_time();
	float get_time();
	float get_duration();
	float get_volume();

	void set_time(float time);
	void set_volume(float vol);

	void play();
	void stop();
	void toggle();
}