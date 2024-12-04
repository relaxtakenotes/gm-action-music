#pragma once

#include <filesystem>
#include <string>
#include <cstdio>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <array>
#include <thread>
#include <regex>
#include <mutex> 
#include <queue>
#include <condition_variable> 
#include <fstream>
#include <cassert>
#include <curl/curl.h>

#include <iostream>
#include <locale>
#include <string>
#include <vector>

namespace fs = std::filesystem;

template <typename T>
class TSQueue {
private:
	std::queue<T> m_queue;
	std::mutex m_mutex;
public:

	void push(T item) {
		std::unique_lock<std::mutex> lock(m_mutex);

		m_queue.push(item);
	}

	T pop() {
		std::unique_lock<std::mutex> lock(m_mutex);

		if (m_queue.empty()) {
			return T();
		}

		T item = m_queue.front();
		m_queue.pop();

		return item;
	}
};

inline std::string input_path = fs::current_path().u8string() + "\\input";
inline std::string output_path = fs::current_path().u8string() + "\\output";

inline auto c_input_path = input_path.c_str();
inline auto c_output_path = output_path.c_str();

inline std::string remove_illegal_chars(std::string path) {
	static const std::string illegal_chars = "\\/:?\"<>|";
	std::string copy;

	for (int i = 0; i < (int)path.size(); i++) {
		if (illegal_chars.find(path[i]) == std::string::npos)
			copy += path[i];
	}

	return copy;
}

inline std::string qstr(std::string input) {
	return std::string("\"" + input + "\"");
}

inline std::string exec(std::string string_cmd) {
	std::string quoted_cmd = qstr(string_cmd);
	auto cmd = quoted_cmd.c_str();

	printf("[EXEC] %s\n", cmd);

    std::array<char, 128> buffer;
    std::string result;
    std::unique_ptr<FILE, decltype(&_pclose)> pipe(_popen(cmd, "r"), _pclose);
    if (!pipe) {
        throw std::runtime_error("popen() failed!");
    }
    while (fgets(buffer.data(), static_cast<int>(buffer.size()), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    return result;
}

inline void async_exec(std::string cmd) {
	std::thread thread(exec, cmd);
	thread.detach();
}

inline void _exec(std::string string_cmd, std::string* output) {
	std::string quoted_cmd = qstr(string_cmd);
	auto cmd = quoted_cmd.c_str();

	printf("[_EXEC] %s\n", cmd);

	std::array<char, 128> buffer;

	std::unique_ptr<FILE, decltype(&_pclose)> pipe(_popen(cmd, "r"), _pclose);
	if (!pipe)
		throw std::runtime_error("popen() failed!");

	while (fgets(buffer.data(), static_cast<int>(buffer.size()), pipe.get()) != nullptr)
		*output += buffer.data();
}

inline void async_exec_output(std::string cmd, std::string *output) {
	std::thread(_exec, cmd, output).detach();
}

inline std::string replace_substr(std::string olds, std::string news, std::string target) {
	size_t start{ target.find(olds) };
	while (start != std::string::npos) {
		target.replace(start, olds.length(), news);
		start = target.find(olds, start + news.length());
	}
	return target;
}

inline std::string get_url_host(const std::string& url) {
	std::regex urlRe("^.*://([^/?:]+)/?.*$");
	return std::regex_replace(url.c_str(), urlRe, "$1");
}

typedef size_t(*curl_write)(char*, size_t, size_t, std::string*);

inline std::string open_page(std::string url) {
	printf("[OPEN_PAGE] Opening %s\n", url.c_str());

	auto curl = curl_easy_init();

	if (!curl) {
		//assert(false); // "Failed to init curl."
		return "";
	}

	std::string buffer_copy;
	CURLcode status_copy;

	for (int i = 0; i < 5; i++) {
		std::string buffer;

		curl_easy_setopt(curl,
			CURLOPT_WRITEFUNCTION,
			static_cast <curl_write> ([](char* contents, size_t size,
				size_t nmemb, std::string* data) -> size_t {
					size_t new_size = size * nmemb;
					if (data == NULL) {
						return 0;
					}
					data->append(contents, new_size);
					return new_size;
				}));
		curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
		curl_easy_setopt(curl, CURLOPT_WRITEDATA, &buffer);
		curl_easy_setopt(curl, CURLOPT_USERAGENT, "Action Builder");
		curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1);
		curl_easy_setopt(curl, CURLOPT_TIMEOUT, 0);
		curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 9999);

		CURLcode status = curl_easy_perform(curl);

		if (status == CURLE_OK) {
			curl_easy_cleanup(curl);
			return buffer;
		}

		buffer_copy = buffer;
		status_copy = status;

		std::this_thread::sleep_for(std::chrono::milliseconds(200));
	}

	printf("[DEBUG OPEN PAGE] open page failed!!1! %d, %s", status_copy, buffer_copy.c_str());

	//assert(false); // "Failed request after three times."

	curl_easy_cleanup(curl);

	return "";
}

inline bool download_file(std::string url, std::string path) {
	auto buffer = open_page(url);

	if (buffer.size() <= 0)
		return false;

	std::ofstream file(path.c_str(), std::ios::binary);

	if (!file.is_open())
		return false;

	file << buffer;
	file.close();

	return true;
}

inline std::string relpath(std::string path) {
	auto rel = fs::current_path().u8string() + "\\" + path;
	//printf("%s\n", rel.c_str());
	return rel;
}

inline bool file_exists(const std::string& name) {
	std::ifstream f(name.c_str());
	return f.good();
}

inline std::string get_filename(std::string path) {
	return path.substr(path.find_last_of("/\\") + 1);
}

inline std::string remove_extension(std::string filename) {
	return filename.substr(0, filename.find_last_of("."));
}

inline std::vector<std::string> get_matches(std::string pattern, std::string input) {
	const auto r = std::regex(pattern);

	std::vector<std::string> matches;

	std::sregex_iterator iter(input.begin(), input.end(), r);
	std::sregex_iterator end;

	while (iter != end) {
		for (unsigned int i = 0; i < iter->size(); ++i) {
			matches.push_back((*iter)[i]);
		}
		++iter;
	}
	
	return matches;
}

inline std::string url_encode(std::string str) {
	std::string new_str = "";

	char c;
	int ic;
	const char* chars = str.c_str();
	char bufHex[10];
	int len = (int)strlen(chars);

	for (int i = 0; i < len; i++) {
		c = chars[i];
		ic = c;
		// uncomment this if you want to encode spaces with +
		/*if (c==' ') new_str += '+';
		else */if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') new_str += c;
		else {
			sprintf_s(bufHex, "%X", c);
			if (ic < 16)
				new_str += "%0";
			else
				new_str += "%";
			new_str += bufHex;
		}
	}
	return new_str;
}

inline std::string url_decode(std::string str) {
	std::string ret;

	char ch;
	int i, ii, len = (int)str.length();

	for (i = 0; i < len; i++) {
		if (str[i] != '%') {
			if (str[i] == '+')
				ret += ' ';
			else
				ret += str[i];
		}
		else {
			sscanf_s(str.substr(i + 1, 2).c_str(), "%x", &ii);
			ch = static_cast<char>(ii);
			ret += ch;
			i = i + 2;
		}
	}

	return ret;
}

// uses a dot instead of a comma. caused by setlocale .utf8
inline std::string float_to_string(float val) {
	return replace_substr(",", ".", std::to_string(val));
}