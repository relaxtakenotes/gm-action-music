#include <stdio.h>
#include <string>
#include <vector>
#include <filesystem>
#include <fstream>
#include <regex>

#include "ui.h"
#include "songs.h"
#include "misc.h"
#include "dependency_resolver.h"
#include "playback.h"
#include "processor.h"
#include "khinsider.h"

#include "imgui/imgui.h"
#include "imgui/imgui_stdlib.h"
#include "imgui/imgui_internal.h"
#include "SDL2/SDL_scancode.h"
#include "json.h"

namespace fs = std::filesystem;
using json = nlohmann::json;

void PushDisabled() {
	ImGuiContext& g = *GImGui;
	if ((g.CurrentItemFlags & ImGuiItemFlags_Disabled) == 0)
		ImGui::PushStyleVar(ImGuiStyleVar_Alpha, g.Style.Alpha * 0.6f);
	ImGui::PushItemFlag(ImGuiItemFlags_Disabled, true);
}

void PopDisabled() {
	ImGuiContext& g = *GImGui;
	ImGui::PopItemFlag();
	if ((g.CurrentItemFlags & ImGuiItemFlags_Disabled) == 0)
		ImGui::PopStyleVar();
}

namespace ui {
	const auto window_flags = ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoTitleBar;

	ImVec2 size;

	std::string pack_name = "generic";

	bool khinsider_unsafe = false;
	int ffmpeg_threads = 2;
	int export_quality = 4;

	int current_song_index;

	float g_volume = 0.5;

	bool is_preview = false;

	bool refocus = false;

	uint8_t* keystate = nullptr;
	bool in_textbox = false;
	std::unordered_map<int, s_key> key_cache;

	void mark_text() {
		in_textbox = in_textbox || ImGui::IsItemActive();
	}

