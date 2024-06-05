#include <string>
#include <vector>
#include <filesystem>
#include <unordered_map>

#include "processor.h"
#include "songs.h"
#include "misc.h"
#include "dependency_resolver.h"

namespace fs = std::filesystem;

namespace processor {
	std::string pack_name;
	int threads = 4;
	int quality = 4;

	int target = 0;
	int processed = 0;

	std::string preview_path = "none";

	TSQueue<song> queue;

	std::string construct_ffmpeg_command(song unit) {
		float duration = 0;

		std::vector<std::string> effects;
		std::string splicing;

		auto output = exec(qstr(dependency_resolver::ffmpeg) + " -i " + qstr(unit.path) + " -af \"volumedetect\" -vn -sn -dn -f null NUL 2>&1");

		{
			auto matches = get_matches(R"(Duration: \d\d:\d\d:\d\d)", output);

			if (matches.size() <= 0)
				return "invalid";

			std::string str = matches[0];

			str = replace_substr("Duration: ", "", str);
			str = replace_substr(".", "", str);

			duration += std::stof(str.substr(0, 2)) * 60 * 60;
			duration += std::stof(str.substr(3, 2)) * 60;
			duration += std::stof(str.substr(6, 2));

			//printf("%0.2f\n", duration);
		}
		
		if (unit.normalize) {
			auto matches = get_matches(R"(max_volume: .* dB)", output);

			if (matches.size() > 0) {
				std::string str = matches[0];

				str = replace_substr("dB", "", str);
				str = replace_substr(" ", "", str);
				str = replace_substr("max_volume:", "", str);
				str = replace_substr("-", "", str);

				printf("[PROCESSOR: %s] Max volume is %s\n", unit.path.c_str(), str.c_str());

				if (str != "0.0")
					effects.push_back("volume=" + str + "dB");
			}
		}

		if (unit.start > 0) {
			splicing.append(" -ss " + float_to_string(unit.start));
		}

		if (unit.end > 0) {
			auto relative = unit.end - unit.start;
			//if (relative <= 0)
			//	printf("[%s]: Very illegal relative float.\n", unit.path.c_str());
			splicing.append(" -t " + float_to_string(relative));
		}

		if (unit.fade_start > 0) {
			effects.push_back("afade=t=in:st=" + float_to_string(unit.start) + ":d=" + float_to_string(unit.fade_start));
		}

		if (unit.fade_end > 0) {
			if (unit.end > 0)
				effects.push_back("afade=t=out:st=" + float_to_string(unit.end - unit.fade_end) + ":d=" + float_to_string(unit.fade_end));
			else
				effects.push_back("afade=t=out:st=" + float_to_string(duration - unit.fade_end) + ":d=" + float_to_string(unit.fade_end));
		}

		std::string s_effects;

		for (int i = 0; i < (int)effects.size(); i++) {
			if (i == 0)
				s_effects.append(effects[i]);
			else
				s_effects.append("," + effects[i]);
		}

		if (effects.size() > 0) {
			s_effects.insert(0, " -af \"");
			s_effects.append("\"");
		}

		return qstr(dependency_resolver::ffmpeg) + " -y -i " + qstr(unit.path) + s_effects + splicing + " -aq " + std::to_string(quality) + " -map a ";
	}

	bool process(song unit) {
		if (unit.action == "unknown")
			return false;

		auto filename = remove_illegal_chars(remove_extension(unit.name));

		auto directory = output_path + "\\" + remove_illegal_chars(pack_name) + "\\sound\\am_music\\" + unit.action + "\\";

		fs::create_directories(directory);

		auto end_path = qstr(directory + filename + ".ogg");

		auto cmd = construct_ffmpeg_command(unit);

		if (cmd == "invalid")
			return false;

		exec(cmd + " " + end_path);

		return true;
	}

	void _process_all() {
		processed = 0;
		target = 0;

		for (int i = 0; i < songs::list.size(); i++) {
			if (songs::list[i].action == "unknown") continue;

			queue.push(songs::list[i]);
			target++;
		}
		
		for (int i = 0; i < threads; i++) {
			std::thread([]() {
				while (true) {
					auto unit = queue.pop();

					if (unit.action.size() <= 0)
						break;

					process(unit);

					processed++;
				}
			}).detach();
		}
	}

	void process_all() {
		std::thread(_process_all).detach();
	}

	std::string get_preview_path(song unit) {
		static std::hash<std::string> hasher;

		auto hash = hasher(unit.path + 
			std::to_string(unit.start) + 
			std::to_string(unit.end) + 
			std::to_string(unit.fade_start) + 
			std::to_string(unit.fade_end) +
			std::to_string(unit.normalize)
		);

		auto end_path = relpath("data\\preview_" + std::to_string(hash) + ".ogg");
		return end_path;
	}

 	void _preview(song unit) {
		auto end_path = get_preview_path(unit);

		auto cmd = construct_ffmpeg_command(unit);

		if (cmd == "invalid")
			return;

		exec(cmd + " " + qstr(end_path));

		preview_path = end_path;
	}

	void preview(song unit) {
		std::thread(_preview, unit).detach();
	}
}