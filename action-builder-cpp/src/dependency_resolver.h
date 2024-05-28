#pragma once

#include <string.h>

namespace dependency_resolver {
	extern std::string ffmpeg_status;
	extern std::string ytdlp_status;
	extern std::string gmpublisher_status;

	extern std::string ffmpeg;
	extern std::string ytdlp;
	extern std::string gmpublisher;

	std::string get_ytdlp_path();
	std::string get_gmpublisher_path();

	void install_ffmpeg();
	void install_ytdlp();
	void install_gmpublisher();
}