	void style() {
		ImGuiStyle& style = ImGui::GetStyle();

		style.Alpha = 1.0f;
		style.DisabledAlpha = 0.1000000014901161f;
		style.WindowPadding = ImVec2(8.0f, 8.0f);
		style.WindowRounding = 2.0f;
		style.WindowBorderSize = 0.0f;
		style.WindowMinSize = ImVec2(30.0f, 30.0f);
		style.WindowTitleAlign = ImVec2(0.5f, 0.5f);
		style.WindowMenuButtonPosition = ImGuiDir_Left;
		style.ChildRounding = 2.0f;
		style.ChildBorderSize = 1.0f;
		style.PopupRounding = 2.0f;
		style.PopupBorderSize = 1.0f;
		style.FramePadding = ImVec2(4.0f, 3.0f);
		style.FrameRounding = 2.0f;
		style.FrameBorderSize = 0.0f;
		style.ItemSpacing = ImVec2(8.0f, 4.0f);
		style.ItemInnerSpacing = ImVec2(4.0f, 4.0f);
		style.CellPadding = ImVec2(4.0f, 2.0f);
		style.IndentSpacing = 21.0f;
		style.ColumnsMinSpacing = 5.0f;
		style.ScrollbarSize = 14.0f;
		style.ScrollbarRounding = 2.0f;
		style.GrabMinSize = 15.0f;
		style.GrabRounding = 2.0f;
		style.TabRounding = 4.0f;
		style.TabBorderSize = 0.0f;
		style.TabMinWidthForCloseButton = 0.0f;
		style.ColorButtonPosition = ImGuiDir_Right;
		style.ButtonTextAlign = ImVec2(0.5f, 0.5f);
		style.SelectableTextAlign = ImVec2(0.0f, 0.0f);

		style.Colors[ImGuiCol_Text] = ImVec4(1.00f, 1.00f, 1.00f, 1.00f);
		style.Colors[ImGuiCol_TextDisabled] = ImVec4(0.50f, 0.50f, 0.50f, 1.00f);
		style.Colors[ImGuiCol_WindowBg] = ImVec4(0.06f, 0.06f, 0.06f, 0.94f);
		style.Colors[ImGuiCol_ChildBg] = ImVec4(1.00f, 1.00f, 1.00f, 0.00f);
		style.Colors[ImGuiCol_PopupBg] = ImVec4(0.08f, 0.08f, 0.08f, 0.94f);
		style.Colors[ImGuiCol_Border] = ImVec4(0.50f, 0.50f, 0.50f, 0.50f);
		style.Colors[ImGuiCol_BorderShadow] = ImVec4(0.00f, 0.00f, 0.00f, 0.00f);
		style.Colors[ImGuiCol_FrameBg] = ImVec4(0.48f, 0.48f, 0.48f, 0.54f);
		style.Colors[ImGuiCol_FrameBgHovered] = ImVec4(0.98f, 0.98f, 0.98f, 0.40f);
		style.Colors[ImGuiCol_FrameBgActive] = ImVec4(0.98f, 0.98f, 0.98f, 0.67f);
		style.Colors[ImGuiCol_TitleBg] = ImVec4(0.04f, 0.04f, 0.04f, 1.00f);
		style.Colors[ImGuiCol_TitleBgActive] = ImVec4(0.48f, 0.48f, 0.48f, 1.00f);
		style.Colors[ImGuiCol_TitleBgCollapsed] = ImVec4(0.00f, 0.00f, 0.00f, 0.51f);
		style.Colors[ImGuiCol_MenuBarBg] = ImVec4(0.14f, 0.14f, 0.14f, 1.00f);
		style.Colors[ImGuiCol_ScrollbarBg] = ImVec4(0.02f, 0.02f, 0.02f, 0.53f);
		style.Colors[ImGuiCol_ScrollbarGrab] = ImVec4(0.31f, 0.31f, 0.31f, 1.00f);
		style.Colors[ImGuiCol_ScrollbarGrabHovered] = ImVec4(0.41f, 0.41f, 0.41f, 1.00f);
		style.Colors[ImGuiCol_ScrollbarGrabActive] = ImVec4(0.51f, 0.51f, 0.51f, 1.00f);
		style.Colors[ImGuiCol_CheckMark] = ImVec4(0.98f, 0.98f, 0.98f, 1.00f);
		style.Colors[ImGuiCol_SliderGrab] = ImVec4(0.88f, 0.88f, 0.88f, 1.00f);
		style.Colors[ImGuiCol_SliderGrabActive] = ImVec4(0.98f, 0.98f, 0.98f, 1.00f);
		style.Colors[ImGuiCol_Button] = ImVec4(0.98f, 0.98f, 0.98f, 0.25f);
		style.Colors[ImGuiCol_ButtonHovered] = ImVec4(0.98f, 0.98f, 0.98f, 0.35f);
		style.Colors[ImGuiCol_ButtonActive] = ImVec4(0.98f, 0.98f, 0.98f, 0.45f);
		style.Colors[ImGuiCol_Header] = ImVec4(0.98f, 0.98f, 0.98f, 0.31f);
		style.Colors[ImGuiCol_HeaderHovered] = ImVec4(0.98f, 0.98f, 0.98f, 0.80f);
		style.Colors[ImGuiCol_HeaderActive] = ImVec4(0.98f, 0.98f, 0.98f, 1.00f);
		style.Colors[ImGuiCol_Separator] = ImVec4(0.50f, 0.50f, 0.50f, 0.50f);
		style.Colors[ImGuiCol_SeparatorHovered] = ImVec4(0.75f, 0.75f, 0.75f, 0.78f);
		style.Colors[ImGuiCol_SeparatorActive] = ImVec4(0.75f, 0.75f, 0.75f, 1.00f);
		style.Colors[ImGuiCol_ResizeGrip] = ImVec4(0.98f, 0.98f, 0.98f, 0.25f);
		style.Colors[ImGuiCol_ResizeGripHovered] = ImVec4(0.98f, 0.98f, 0.98f, 0.67f);
		style.Colors[ImGuiCol_ResizeGripActive] = ImVec4(0.98f, 0.98f, 0.98f, 0.95f);
		style.Colors[ImGuiCol_Tab] = ImVec4(0.18f, 0.35f, 0.58f, 0.86f);
		style.Colors[ImGuiCol_TabHovered] = ImVec4(0.26f, 0.59f, 0.98f, 0.80f);
		style.Colors[ImGuiCol_TabActive] = ImVec4(0.20f, 0.41f, 0.68f, 1.00f);
		style.Colors[ImGuiCol_TabUnfocused] = ImVec4(0.07f, 0.10f, 0.15f, 0.97f);
		style.Colors[ImGuiCol_TabUnfocusedActive] = ImVec4(0.14f, 0.26f, 0.42f, 1.00f);
		style.Colors[ImGuiCol_PlotLines] = ImVec4(0.61f, 0.61f, 0.61f, 1.00f);
		style.Colors[ImGuiCol_PlotLinesHovered] = ImVec4(1.00f, 1.00f, 1.00f, 1.00f);
		style.Colors[ImGuiCol_PlotHistogram] = ImVec4(0.90f, 0.90f, 0.90f, 1.00f);
		style.Colors[ImGuiCol_PlotHistogramHovered] = ImVec4(1.00f, 1.00f, 1.00f, 1.00f);
		style.Colors[ImGuiCol_TableHeaderBg] = ImVec4(0.19f, 0.19f, 0.20f, 1.00f);
		style.Colors[ImGuiCol_TableBorderStrong] = ImVec4(0.31f, 0.31f, 0.35f, 1.00f);
		style.Colors[ImGuiCol_TableBorderLight] = ImVec4(0.23f, 0.23f, 0.25f, 1.00f);
		style.Colors[ImGuiCol_TableRowBg] = ImVec4(0.00f, 0.00f, 0.00f, 0.00f);
		style.Colors[ImGuiCol_TableRowBgAlt] = ImVec4(1.00f, 1.00f, 1.00f, 0.06f);
		style.Colors[ImGuiCol_TextSelectedBg] = ImVec4(0.98f, 0.98f, 0.98f, 0.35f);
		style.Colors[ImGuiCol_DragDropTarget] = ImVec4(1.00f, 1.00f, 1.00f, 0.90f);
		style.Colors[ImGuiCol_NavHighlight] = ImVec4(0.98f, 0.98f, 0.98f, 1.00f);
		style.Colors[ImGuiCol_NavWindowingHighlight] = ImVec4(1.00f, 1.00f, 1.00f, 0.70f);
		style.Colors[ImGuiCol_NavWindowingDimBg] = ImVec4(0.80f, 0.80f, 0.80f, 0.20f);
		style.Colors[ImGuiCol_ModalWindowDimBg] = ImVec4(0.00f, 0.00f, 0.00f, 0.35f);
	}

