import imgui
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
from pathlib import Path
import json
from just_playback import Playback
from threading import Thread
from pydub import AudioSegment
from pydub import effects
import urllib.request
import zipfile
import shutil
import khinsider
import re
from winreg import ConnectRegistry, OpenKey, HKEY_LOCAL_MACHINE, QueryValue
from time import sleep
import numpy

INPUT_DIR = r"input/"
OUTPUT_DIR = r"output/"
TOOLS_DIR = r"tools/"

if not os.path.isdir(INPUT_DIR):
    os.mkdir(INPUT_DIR)
if not os.path.isdir(OUTPUT_DIR):
    os.mkdir(OUTPUT_DIR)
if not os.path.isdir(TOOLS_DIR):
    os.mkdir(TOOLS_DIR)

class khinsider_downloader():
    def __init__(self):
        self.done = False
        self.started = False

    def _download(self, url):
        self.done = False
        self.started = True
        khinsider.download(url, INPUT_DIR, makeDirs=False, verbose=True)
        self.done = True
        self.started = False

    def download(self, url):
        process_thread = Thread(target=self._download, args=(url,), daemon=True)
        process_thread.start()

class dependency_resolver():
    def __init__(self):
        self.ffmpeg = False
        self.ffmpeg_path = ""
        self.ytdlp = False
        self.gmpublisher = False
        self.gmpublisher_path = ""
        self.gmpublisher_status = " "*13

        self.ffmpeg_status = " "*10
        self.ytdlp_status = " "*10

        if "yt-dlp" in subprocess.run("where yt-dlp", stdout=subprocess.PIPE).stdout.decode('utf-8'):
            self.ytdlp = True
        if os.path.isfile("tools/yt-dlp.exe"):
            self.ytdlp = True

        if "ffmpeg" in subprocess.run("where ffmpeg", stdout=subprocess.PIPE).stdout.decode('utf-8'):
            self.ffmpeg = True
            self.ffmpeg_path = subprocess.run("where ffmpeg", stdout=subprocess.PIPE).stdout.decode('utf-8').split("\n")[0].strip()
        if os.path.isfile("ffmpeg.exe"):
            self.ffmpeg = True
            self.ffmpeg_path = os.path.abspath("ffmpeg.exe")

        self._check_gmpublisher()

    def _check_gmpublisher(self):
        try:
            reg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
            k = OpenKey(reg, r'SOFTWARE\Classes\gmpublisher.gma.Document\shell\open\command')
            self.gmpublisher_path = QueryValue(k, None).replace(" -e \"%1\"", "")
            self.gmpublisher = True
        except Exception as e:
            pass        

    def _gmpublisher(self):
        if self.gmpublisher:
            return
        self.gmpublisher_status = "Downloading installer..."
        try:
            urllib.request.urlretrieve("https://github.com/WilliamVenner/gmpublisher/releases/download/2.9.2/gmpublisher_2.9.2_x64.msi", "gmpublisher.msi")
            self.gmpublisher_status = "Running installer..."
            subprocess.run("gmpublisher.msi", shell=True)
            self._check_gmpublisher()
            os.remove("gmpublisher.msi")
        except Exception as e:
            self.gmpublisher_status = str(e)

        if self.gmpublisher:
            self.gmpublisher_status = "Installed!"
        else:
            self.gmpublisher_status = "Install cancelled or failed?"

    def install_gmpublisher(self):
        process_thread = Thread(target=self._gmpublisher, daemon=True)
        process_thread.start()

    def _ffmpeg(self):
        if self.ffmpeg:
            return
        self.ffmpeg_status = "Installing."
        try:
            urllib.request.urlretrieve("https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip", "ffmpeg.zip")
            with zipfile.ZipFile("ffmpeg.zip", 'r') as zip_ref:
                zip_ref.extractall(".")
            os.remove("ffmpeg.zip")
            os.rename("ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe", "ffmpeg.exe")
            shutil.rmtree("ffmpeg-master-latest-win64-gpl/")
        except Exception as e:
            self.ffmpeg_status = e
            return
        self.ffmpeg_status = "Installed."
        self.ffmpeg = True

    def install_ffmpeg(self):
        process_thread = Thread(target=self._ffmpeg, daemon=True)
        process_thread.start()

    def _ytdlp(self):
        if self.ytdlp:
            return
        self.ytdlp_status = "Installing."
        try:
            urllib.request.urlretrieve("https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe", "tools/yt-dlp.exe")
        except Exception as e:
            self.ytdlp_status = e
            return
        self.ytdlp_status = "Installed."
        self.ytdlp = True

    def install_ytdlp(self):
        process_thread = Thread(target=self._ytdlp, daemon=True)
        process_thread.start()

