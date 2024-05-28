#pragma once

#include <vector>

#include <mutex>

struct song {
	std::string name;
	std::string action;
	std::string path;
	bool normalize = false;
	float start = 0.0f;
	float end = 0.0f;
	float fade_start = 0.0f;
	float fade_end = 0.0f;
};

namespace songs {
	extern std::vector<song> list;
	extern std::mutex lock;

	void add(
		std::string name,
		std::string action,
		std::string path,
		bool normalize,
		float start,
		float end,
		float fade_start,
		float fade_end
	);
	void remove(int idx);
	int find_song_by_attr(std::string attr_type, std::string query);
	void save();
	void restore();
	void init();
}