	void help_marker(const char* desc) {
		ImGui::TextDisabled("(?)");
		if (ImGui::BeginItemTooltip()) {
			ImGui::PushTextWrapPos(ImGui::GetFontSize() * 35.0f);
			ImGui::TextUnformatted(desc);
			ImGui::PopTextWrapPos();
			ImGui::EndTooltip();
		}
	}

	void draw_pack_text_field() {
		if (ImGui::BeginChild("pack_name", ImVec2(size.x - 16, 38), ImGuiChildFlags_Border)) {
			ImGui::PushItemWidth(size.x - 32);

			ImGui::InputText("##packname", &pack_name);
			mark_text();

			ImGui::PopItemWidth();
		}
		ImGui::EndChild();
	}

	void draw_list_controls() {
		if (ImGui::BeginChild("list_controls", ImVec2(size.x - 16, 38), ImGuiChildFlags_Border)) {
			static const std::vector<std::string> buttons = {
				"New", "reset-all", "0",
				"Reset selected", "reset-current", "0",
				"Remove selected", "remove-selected", "76", // SDL_SCANCODE_DELETE
				"Output", "open-output", "0",
				"Input", "open-input", "0",
				"Rename All", "mass-rename", "0",
				"Configure All", "mass-cfg", "0",
				"Config", "internal-cfg", "0",
				"Dupe", "dupe", "78"
			};
			
			for (size_t i = 0; i < buttons.size(); i = i + 3) {
				if (i != 0) ImGui::SameLine();

				if (ImGui::Button(buttons[i].c_str())) 
					ImGui::OpenPopup(buttons[i + 1].c_str());

				auto code = atoi(buttons[i + 2].c_str());
				if (code != 0 && is_key_pressed(code).pressed)
					ImGui::OpenPopup(buttons[i + 1].c_str());
			}
		}

		if (ImGui::BeginPopupModal("dupe", NULL, window_flags)) {
			auto curr_song = songs::list[current_song_index];

			auto path = curr_song.path;
			auto name = remove_extension(get_filename(path));
			auto target_path = replace_substr(name, name + " - Copy", path);

			if (!file_exists(target_path)) {
				fs::copy_file(path, target_path);

				// if the filewatcher already added it, which is unlikely
				auto fw_idx = songs::find_song_by_attr("path", target_path);
				if (fw_idx > 0)
					songs::remove(fw_idx);

				songs::add(
					get_filename(target_path),
					curr_song.action, 
					target_path,
					curr_song.normalize, 
					curr_song.start, 
					curr_song.end, 
					curr_song.fade_start, 
					curr_song.fade_end, 
					current_song_index + 1
				);
			}
			
			ImGui::CloseCurrentPopup();
			ImGui::EndPopup();
		}

		if (ImGui::BeginPopupModal("open-input", NULL, window_flags)) {
			async_exec("explorer " + qstr(input_path));
			ImGui::CloseCurrentPopup();
			ImGui::EndPopup();
		}

		if (ImGui::BeginPopupModal("open-output", NULL, window_flags)) {
			async_exec("explorer " + qstr(output_path));
			ImGui::CloseCurrentPopup();
			ImGui::EndPopup();
		}

		if (ImGui::BeginPopupModal("reset-all", NULL, window_flags)) {
			ImGui::Text("This will wipe all the current configuration and you wont be able to return it. Continue?");

			if (ImGui::Button("Yes!") || is_key_pressed(SDL_SCANCODE_RETURN).pressed) {
				songs::list.clear();
				songs::save();
				songs::init();
				ImGui::CloseCurrentPopup();
			}

			ImGui::SameLine();

			if (ImGui::Button("No...") || is_key_pressed(SDL_SCANCODE_ESCAPE).pressed)
				ImGui::CloseCurrentPopup();

			ImGui::EndPopup();
		}

		if (ImGui::BeginPopupModal("reset-current", NULL, window_flags)) {
			ImGui::Text("This will erase the configuration of your current song. Continue?");

			if (ImGui::Button("Yes!") || is_key_pressed(SDL_SCANCODE_RETURN).pressed) {
				const int i = current_song_index;

				songs::list[i].action = "unknown";
				songs::list[i].normalize = false;
				songs::list[i].fade_end = 0.0f;
				songs::list[i].fade_start = 0.0f;
				songs::list[i].start = 0.0f;
				songs::list[i].end = 0.0f;

				auto path = songs::list[i].path;
				songs::list[i].name = path.substr(path.find_last_of("/\\") + 1);

				ImGui::CloseCurrentPopup();
			}

			ImGui::SameLine();

			if (ImGui::Button("No...") || is_key_pressed(SDL_SCANCODE_ESCAPE).pressed)
				ImGui::CloseCurrentPopup();
			
			ImGui::EndPopup();
		}

		if (ImGui::BeginPopupModal("remove-selected", NULL, window_flags)) {
			ImGui::Text("Are you sure? You won't be able to return this file.");
			if (ImGui::Button("Yes!") || is_key_pressed(SDL_SCANCODE_RETURN).pressed) {
				const int backup = current_song_index;
				const std::string backup_path = songs::list[backup].path;

				songs::remove(backup);

				auto size = (int)songs::list.size();

				current_song_index = std::clamp(current_song_index, 0, std::max(size - 1, 0));

				if (songs::list.size() > 0) {
					playback::init(songs::list[current_song_index].path, g_volume);
					playback::index = current_song_index;
				} else {
					playback::shutdown();
				}

				std::thread([](const std::string path) {
					while (true) {
						try {
							fs::remove(path);
							break;
						} catch (...) {}
						std::this_thread::sleep_for(std::chrono::milliseconds(200));
					}
				}, backup_path).detach();

				ImGui::CloseCurrentPopup();
			}

			ImGui::SameLine();

			if (ImGui::Button("No...") || is_key_pressed(SDL_SCANCODE_ESCAPE).pressed)
				ImGui::CloseCurrentPopup();
			
			ImGui::EndPopup();
		}

		if (ImGui::BeginPopupModal("mass-rename", NULL, window_flags)) {
			ImGui::Text("This will rename all the files in the directory using a regex pattern you pass.");

			static std::string mass_rename_pattern;
			static std::string mass_rename_replace;

			ImGui::PushItemWidth(size.x * 0.5f);
			ImGui::InputText("Pattern", &mass_rename_pattern);
			mark_text();
			ImGui::InputText("What to replace with", &mass_rename_replace);
			mark_text();
			ImGui::PopItemWidth();

			if (ImGui::Button("Execute")) {

				for (int i = 0; i < (int)songs::list.size(); i++) {
					auto matches = get_matches(mass_rename_pattern, songs::list[i].name);

					if (matches.size() <= 0)
						continue;

					songs::list[i].name = replace_substr(matches[0], mass_rename_replace, songs::list[i].name);
				}
			}

			ImGui::SameLine();

			if (ImGui::Button("Quit"))
				ImGui::CloseCurrentPopup();
			
			ImGui::EndPopup();
		}

		if (ImGui::BeginPopupModal("mass-cfg", NULL, window_flags)) {
			ImGui::PushItemWidth(size.x * 0.5f);
			ImGui::Text("You can mass configure certain options in here.");
			ImGui::PopItemWidth();

			static bool mass_cfg_start_change;
			static float mass_cfg_start;

			static bool mass_cfg_end_change;
			static float mass_cfg_end;

			static bool mass_cfg_normalize_change;
			static bool mass_cfg_normalize;

			static bool mass_cfg_fade_start_change;
			static float mass_cfg_fade_start;

			static bool mass_cfg_fade_end_change;
			static float mass_cfg_fade_end;

			ImGui::Checkbox("##mcsc", &mass_cfg_start_change);
			ImGui::SameLine();
			ImGui::InputFloat("Start", &mass_cfg_start, 0.1f, 0.5f, "%.2f");

			ImGui::Checkbox("##msec", &mass_cfg_end_change);
			ImGui::SameLine();
			ImGui::InputFloat("End", &mass_cfg_end, 0.1f, 0.5f, "%.2f");

			ImGui::Checkbox("##mcns", &mass_cfg_normalize_change);
			ImGui::SameLine();
			ImGui::Checkbox("Normalize", &mass_cfg_normalize);

			ImGui::Checkbox("##mcfs", &mass_cfg_fade_start_change);
			ImGui::SameLine();
			ImGui::InputFloat("Fade Start", &mass_cfg_fade_start, 0.1f, 0.5f, "%.2f");

			ImGui::Checkbox("##mcfe", &mass_cfg_fade_end_change);
			ImGui::SameLine();
			ImGui::InputFloat("Fade End", &mass_cfg_fade_end, 0.1f, 0.5f, "%.2f");

			if (ImGui::Button("Execute")) {
				for (int i = 0; i < (int)songs::list.size(); i++) {
					if (mass_cfg_start_change)
						songs::list[i].start = mass_cfg_start;
					if (mass_cfg_end_change)
						songs::list[i].end = mass_cfg_end;
					if (mass_cfg_normalize_change)
						songs::list[i].normalize = mass_cfg_normalize;
					if (mass_cfg_fade_start_change)
						songs::list[i].fade_start = mass_cfg_fade_start;
					if (mass_cfg_fade_end_change)
						songs::list[i].fade_end = mass_cfg_fade_end;
				}
			}

			ImGui::SameLine();

			if (ImGui::Button("Quit"))
				ImGui::CloseCurrentPopup();
			
			ImGui::EndPopup();
		}

		if (ImGui::BeginPopupModal("internal-cfg", NULL, window_flags)) {
			ImGui::Text("Miscellaneous settings that you probably shouldn't change.");

			ImGui::Checkbox("KHInsider unsafe mode", &khinsider_unsafe);
			ImGui::InputInt("FFMpeg threads", &ffmpeg_threads);
			ImGui::InputInt("Export Quality (Higher is better)", &export_quality);

			if (ImGui::Button("Quit"))
				ImGui::CloseCurrentPopup();
			
			ImGui::EndPopup();
		}

		ImGui::EndChild();
	}