class music_processor():
    def __init__(self, music_list):
        self.music_list = music_list
        self.progress_curr = 0
        self.progress_max = 0

    def _process(self, pack_name):
        self.progress_max = 0
        for key, info in self.music_list.songs.items():
            if info["action"] == "unknown":
                continue
            self.progress_max += 1
        self.progress_curr = 0
        try:
            os.mkdir(f"{OUTPUT_DIR}/{pack_name}")
            os.mkdir(f"{OUTPUT_DIR}/{pack_name}/sound")
            os.mkdir(f"{OUTPUT_DIR}/{pack_name}/sound/am_music/")
            os.mkdir(f"{OUTPUT_DIR}/{pack_name}/sound/am_music/background")
            os.mkdir(f"{OUTPUT_DIR}/{pack_name}/sound/am_music/battle")
            os.mkdir(f"{OUTPUT_DIR}/{pack_name}/sound/am_music/battle_intensive")
            os.mkdir(f"{OUTPUT_DIR}/{pack_name}/sound/am_music/suspense")
        except FileExistsError:
            pass
        for key, info in self.music_list.songs.items():
            if info["action"] == "unknown":
                continue

            audio = AudioSegment.from_file(key)
            if info["normalize"]:
                audio = effects.normalize(audio)

            if info["start"] > 0 and info["end"] == 0:
                audio = audio[int(info["start"]*1000):len(audio)]
            if info["start"] == 0 and info["end"] > 0:
                audio = audio[len(audio):int(info["end"]*1000)]
            if info["start"] > 0 and info["end"] > 0:
                audio = audio[int(info["start"]*1000):int(info["end"]*1000)]

            if info["fade_start"]:
                audio = audio.fade_in(int(info["fade_start"]*1000))
            if info["fade_end"]:
                audio = audio.fade_out(int(info["fade_end"]*1000))

            name, _ = os.path.splitext(info["name"])
            audio.export(f'output/{pack_name}/sound/am_music/{info["action"]}/{name}.ogg', format="ogg")

            self.progress_curr += 1

    def process(self, pack_name):
        process_thread = Thread(target=self._process, args=(pack_name,), daemon=True)
        process_thread.start()


class music_player():
    def __init__(self, path):
        self.playback = Playback()
        self.playback.load_file(path)
        self.playback.play()
        self.playback.pause()
        self.paused = True
        self.seeking = False
        self.volume = 0.75

    def toggle(self):
        self.paused = not self.paused
        if self.paused:
            self.playback.pause()
        else:
            self.playback.resume()

    def seek(self, time, changed, lmb):
        if changed and lmb:
            self.seeking = True

        if self.seeking:
            self.playback.pause()
            self.playback.seek(time)        

        if self.seeking and not lmb:
            self.seeking = False
            if not self.paused:
                self.playback.resume()

    def think(self):
        self.playback.set_volume(self.volume)
        if self.playback.curr_pos >= self.playback.duration - 0.05:
            self.playback.seek(0)
            self.playback.pause()
            self.paused = True

class input_watcher(FileSystemEventHandler):
    def set_music_list(self, music_list):
        self.music_list = music_list

    def on_created(self, event):
        self.music_list.add(event.src_path)

    def on_deleted(self, event):
        self.music_list.remove(event.src_path)

