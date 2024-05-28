#include <filesystem>
#include <string>
#include <thread>

#include "dependency_resolver.h"
#include "misc.h"
#include "picounzip.h"


namespace fs = std::filesystem;

namespace dependency_resolver {
	std::string ffmpeg_status = "Nothing.";
	std::string ytdlp_status = "Nothing.";
	std::string gmpublisher_status = "Nothing.";

	std::string ffmpeg = "none";
	std::string ytdlp = "none";
	std::string gmpublisher = "none";

	void _install_ffmpeg() {
		auto result = exec("where ffmpeg");
		if (result.size() > 0) {
			result.erase(result.size() - 1);
			ffmpeg = result;
			ffmpeg_status = "FFMpeg found in system path. It's installed.";
			return;
		}
		
		auto path = relpath("data\\ffmpeg.exe");
		if (file_exists(path)) {
			ffmpeg = path;
			ffmpeg_status = "FFMpeg found near the executable. It's installed.";
			return;
		}

		ffmpeg_status = "FFMpeg not found. Installing...";

		bool saved = download_file(
			"https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
			relpath("data\\ffmpeg.zip")
		);

		if (!saved) {
			ffmpeg_status = "Failed to download the ffmpeg archive.";
			return;
		}

		ffmpeg_status = "FFMpeg archive downloaded. Extracting.";

		{
			picounzip::unzip zip(relpath("data\\ffmpeg.zip"));
			zip.extractall(relpath("data\\"));
		}

		ffmpeg_status = "Extracted. Moving files.";

		for (const auto& entry : fs::directory_iterator(relpath("data\\ffmpeg-master-latest-win64-gpl\\bin\\")))
			fs::rename(entry.path(), relpath("data\\" + entry.path().filename().u8string()));

		ffmpeg = relpath("data\\ffmpeg.exe");
		ffmpeg_status = "Cleaned up and done. FFMpeg is installed.";

		std::this_thread::sleep_for(std::chrono::milliseconds(500));

		fs::remove_all(relpath("data\\ffmpeg-master-latest-win64-gpl\\").c_str());
		fs::remove(relpath("data\\ffmpeg.zip").c_str());
	}

	void install_ffmpeg() {
		std::thread thread(_install_ffmpeg);
		thread.detach();
	}

	std::string get_ytdlp_path() {
		auto result = exec("where yt-dlp");
		if (result.size() > 0) {
			result.erase(result.size() - 1);
			return result;
		}

		auto path = relpath("data\\yt-dlp.exe");
		if (file_exists(path)) {
			return path;
		}

		return "none";
	}

	void _install_ytdlp () {
		ytdlp = get_ytdlp_path();
		if (ytdlp != "none") {
			ytdlp_status = "yt-dlp found.";
			return;
		}

		bool saved = download_file(
			"https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
			relpath("data\\yt-dlp.exe")
		);

		if (!saved) {
			ytdlp_status = "Failed to download yt-dlp.exe";
			return;
		}

		ytdlp = relpath("data\\yt-dlp.exe");
		ytdlp_status = "yt-dlp.exe downloaded. It's installed.";
	}

	void install_ytdlp() {
		std::thread thread(_install_ytdlp);
		thread.detach();
	}

	std::string get_gmpublisher_path() {
		HKEY result;
		if (RegConnectRegistryA(NULL, HKEY_LOCAL_MACHINE, &result) != ERROR_SUCCESS)
			return "none";
		
		HKEY second_result;
		if (RegOpenKeyA(result, "SOFTWARE\\Classes\\gmpublisher.gma.Document\\shell\\open\\command", &second_result) != ERROR_SUCCESS)
			return "none";

		char data[1024];
		long size = 1024;
		if (RegQueryValueA(second_result, NULL, data, &size) != ERROR_SUCCESS)
			return "none";

		return replace_substr("\"", "", replace_substr(" -e \"%1\"", "", std::string{ data, data + strlen(data)}));
	}

	void _install_gmpublisher() {
		gmpublisher = get_gmpublisher_path();
		if (gmpublisher != "none") {
			gmpublisher_status = "gmpublisher found.";
			return;
		}

		gmpublisher_status = "gmpublisher not found. Installing...";

		bool saved = download_file(
			"https://github.com/WilliamVenner/gmpublisher/releases/download/2.9.2/gmpublisher_2.9.2_x64.msi",
			relpath("gmpublisher.msi")
		);

		if (!saved) {
			gmpublisher_status = "Failed to download gmpublisher.msi";
			return;
		}

		gmpublisher_status = "gmpublisher.msi downloaded. Finish the install process.";
		exec(qstr(relpath("gmpublisher.msi")));
		
		gmpublisher = get_gmpublisher_path();
		if (gmpublisher != "none") {
			gmpublisher_status = "gmpublisher found.";
		} else {
			gmpublisher_status = "gmpublisher not found.";
		}

		std::this_thread::sleep_for(std::chrono::milliseconds(500));
		fs::remove(relpath("gmpublisher.msi").c_str());
	}

	void install_gmpublisher() {
		std::thread thread(_install_gmpublisher);
		thread.detach();
	}
}