	void draw_music_list() {
		if (ImGui::BeginChild("music_list", ImVec2(size.x - 16, -42), ImGuiChildFlags_Border, ImGuiWindowFlags_HorizontalScrollbar)) {
			for (int i = 0; i < (int)songs::list.size(); i++) {
				std::lock_guard<std::mutex> guard(songs::lock);

				auto color_button = ImVec4(0.98f, 0.98f, 0.98f, 0.25f);
				auto color_button_hover = ImVec4(0.98f, 0.98f, 0.98f, 0.35f);
				auto color_button_active = ImVec4(0.98f, 0.98f, 0.98f, 0.45f);

				if (i == current_song_index) {
					color_button.w = 0.4f;
					color_button_hover.w = 0.4f;
					color_button_active.w = 0.4f;
				} else {
					if (i % 2 == 0) {
						color_button.w = 0.2f;
						color_button_hover.w = 0.3f;
						color_button_active.w = 0.4f;
					} else {
						color_button.w = 0.1f;
						color_button_hover.w = 0.2f;
						color_button_active.w = 0.3f;
					}
				}

				if (songs::list[i].action == "unknown") {
					color_button.y = color_button.z = 0.75f;
					color_button_hover.y = color_button_hover.z = 0.75f;
					color_button_active.y = color_button_active.z = 0.75f;
				} else {
					color_button.x = color_button.z = 0.75f;
					color_button_hover.x = color_button_hover.z = 0.75f;
					color_button_active.x = color_button_active.z = 0.75f;
				}

				ImGui::PushStyleColor(ImGuiCol_Button, color_button);
				ImGui::PushStyleColor(ImGuiCol_ButtonHovered, color_button_hover);
				ImGui::PushStyleColor(ImGuiCol_ButtonActive, color_button_active);
				ImGui::PushStyleVar(ImGuiStyleVar_ButtonTextAlign, ImVec2(0, 0.5f));
				
				if (ImGui::Button(songs::list[i].name.c_str(), ImVec2(ImGui::GetContentRegionAvail().x, ImGui::GetTextLineHeightWithSpacing()))) {
					is_preview = false;
					current_song_index = i;
				}

				if (i == current_song_index && refocus) {
					ImGui::FocusItem();
					refocus = false;
				}
				
				ImGui::PopStyleColor(3);
				ImGui::PopStyleVar(1);
			}
		}
		ImGui::EndChild();
	}

