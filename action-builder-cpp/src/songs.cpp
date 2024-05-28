#include <stdio.h>
#include <string>
#include <vector>
#include <filesystem>
#include <fstream>
#include <mutex>

//#include <efsw/efsw.h>
#include <efsw/efsw.hpp>

#include "songs.h"
#include "misc.h"
#include "json.h"

namespace fs = std::filesystem;
using json = nlohmann::json;

namespace songs {
	std::vector<song> list;

	std::mutex lock;

	void add(std::string name,
		std::string action,
		std::string path,
		bool normalize,
		float start,
		float end,
		float fade_start,
		float fade_end)
	{
		song unit;

		unit.name = name;
		unit.action = action;
		unit.path = path;
		unit.normalize = normalize;
		unit.start = start;
		unit.end = end;
		unit.fade_start = fade_start;
		unit.fade_end = fade_end;

		list.push_back(unit);
	}

	void remove(int idx) {
		std::lock_guard<std::mutex> guard(lock);

		list.erase(list.begin() + idx);
	}

	int find_song_by_attr(std::string attr_type, std::string query) {
		for (int i = 0; i < (int)list.size(); i++) {
			if (attr_type == "name" && query == list[i].name)
				return i;
			if (attr_type == "path" && query == list[i].path)
				return i;
		}

		return -1;
	}

	void save() {
		json data = {};

		for (size_t i = 0; i < list.size(); i++) {
			data[i]["name"] = list[i].name;
			data[i]["action"] = list[i].action;
			data[i]["normalize"] = list[i].normalize;
			data[i]["path"] = list[i].path;
			data[i]["start"] = list[i].start;
			data[i]["end"] = list[i].end;
			data[i]["fade_start"] = list[i].fade_start;
			data[i]["fade_end"] = list[i].fade_end;
		}

		std::ofstream file(relpath("data\\songs.json"));

		if (!file.is_open())
			return;

		file << data.dump(4);
		file.close();
	}

	void restore() {
		std::ifstream file(relpath("data\\songs.json"));

		if (!file.is_open())
			return;

		std::string content{ std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>() };

		file.close();

		auto data = json::parse(content);

		for (size_t i = 0; i < data.size(); i++) {
			if (!file_exists(std::string(data[i]["path"])))
				continue; // todo: ideally we'd remove them...
			if (songs::find_song_by_attr("path", std::string(data[i]["path"])) >= 0)
				continue;

			add(
				std::string(data[i]["name"]),
				std::string(data[i]["action"]),
				std::string(data[i]["path"]),
				data[i]["normalize"],
				data[i]["start"],
				data[i]["end"],
				data[i]["fade_start"],
				data[i]["fade_end"]
			);
		}
	}

	class UpdateListener : public efsw::FileWatchListener {
	public:
		void handleFileAction(efsw::WatchID watchid, const std::string& dir, const std::string& filename, efsw::Action action, std::string oldFilename) override {
			switch (action) {
			case efsw::Actions::Add: {
				songs::add(filename, "unknown", input_path + "\\" + filename, false, 0.0f, 0.0f, 0.0f, 0.0f);
				break;
			}
			case efsw::Actions::Delete: {
				int idx = songs::find_song_by_attr("path", input_path + "\\" + filename);
				if (idx < 0)
					break;
				songs::remove(idx);
				break;
			}
			case efsw::Actions::Modified: {
				//std::cout << "DIR (" << dir << ") FILE (" << filename << ") has event Modified"
				//	<< std::endl;
				break;
			}
			case efsw::Actions::Moved: {
				int idx = songs::find_song_by_attr("path", input_path + "\\" + oldFilename);
				if (idx < 0)
					break;
				songs::list[idx].path = input_path + "\\" + filename;
				break;
			}
			default:
				break;
				//std::cout << "Should never happen!" << std::endl;		
			}
		}
	};

	void init() {
		efsw::FileWatcher* fileWatcher = new efsw::FileWatcher();
		UpdateListener* listener = new UpdateListener();
		efsw::WatchID watchID = fileWatcher->addWatch(input_path, listener, true);
		fileWatcher->watch();

		songs::restore();
		for (const auto& entry : fs::directory_iterator(input_path)) {
			if (songs::find_song_by_attr("path", entry.path().u8string()) >= 0)
				continue;
			songs::add(entry.path().filename().u8string(), "unknown", entry.path().u8string(), false, 0.0f, 0.0f, 0.0f, 0.0f);
		}
	}
}