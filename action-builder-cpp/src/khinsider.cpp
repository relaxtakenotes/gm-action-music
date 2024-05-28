#include <string>
#include <regex>
#include <filesystem>
#include <thread>
#include <unordered_map>

#include "misc.h"

namespace fs = std::filesystem;

namespace khinsider {
	bool working = false;
	int amount_of_songs = 0;
	int downloaded = 0;
	int failed = 0;

	TSQueue<std::string> queue;

	void _download(std::string url) {

		std::string code;

		if (url.find("/") != std::string::npos) {
			code = get_filename(url);
		} else {
			code = url;
		}
		
		auto album_page = open_page("https://downloads.khinsider.com/game-soundtracks/album/" + code);

		auto matches = get_matches(R"(<td class=\"clickable-row\" align=\"right\"><a href=\"\/game-soundtracks\/album\/.*\" style=\"font-weight:normal;\">.*<\/a><\/td>)", album_page);

		std::unordered_map<std::string, bool> processed_hrefs;

		for (int i = 0; i < matches.size(); i++) {
			try {
				//printf("[MATCH %d]%s\n", i, matches[i].c_str());

				auto indirect_url = get_matches(R"(\"\/game-soundtracks\/album\/.*\/.*\.mp3\")", matches[i])[0];

				indirect_url = replace_substr("\"", "", indirect_url);

				if (processed_hrefs[indirect_url])
					continue;

				processed_hrefs[indirect_url] = true;

				queue.push(indirect_url);

				amount_of_songs++;
			} catch (...) { failed++; }
		}

		for (int i = 0; i < 4; i++) {
			std::thread([]() {
				while (true) {
					auto download_url = queue.pop();

					if (download_url.size() <= 0) {
						working = false;
						break;
					}

					try {
						auto download_page = open_page("http://downloads.khinsider.com" + download_url);

						auto j_matches = get_matches(R"(<p><a href=\".*\"><span class=\"songDownloadLink\"><i class=\"material-icons\">get_app<\/i>Click here to download as MP3<\/span><\/a>.*<\/p>)", download_page);
						if (j_matches.size() <= 0) {
							//printf("[OPEN PAGE] No matches, wtf?-------\n\n%s-------\n\n", download_page.c_str());
							throw("no matches for download page");
						}

						auto direct_urls = get_matches(R"(https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()!@:%_\+.~#?&\/\/=]*))", j_matches[0]);

						if (direct_urls.size() <= 0) {
							//printf("[OPEN PAGE] No matches, wtf?-------\n\n%s-------\n\n", j_matches[0].c_str());
							throw("no matches for direct urls");
						}

						if (!download_file(direct_urls[0], input_path + "\\" + remove_illegal_chars(url_decode(get_filename(direct_urls[0]))))) {
							//printf("[download_file] failed to download %s\n", direct_urls[0].c_str());
							throw("unable to download");
						}

						downloaded++;
					} catch (...) { failed++; }
				}
			}).detach();
		}
	}

	void download(std::string code) {
		if (working) return;

		working = true;
		amount_of_songs = 0;
		downloaded = 0;
		failed = 0;

		std::thread(_download, code).detach();
	}
}