	void draw_misc_buttons() {
		if (ImGui::BeginChild("misc_buttons", ImVec2(size.x - 16, 38), ImGuiChildFlags_Border)) {
			static const std::vector<std::string> buttons = {
				"yt-dlp", "ytdownload",
				"khinsider", "khinsiderdownload",
				"gmpublisher", "gmpublisher-install",
			};

			for (size_t i = 0; i < buttons.size(); i = i + 2) {
				if (i != 0) ImGui::SameLine();

				if (ImGui::Button(buttons[i].c_str())) 
					ImGui::OpenPopup(buttons[i + 1].c_str());
			}

			if (ImGui::BeginPopupModal("gmpublisher-install", NULL, window_flags)) {
				if (dependency_resolver::gmpublisher == "none") {
					ImGui::Text(("Status: " + dependency_resolver::gmpublisher_status).c_str());

					if (ImGui::Button("Install gmpublisher"))
						dependency_resolver::install_gmpublisher();

					ImGui::SameLine();

					if (ImGui::Button("Quit"))
						ImGui::CloseCurrentPopup();
				} else {
					async_exec(qstr(dependency_resolver::gmpublisher));
					ImGui::CloseCurrentPopup();
				}
				ImGui::EndPopup();
			}

			if (ImGui::BeginPopupModal("ytdownload", NULL, window_flags)) {
				static std::string ytdlp_url;
				static std::string output;

				if (ImGui::BeginChild("console_output", ImVec2(size.x / 2, size.y / 2), NULL, window_flags)) {
					ImGui::TextWrapped(output.c_str());
				}
				ImGui::EndChild();

				ImGui::PushItemWidth(size.x * 0.5f);
				ImGui::InputText("##ytdlpurl", &ytdlp_url);
				mark_text();
				ImGui::PopItemWidth();

				if (dependency_resolver::ytdlp == "none") {
					if (ImGui::Button("Install ytdlp")) 
						dependency_resolver::install_ytdlp();

					ImGui::SameLine();

					if (ImGui::Button("Quit")) 
						ImGui::CloseCurrentPopup();
				} else {
					if (ImGui::Button("Execute")) {
						output = "";
						async_exec_output(
							qstr(dependency_resolver::ytdlp) + " -o " + qstr(input_path + "\\%(title)s.mp3") + " --extract-audio --audio-format mp3 --audio-quality 0 " + ytdlp_url + " --ffmpeg-location " + qstr(dependency_resolver::ffmpeg),
							&output
						);
					}

					ImGui::SameLine();

					if (ImGui::Button("Quit")) 
						ImGui::CloseCurrentPopup();
					
				}
				ImGui::EndPopup();
			}

			if (ImGui::BeginPopupModal("khinsiderdownload", NULL, window_flags)) {
				if (!khinsider::working && khinsider::amount_of_songs <= 0)
					ImGui::Text("Status: Idle.");

				if (!khinsider::working && khinsider::amount_of_songs > 0)
					ImGui::Text("Status: Done. Downloaded %d songs! (%d iterations failed)", khinsider::downloaded, khinsider::failed);
				
				if (khinsider::working) {
					if (khinsider::amount_of_songs <= 0)
						ImGui::Text("Status: Started!");
					else
						ImGui::Text("Status: Downloaded %d out of %d", khinsider::downloaded, khinsider::amount_of_songs);
				}

				static std::string khinsider_url;

				ImGui::PushItemWidth(size.x * 0.5f);
				ImGui::InputText("##khinsiderurl", &khinsider_url);
				mark_text();
				ImGui::PopItemWidth();

				if (ImGui::Button("Execute")) {
					khinsider::download(khinsider_url);
				}

				ImGui::SameLine();

				if (ImGui::Button("Quit")) 
					ImGui::CloseCurrentPopup();
				
				ImGui::EndPopup();
			}
		}
		ImGui::EndChild();
	}

