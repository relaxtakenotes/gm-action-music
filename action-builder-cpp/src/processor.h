#pragma once


#include "songs.h"

namespace processor {
	extern std::string pack_name;
	extern int threads;
	extern int quality;

	extern int target;
	extern int processed;

	extern std::string preview_path;

	bool process(song unit);
	void process_all();

	std::string get_preview_path(song unit);
	void preview(song unit);
}