class music_list():
    def __init__(self):
        self.songs = {}

        observer = Observer()
        event_handler = input_watcher()
        event_handler.set_music_list(self)
        observer.schedule(event_handler, path=INPUT_DIR)
        observer.start()

        self.update()

    def remove(self, file):
        file = os.path.abspath(file)
        if self.songs.get(file):
            del self.songs[file]

    def add(self, file):
        file = str(os.path.abspath(file))
        name, extension = os.path.splitext(file)

        if extension not in [".mp3", ".wav", ".mp4a", ".ogg", ".flac"]:
            return

        name = name.split("\\")
        name[-1] = name[-1].encode("ascii", errors="ignore").decode().replace(".", "")
        name = "\\".join(name) + extension
        
        while True:
            try:
                os.rename(file, name)
                break
            except PermissionError:
                pass
        file = name

        action = "unknown"
        
        try:
            if file.split("\\")[4] and file.split("\\")[3] == "am_music":
                action = file.split("\\")[4]
        except IndexError:
            pass

        self.songs.update({
            file: {"action": action,
                   "start": 0,
                   "end": 0,
                   "normalize": False,
                   "name": file.split("\\")[-1],
                   "fade_start": 0,
                   "fade_end": 0
                  }
            })

    def mass_rename(self, pattern, replace_to):
        for file, info in self.songs.items():
            try:
                self.songs[file]["name"] = re.sub(pattern, replace_to, self.songs[file]["name"])
            except Exception:
                print(f"failed to rename {file}, {info}")
                continue

    def update(self):
        self.songs = {}
        for file in Path(INPUT_DIR).rglob('*.*'):
            self.add(file)