	void top_segment() {
		ImGui::SetNextWindowPos(ImVec2(0.0f, 0.0f));
		ImGui::SetNextWindowSize(ImVec2(size.x, size.y * 0.7f));

		if (ImGui::Begin("top_segment", NULL, window_flags)) {
			draw_pack_text_field();
			draw_list_controls();
			draw_music_list();
			draw_misc_buttons();
		}

		ImGui::End();
	}

	void draw_song_configuration() {
		if (ImGui::BeginChild("song_configuration", ImVec2(0, -42), ImGuiChildFlags_Border)) {
			auto lsize = (int)songs::list.size();

			if (lsize <= 0)
				goto end;

			std::lock_guard<std::mutex> guard(songs::lock);

			static bool preview_processing_started = false;
			static bool song_initialized = false;

			current_song_index = std::clamp(current_song_index, 0, std::max((int)lsize - 1, 0));

			ImGui::Spacing();

			ImGui::PushItemWidth(ImGui::GetContentRegionAvail().x);
			ImGui::InputText("Name##songname", &songs::list[current_song_index].name);
			mark_text();
			ImGui::PopItemWidth();

			ImGui::Spacing();

			if (ImGui::Button("Background"))
				songs::list[current_song_index].action = "background";
			ImGui::SameLine();
			if (ImGui::Button("Battle"))
				songs::list[current_song_index].action = "battle";
			ImGui::SameLine();
			if (ImGui::Button("Intensive Battle"))
				songs::list[current_song_index].action = "battle_intensive";
			ImGui::SameLine();
			if (ImGui::Button("Suspense"))
				songs::list[current_song_index].action = "suspense";
			ImGui::SameLine();
			ImGui::Text("Action Type: %s", songs::list[current_song_index].action.c_str());

			ImGui::Spacing();

			if (is_preview)
				PushDisabled();

			ImGui::Checkbox("Normalize", &songs::list[current_song_index].normalize);

			if (is_preview)
				PopDisabled();
			
			ImGui::SameLine();

			ImGui::Checkbox("Preview", &is_preview);

			if (!is_preview) {
				if (song_initialized) {
					playback::init(songs::list[current_song_index].path, g_volume);
				}
				preview_processing_started = false;
				song_initialized = false;
			}

			auto preview_path = processor::get_preview_path(songs::list[current_song_index]);

			if (is_preview && processor::preview_path != preview_path) {
				if (!song_initialized) {
					ImGui::SameLine();
					ImGui::Text("Processing the preview.");
				}

				if (!preview_processing_started) {
					if (file_exists(preview_path)) {
						processor::preview_path = preview_path;
						preview_processing_started = false;
						song_initialized = false;
					} else {
						//printf("[DEBUG] Started processing\n");
						processor::preview(songs::list[current_song_index]);
						preview_processing_started = true;
						song_initialized = false;
					}
				}
			} 
			
			if (is_preview && processor::preview_path == preview_path) {
				ImGui::SameLine();
				ImGui::Text("Preview active!");
				if (!song_initialized) {
					//printf("[DEBUG] Initialized the song!\n");
					playback::init(processor::preview_path, g_volume);
					song_initialized = true;
					preview_processing_started = false;
				}
			}

			ImGui::Spacing();

			s_key k_up = is_key_pressed(SDL_SCANCODE_UP);
			s_key k_down = is_key_pressed(SDL_SCANCODE_DOWN);

			if (k_up.time <= 0 && k_down.time <= 0) {
				if (playback::index != current_song_index) {
					if (!is_preview) {
						playback::init(songs::list[current_song_index].path, g_volume);
					} else {
						song_initialized = false;
						preview_processing_started = false;
					}
				}
				playback::index = current_song_index;
			}

			s_key backwards = is_key_pressed(SDL_SCANCODE_LEFT);
			s_key forward = is_key_pressed(SDL_SCANCODE_RIGHT);
			
			float time = playback::get_visual_time();
			float duration = playback::get_duration();
			float volume = playback::get_volume();

			if (backwards.time > 0)
				time -= 2 * backwards.time;

			if (forward.time > 0)
				time += 2 * forward.time;

			if (is_preview)
				PushDisabled();

			if (ImGui::Button("Mark Start"))
				songs::list[current_song_index].start = time;
			ImGui::SameLine();
			if (ImGui::Button("Mark End"))
				songs::list[current_song_index].end = time;

			if (songs::list[current_song_index].end < songs::list[current_song_index].start) {
				songs::list[current_song_index].end = songs::list[current_song_index].start;
			}

			ImGui::SameLine();

			ImGui::Text("Start: %0.2f | End: %0.2f", songs::list[current_song_index].start, songs::list[current_song_index].end);

			ImGui::Spacing();

			ImGui::PushItemWidth(50.0f);
			ImGui::InputFloat("Fade Start", &songs::list[current_song_index].fade_start);
			ImGui::SameLine();
			ImGui::InputFloat("Fade End", &songs::list[current_song_index].fade_end);

			if (is_preview)
				PopDisabled();

			ImGui::Spacing();

			if (ImGui::Button("|>")) {
				playback::toggle();
			}

			ImGui::SameLine();

			ImGui::PushItemWidth((size.x - 76.0f) * 0.9f);

			static float new_time = 0;

			time = std::max(time, 0.0f);

			if (ImGui::SliderFloat("##timebar", &time, 0.0f, duration, "%.2f")) 
				new_time = time;

			if (backwards.released || forward.released)
				new_time = time;

			if (ImGui::IsItemDeactivatedAfterEdit() || backwards.released || forward.released) {
				playback::set_time(new_time);
				new_time = 0;
			}
			
			ImGui::PopItemWidth();

			ImGui::SameLine();

			ImGui::PushItemWidth((size.x - 9.0f) * 0.1f);

			static float new_volume = 0;

			if (ImGui::SliderFloat("##volume", &volume, 0.0f, 1.0f, "%.2f")) 
				new_volume = volume;

			if (ImGui::IsItemDeactivatedAfterEdit()) {
				g_volume = new_volume;
				playback::set_volume(new_volume);
				new_volume = 0;
			}

			ImGui::PopItemWidth();
		}
	end:
		ImGui::EndChild();
	}

	void draw_footer() {
		if (ImGui::BeginChild("footer", ImVec2(0, 38), ImGuiChildFlags_Border)) {
			if (processor::target == 0 && ImGui::Button("Start")) {
				processor::quality = export_quality;
				processor::pack_name = pack_name;
				processor::threads = ffmpeg_threads;
				processor::process_all();
			}

			if (processor::target != 0) {
				if (processor::target == processor::processed) {
					if (ImGui::Button("Finish"))
						processor::target = 0;
					ImGui::SameLine();
				}

				ImGui::Text("Processed %d out of %d", processor::processed, processor::target);
			}

			if (dependency_resolver::ffmpeg == "none") {
				ImGui::SameLine();
				ImGui::Text(dependency_resolver::ffmpeg_status.c_str());
			}
		}
		ImGui::EndChild();
	}

	s_key is_key_pressed(int key) {
		static std::unordered_map<int, float> keytime;

		if (key_cache.find(key) != key_cache.end()) {
			return key_cache[key];
		}

		s_key output{};

		if (keystate[key] > 0 && keytime[key] <= 0)
			output.pressed = true;

		if (keystate[key] <= 0 && keytime[key] > 0)
			output.released = true;
		
		if (keystate[key] > 0)
			keytime[key] += 0.016f;

		output.time = keytime[key];

		if (keystate[key] <= 0)
			keytime[key] = 0;

		key_cache[key] = output;

		return output;
	}