class gui():
    def __init__(self):
        self.width = 0
        self.height = 0
        self.mx = 0
        self.my = 0
        self.buttonstate = None
        self.window_flags = imgui.WINDOW_NO_MOVE + imgui.WINDOW_NO_RESIZE + imgui.WINDOW_NO_SCROLL_WITH_MOUSE + imgui.WINDOW_NO_TITLE_BAR

        self.music_list = music_list()
        self.current_file = ""
        self.current_settings = {}
        self.pack_name = "Pack Name"

        self.music = None

        self.processor = music_processor(self.music_list)

        self.dependency_resolver = dependency_resolver()
        self.dependency_resolver.install_ffmpeg() # audio processing wont work without it. it doesnt install anything if u already have it tho

        self.khinsider = khinsider_downloader()
        self.khinsider_url = "CODE"

        self.ytdlp_url = "URL"

        self.mass_rename_pattern = ""
        self.mass_rename_replace = ""

        self.restore_last_session()

    def restore_last_session(self):
        if os.path.isfile("last_session.json"):
            data = {}
            with open("last_session.json", "r") as f:
                data = json.load(f)
                self.pack_name = data["pack_name"]
                for key, info in self.music_list.songs.items():
                    if data.get("music_list").get(key):
                        self.music_list.songs[key] = data.get("music_list").get(key)
                    if data.get("current_file") == key:
                        self.current_file = key
                        self.current_settings = data.get("current_settings")
                        self.music = music_player(key)

    def save_session(self):
        with open("last_session.json", "w+") as f:
            data = {
                "music_list": self.music_list.songs,
                "current_file": self.current_file,
                "current_settings": self.current_settings,
                "pack_name": self.pack_name,
            }
            json.dump(data, f)

    def push_style(self):
        imgui.push_style_var(imgui.STYLE_WINDOW_ROUNDING, 0.0)
        imgui.push_style_var(imgui.STYLE_CHILD_ROUNDING, 0.0)
        imgui.push_style_var(imgui.STYLE_POPUP_ROUNDING, 0.0)
        imgui.push_style_var(imgui.STYLE_FRAME_ROUNDING, 0.0)
        imgui.push_style_var(imgui.STYLE_SCROLLBAR_ROUNDING, 0.0)
        imgui.push_style_var(imgui.STYLE_GRAB_ROUNDING, 0.0)
        imgui.push_style_var(imgui.STYLE_WINDOW_BORDERSIZE, 0.0)

        imgui.push_style_color(imgui.COLOR_TEXT, 1.00, 1.00, 1.00, 1.00)
        imgui.push_style_color(imgui.COLOR_TEXT_DISABLED, 0.50, 0.50, 0.50, 1.00)
        imgui.push_style_color(imgui.COLOR_WINDOW_BACKGROUND, 0.06, 0.06, 0.06, 0.94)
        imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, 1.00, 1.00, 1.00, 0.00)
        imgui.push_style_color(imgui.COLOR_POPUP_BACKGROUND, 0.08, 0.08, 0.08, 0.94)
        imgui.push_style_color(imgui.COLOR_BORDER, 0.50, 0.50, 0.50, 0.50)
        imgui.push_style_color(imgui.COLOR_BORDER_SHADOW, 0.00, 0.00, 0.00, 0.00)
        imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND, 0.48, 0.48, 0.48, 0.54)
        imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND_HOVERED, 0.98, 0.98, 0.98, 0.40)
        imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND_ACTIVE, 0.98, 0.98, 0.98, 0.67)
        imgui.push_style_color(imgui.COLOR_TITLE_BACKGROUND, 0.04, 0.04, 0.04, 1.00)
        imgui.push_style_color(imgui.COLOR_TITLE_BACKGROUND_ACTIVE, 0.48, 0.48, 0.48, 1.00)
        imgui.push_style_color(imgui.COLOR_TITLE_BACKGROUND_COLLAPSED, 0.00, 0.00, 0.00, 0.51)
        imgui.push_style_color(imgui.COLOR_MENUBAR_BACKGROUND, 0.14, 0.14, 0.14, 1.00)
        imgui.push_style_color(imgui.COLOR_SCROLLBAR_BACKGROUND, 0.02, 0.02, 0.02, 0.53)
        imgui.push_style_color(imgui.COLOR_SCROLLBAR_GRAB, 0.31, 0.31, 0.31, 1.00)
        imgui.push_style_color(imgui.COLOR_SCROLLBAR_GRAB_HOVERED, 0.41, 0.41, 0.41, 1.00)
        imgui.push_style_color(imgui.COLOR_SCROLLBAR_GRAB_ACTIVE, 0.51, 0.51, 0.51, 1.00)
        imgui.push_style_color(imgui.COLOR_CHECK_MARK, 0.98, 0.98, 0.98, 1.00)
        imgui.push_style_color(imgui.COLOR_SLIDER_GRAB, 0.88, 0.88, 0.88, 1.00)
        imgui.push_style_color(imgui.COLOR_SLIDER_GRAB_ACTIVE, 0.98, 0.98, 0.98, 1.00)
        imgui.push_style_color(imgui.COLOR_BUTTON, 0.98, 0.98, 0.98, 0.25)
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 0.98, 0.98, 0.98, 0.35)
        imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, 0.98, 0.98, 0.98, 0.45)
        imgui.push_style_color(imgui.COLOR_HEADER, 0.98, 0.98, 0.98, 0.31)
        imgui.push_style_color(imgui.COLOR_HEADER_HOVERED, 0.98, 0.98, 0.98, 0.80)
        imgui.push_style_color(imgui.COLOR_HEADER_ACTIVE, 0.98, 0.98, 0.98, 1.00)
        imgui.push_style_color(imgui.COLOR_SEPARATOR, 0.50, 0.50, 0.50, 0.50)
        imgui.push_style_color(imgui.COLOR_SEPARATOR_HOVERED, 0.75, 0.75, 0.75, 0.78)
        imgui.push_style_color(imgui.COLOR_SEPARATOR_ACTIVE, 0.75, 0.75, 0.75, 1.00)
        imgui.push_style_color(imgui.COLOR_RESIZE_GRIP, 0.98, 0.98, 0.98, 0.25)
        imgui.push_style_color(imgui.COLOR_RESIZE_GRIP_HOVERED, 0.98, 0.98, 0.98, 0.67)
        imgui.push_style_color(imgui.COLOR_RESIZE_GRIP_ACTIVE, 0.98, 0.98, 0.98, 0.95)
        imgui.push_style_color(imgui.COLOR_PLOT_LINES, 0.61, 0.61, 0.61, 1.00)
        imgui.push_style_color(imgui.COLOR_PLOT_LINES_HOVERED, 1.00, 1.00, 1.00, 1.00)
        imgui.push_style_color(imgui.COLOR_PLOT_HISTOGRAM, 0.90, 0.90, 0.90, 1.00)
        imgui.push_style_color(imgui.COLOR_PLOT_HISTOGRAM_HOVERED, 1.00, 1.00, 1.00, 1.00)
        imgui.push_style_color(imgui.COLOR_TEXT_SELECTED_BACKGROUND, 0.98, 0.98, 0.98, 0.35)
        imgui.push_style_color(imgui.COLOR_DRAG_DROP_TARGET, 1.00, 1.00, 1.00, 0.90)
        imgui.push_style_color(imgui.COLOR_NAV_HIGHLIGHT, 0.98, 0.98, 0.98, 1.00)
        imgui.push_style_color(imgui.COLOR_NAV_WINDOWING_HIGHLIGHT, 1.00, 1.00, 1.00, 0.70)
        imgui.push_style_color(imgui.COLOR_NAV_WINDOWING_DIM_BACKGROUND, 0.80, 0.80, 0.80, 0.20)
        imgui.push_style_color(imgui.COLOR_MODAL_WINDOW_DIM_BACKGROUND, 0.80, 0.80, 0.80, 0.35)

    def pop_style(self):
        imgui.pop_style_var(7)
        imgui.pop_style_color(43)

    def draw_list_controls(self):
        imgui.begin_child("music_list_top", self.width-16, 35, border=True)
        if imgui.button("new"):
            imgui.open_popup("reset-all")
        imgui.same_line()
        if imgui.button("default selected") and self.current_file and self.current_settings:
            imgui.open_popup("reset-current")
        imgui.same_line()
        if imgui.button("remove selected") and self.current_file and self.current_settings:
            imgui.open_popup("remove-selected")
        imgui.same_line()
        if imgui.button("open output"):
            subprocess.Popen(f"start \"\" \"{os.path.abspath(OUTPUT_DIR)}\"", shell=True)
        imgui.same_line()
        if imgui.button("open input"):
            subprocess.Popen(f"start \"\" \"{os.path.abspath(INPUT_DIR)}\"", shell=True)
        imgui.same_line()
        if imgui.button("mass rename"):
            imgui.open_popup("mass-rename")

        if imgui.begin_popup_modal("mass-rename", True, flags=self.window_flags)[0]:
            imgui.text("This will rename all the files in the directory using a regex pattern you pass.")

            imgui.push_item_width(self.width * 0.5)
            _, self.mass_rename_pattern = imgui.input_text('Pattern', self.mass_rename_pattern, 256)
            _, self.mass_rename_replace = imgui.input_text('What to replace with', self.mass_rename_replace, 256)
            imgui.pop_item_width()
            if imgui.button("Quit"):
                imgui.close_current_popup()
            imgui.same_line()
            if imgui.button("Execute"):
                self.music = None
                self.current_file = ""
                self.current_settings = {}
                sleep(0.1)
                self.music_list.mass_rename(self.mass_rename_pattern, self.mass_rename_replace)
                
            imgui.end_popup()

        if imgui.begin_popup_modal("reset-all", True, flags=self.window_flags)[0]:
            imgui.text("This will wipe all the current configuration and you wont be able to return it. Continue?")
            if imgui.button("yes!"):
                self.music = None
                self.current_settings = {}
                self.current_file = ""
                self.pack_name = "Pack Name"
                self.music_list.update()
                imgui.close_current_popup()
            imgui.same_line()
            if imgui.button("no!"):
                imgui.close_current_popup()
            imgui.end_popup()

        if imgui.begin_popup_modal("reset-current", True, flags=self.window_flags)[0]:
            imgui.text("Are you sure?")
            if imgui.button("yes!"):
                self.current_settings = {"action": "unknown", "start": 0, "end": 0, "name": self.current_file.split("\\")[-1], "normalize": False}
                self.music_list.songs[self.current_file] = self.current_settings
                imgui.close_current_popup()
            imgui.same_line()
            if imgui.button("no!"):
                imgui.close_current_popup()
            imgui.end_popup()

        if imgui.begin_popup_modal("remove-selected", True, flags=self.window_flags)[0]:
            imgui.text("Are you sure? You won't be able to return this file.")
            if imgui.button("yes!"):
                self.music = None
                os.remove(self.current_file)
                del self.music_list.songs[self.current_file]
                self.current_file = ""
                self.current_settings = {}
                imgui.close_current_popup()
            imgui.same_line()
            if imgui.button("no!"):
                imgui.close_current_popup()
            imgui.end_popup()

        imgui.end_child()

    def draw_music_list(self):
        imgui.begin_child("music_list", self.width-16, -39, border=True, flags=imgui.WINDOW_HORIZONTAL_SCROLLING_BAR)
        for key, info in self.music_list.songs.items():
            _text = info.get("name")
            if self.current_file == key:
                _text = f"[[{_text}]]"

            if imgui.button(_text):
                self.current_file = key
                self.current_settings = info
                self.music = music_player(key)

            imgui.same_line()
            if info["action"] != "unknown":
                imgui.text("+")
            else:
                imgui.text("-")

        imgui.end_child()

    def draw_misc_buttons(self):
        imgui.begin_child("misc_buttons", self.width-16, 0, border=True)
        if imgui.button("yt-dlp"):
            imgui.open_popup("ytdownload")
        imgui.same_line()
        if imgui.button("khinsider"):
            imgui.open_popup("khinsiderdownload")
        imgui.same_line()
        if imgui.button("gmpublisher"):
            if self.dependency_resolver.gmpublisher:
                subprocess.Popen(self.dependency_resolver.gmpublisher_path)
            else:
                imgui.open_popup("gmpublisher-install")

        if imgui.begin_popup_modal("gmpublisher-install", True, flags=self.window_flags)[0]:
            imgui.text("gmpublisher is not installed.")
            imgui.text(self.dependency_resolver.gmpublisher_status)
            if imgui.button("Install"):
                self.dependency_resolver.install_gmpublisher()
            imgui.same_line()
            if imgui.button("Quit"):
                imgui.close_current_popup()
            imgui.end_popup()

        if imgui.begin_popup_modal("ytdownload", True, flags=self.window_flags)[0]:
            if not self.dependency_resolver.ytdlp:
                imgui.text("yt-dlp is not installed")
                
                if imgui.button("Install"):
                    self.dependency_resolver.install_ytdlp()

            imgui.push_item_width(self.width * 0.3)
            _, self.ytdlp_url = imgui.input_text('', self.ytdlp_url, 256)
            imgui.pop_item_width()
            if imgui.button("Quit"):
                imgui.close_current_popup()
            imgui.same_line()
            if imgui.button("Execute"):
                subprocess.Popen(f"\"{os.path.abspath('tools/yt-dlp.exe')}\" -o \"{os.path.abspath('input/')}\\%(title)s.%(ext)s\" --extract-audio --audio-format mp3 --audio-quality 0 {self.ytdlp_url} --ffmpeg-location \"{self.dependency_resolver.ffmpeg_path}\" && pause", creationflags=subprocess.CREATE_NEW_CONSOLE)
            imgui.end_popup()

        if imgui.begin_popup_modal("khinsiderdownload", True, flags=self.window_flags)[0]:
            _text = " "*10
            if self.khinsider.done:
                _text = "Download done."
            if self.khinsider.started:
                _text = khinsider.last_line
            imgui.text(_text)

            imgui.push_item_width(self.width * 0.5)
            _, self.khinsider_url = imgui.input_text('', self.khinsider_url, 256)
            imgui.pop_item_width()
            if imgui.button("Quit"):
                imgui.close_current_popup()
            imgui.same_line()
            if imgui.button("Execute"):
                self.khinsider.download(self.khinsider_url)
            imgui.end_popup()
        imgui.end_child()

    def draw_pack_name(self):
        imgui.begin_child("pack_name", self.width-16, 35, border=True)
        imgui.push_item_width(self.width-32)
        imgui.push_id("packname")
        _, self.pack_name = imgui.input_text('', self.pack_name, 256)
        imgui.pop_id()
        imgui.pop_item_width()
        imgui.end_child()

    def draw_top_segment(self):
        imgui.set_next_window_size(self.width, self.height*0.7)
        imgui.set_next_window_position(0, 0)
        imgui.begin("top_segment", True, flags=self.window_flags)
        self.draw_pack_name()
        self.draw_list_controls()
        self.draw_music_list()
        self.draw_misc_buttons()
        imgui.end()

    def draw_song_configuration(self):
        imgui.begin_child("main", 0, -42, border=True)
        if self.current_file and self.current_settings:
            imgui.text(f"Current Song: {self.current_settings['name']}")
            imgui.spacing()
            imgui.separator()
            imgui.spacing()

            imgui.push_item_width(self.width - 72)
            imgui.push_id("newname")
            _, self.current_settings["name"] = imgui.input_text('Name', self.current_settings["name"], 256)
            imgui.pop_id()
            imgui.pop_item_width()

            if imgui.button("Background"):
                self.current_settings["action"] = "background"
            imgui.same_line()
            if imgui.button("Battle"):
                self.current_settings["action"] = "battle"
            imgui.same_line()
            if imgui.button("Intensive battle"):
                self.current_settings["action"] = "battle_intensive"
            imgui.same_line()
            if imgui.button("Suspense"):
                self.current_settings["action"] = "suspense"
            imgui.same_line()
            imgui.text(f"Action Type: {self.current_settings.get('action')}")

            _, self.current_settings["normalize"] = imgui.checkbox("Normalize", self.current_settings["normalize"])

            if self.music:
                time = self.music.playback.curr_pos

                if imgui.button("Mark Start"):
                    self.current_settings["start"] = time
                imgui.same_line()
                if imgui.button("Mark End"):
                    self.current_settings["end"] = time
                imgui.same_line()

                imgui.text(f"Start: {self.current_settings['start']} | End: {self.current_settings['end']}")

                imgui.push_item_width(50)
                _, self.current_settings["fade_start"] = imgui.input_float('Fade Start', self.current_settings["fade_start"])
                imgui.same_line()
                _, self.current_settings["fade_end"] = imgui.input_float('Fade End', self.current_settings["fade_end"])
                imgui.pop_item_width()

                if imgui.button("|>"):
                    self.music.toggle()

                imgui.same_line()

                imgui.push_item_width((self.width - 76) * 0.9)
                imgui.push_id("seek_slider")
                changed, time = imgui.slider_float(
                    "", time,
                    min_value=0.0, max_value=self.music.playback.duration,
                    format="%.2f",
                    power=1.0
                )
                imgui.pop_id()
                imgui.pop_item_width()

                self.music.seek(time, changed, self.buttonstate.left)

                imgui.same_line()
                imgui.push_item_width((self.width - 9) * 0.1)
                imgui.push_id("volume_slider")
                _, self.music.volume = imgui.slider_float(
                    "", self.music.volume,
                    min_value=0.0, max_value=1.0,
                    format="%.2f",
                    power=1.0
                )
                imgui.pop_id()
                imgui.pop_item_width()

                self.music.think()

            self.music_list.songs[self.current_file] = self.current_settings
        imgui.end_child()

    def draw_footer(self):
        imgui.begin_child("footer", 0, 37, border=True)
        if imgui.button("Apply"):
            self.processor.process(self.pack_name)
            imgui.open_popup("processor-progress")
        if imgui.begin_popup_modal("processor-progress", True, flags=self.window_flags)[0]:
            processing_done = (self.processor.progress_curr >= self.processor.progress_max)
            _text = "Working..."
            if processing_done:
                _text = "Done!"
            imgui.text(_text)
            imgui.text(f"Processed {self.processor.progress_curr} out of {self.processor.progress_max}      ")
            if imgui.button("Exit"):
                if processing_done:
                    imgui.close_current_popup()
            imgui.end_popup()
        imgui.end_child()

    def draw_bottom_segment(self):
        imgui.set_next_window_size(self.width, self.height*0.3)
        imgui.set_next_window_position(0, self.height*0.7)
        imgui.begin("main_bg", True, flags=self.window_flags)
        self.draw_song_configuration()
        self.draw_footer()
        imgui.end()

    def render(self, width, height, mx, my, buttonstate):
        self.width = width
        self.height = height
        self.mx = mx
        self.my = my
        self.buttonstate = buttonstate

        self.push_style()
        
        if self.dependency_resolver.ffmpeg:
            self.draw_top_segment()
            self.draw_bottom_segment()
        else:
            imgui.set_next_window_size(self.width / 2, self.height / 2)
            imgui.set_next_window_position(self.width / 4, self.height / 4)
            imgui.begin("main_bg", True, flags=self.window_flags)
            imgui.text("Please wait until ffmpeg is installed. ")
            imgui.text("Normal UI will be drawn once it's done.")
            imgui.end()            
        
        self.pop_style()

    def stop(self):
        self.save_session()