	void handle_hotkeys() {
		if (keystate == nullptr || in_textbox)
			return;

		auto lsize = songs::list.size();

		if (lsize <= 0)
			return;

		s_key up = is_key_pressed(SDL_SCANCODE_UP);
		s_key down = is_key_pressed(SDL_SCANCODE_DOWN);

		if (up.pressed) {
			refocus = true;
			is_preview = false;
			current_song_index--;
		}

		if (down.pressed) {
			refocus = true;
			is_preview = false;
			current_song_index++;
		}

		current_song_index = std::clamp(current_song_index, 0, std::max((int)lsize - 1, 0));

		s_key normalize = is_key_pressed(SDL_SCANCODE_Q);
		s_key preview = is_key_pressed(SDL_SCANCODE_W);

		s_key a_background = is_key_pressed(SDL_SCANCODE_1);
		s_key a_battle = is_key_pressed(SDL_SCANCODE_2);
		s_key a_battle_intensive = is_key_pressed(SDL_SCANCODE_3);
		s_key a_suspense = is_key_pressed(SDL_SCANCODE_4);

		s_key toggle = is_key_pressed(SDL_SCANCODE_SPACE);
		s_key backwards = is_key_pressed(SDL_SCANCODE_LEFT);
		s_key forward = is_key_pressed(SDL_SCANCODE_RIGHT);

		s_key mark_start = is_key_pressed(SDL_SCANCODE_A);
		s_key mark_end = is_key_pressed(SDL_SCANCODE_S);

		s_key mark_fade_start_plus = is_key_pressed(SDL_SCANCODE_X);
		s_key mark_fade_start_minus = is_key_pressed(SDL_SCANCODE_Z);

		s_key mark_fade_end_plus = is_key_pressed(SDL_SCANCODE_V);
		s_key mark_fade_end_minus = is_key_pressed(SDL_SCANCODE_C);

		std::lock_guard<std::mutex> guard(songs::lock);

		if (toggle.pressed)
			playback::toggle();

		if (a_background.pressed)
			songs::list[current_song_index].action = "background";
		if (a_battle.pressed)
			songs::list[current_song_index].action = "battle";
		if (a_battle_intensive.pressed)
			songs::list[current_song_index].action = "battle_intensive";
		if (a_suspense.pressed)
			songs::list[current_song_index].action = "suspense";

		if (preview.pressed)
			is_preview = !is_preview;

		if (is_preview)
			return;

		if (normalize.pressed)
			songs::list[current_song_index].normalize = !songs::list[current_song_index].normalize;

		if (mark_start.pressed)
			songs::list[current_song_index].start = playback::get_visual_time();
		if (mark_end.pressed)
			songs::list[current_song_index].end = playback::get_visual_time();

		if (mark_fade_start_plus.time > 0)
			songs::list[current_song_index].fade_start += std::max(mark_fade_start_plus.time * mark_fade_start_plus.time / 20, 0.01f);
		if (mark_fade_start_minus.time > 0)
			songs::list[current_song_index].fade_start -= std::max(mark_fade_start_plus.time * mark_fade_start_plus.time / 20, 0.01f);

		if (mark_fade_end_plus.time > 0)
			songs::list[current_song_index].fade_end += std::max(mark_fade_end_plus.time * mark_fade_end_plus.time / 20, 0.01f);
		if (mark_fade_end_minus.time > 0)
			songs::list[current_song_index].fade_end -= std::max(mark_fade_end_minus.time * mark_fade_end_minus.time / 20, 0.01f);

		songs::list[current_song_index].fade_start = std::max(songs::list[current_song_index].fade_start, 0.0f);
		songs::list[current_song_index].fade_end = std::max(songs::list[current_song_index].fade_end, 0.0f);
	}

	void bottom_segment() {
		ImGui::SetNextWindowPos(ImVec2(0.0f, size.y * 0.7f - 8.0f));
		ImGui::SetNextWindowSize(ImVec2(size.x, size.y * 0.3f + 8.0f));

		if (ImGui::Begin("bottom_segment", NULL, window_flags)) {
			draw_song_configuration();
			draw_footer();
		}

		ImGui::End();
	}

	void save_config() {
		json data = {
			{"pack_name", pack_name},
			{"khinsider_unsafe", khinsider_unsafe},
			{"ffmpeg_threads", ffmpeg_threads},
			{"current_song_index", current_song_index},
			{"export_quality", export_quality},
			{"volume", g_volume}
		};

		std::ofstream file(relpath("data\\config.json"));

		if (!file.is_open())
			return;

		file << data.dump(4);

		file.close();
	}

	void load_config() {
		std::ifstream file(relpath("data\\config.json"));

		if (!file.is_open())
			return;

		std::string content{ std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>() };

		file.close();

		auto data = json::parse(content);
		
		pack_name = data["pack_name"];
		khinsider_unsafe = data["khinsider_unsafe"];
		ffmpeg_threads = data["ffmpeg_threads"];
		current_song_index = data["current_song_index"];
		export_quality = data["export_quality"];
		g_volume = data["volume"];
	}

	void init() {
		dependency_resolver::gmpublisher = dependency_resolver::get_gmpublisher_path();
		if (dependency_resolver::gmpublisher != "none") {
			dependency_resolver::gmpublisher_status = "gmpublisher found.";
		} else {
			dependency_resolver::gmpublisher_status = "gmpublisher not found.";
		}

		dependency_resolver::ytdlp = dependency_resolver::get_ytdlp_path();
		if (dependency_resolver::ytdlp != "none") {
			dependency_resolver::ytdlp_status = "yt-dlp found.";
		}

		dependency_resolver::install_ffmpeg();

		load_config();

		songs::init();
	}

	void shutdown() {
		save_config();

		songs::save();

		for (const auto& entry : fs::directory_iterator(relpath("data\\"))) {
			auto filename = entry.path().filename().u8string();
			if (filename._Starts_with("preview_") && filename.find_last_of(".ogg"))
				fs::remove(entry.path());
		}
	}

	void render() {
		in_textbox = false;
		key_cache.clear();

        const ImGuiViewport* viewport = ImGui::GetMainViewport();

        ImGui::SetNextWindowPos(viewport->Pos);
        ImGui::SetNextWindowSize(viewport->Size);

		size = viewport->Size;

        if (ImGui::Begin("fullscreen_window", NULL, ImGuiWindowFlags_NoDecoration | ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoSavedSettings)) {
			top_segment();
			bottom_segment();
        }

        ImGui::End();

		handle_hotkeys();
        
        //ImGui::ShowDemoWindow(NULL);
	}
}