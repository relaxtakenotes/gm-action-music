import os
import subprocess
import shutil
from pathlib import Path
from threading import Thread
import zipfile
from winreg import ConnectRegistry, OpenKey, HKEY_LOCAL_MACHINE, QueryValue
import re
import json
from time import sleep

import imgui
from sdl2 import *

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from just_playback import Playback
from pydub import AudioSegment
from pydub import effects

from urllib.request import urlopen, urlretrieve
from urllib.parse import urlparse, unquote
import numpy

from traceback import format_exc
from multiprocessing import cpu_count

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
        self.status = "Idle..."

        self.target = 0
        self.progress = 0

        self.progress_matches = 0
        self.target_matches = 0

        self.unsafe = False

    def _download(self, url):
        self.done = False
        self.started = True

        i_base = "http://downloads.khinsider.com/game-soundtracks/album/"
        j_base = "http://downloads.khinsider.com"
        album = url

        try:
            album_page = urlopen(i_base + album).read().decode()

            processed_hrefs = {}
            direct_urls = []

            matches = re.findall(r"<td class=\"clickable-row\" align=\"right\"><a href=\"\/game-soundtracks\/album\/.*\" style=\"font-weight:normal;\">.*<\/a><\/td>", album_page)

            def parse_direct_urls(matches):
                for i_match in matches:
                    indirect_url = re.search(r"\"\/game-soundtracks\/album\/.*\/.*\.mp3\"", i_match)[0]

                    if not indirect_url:
                        self.status = "[Parsing] Couldn't find an indirect url."
                        self.progress_matches += 1
                        continue

                    indirect_url = indirect_url[1:-1]

                    if processed_hrefs.get(indirect_url):
                        self.progress_matches += 1
                        continue

                    processed_hrefs[indirect_url] = True

                    if not self.unsafe:
                        sleep(0.5)

                    try:
                        download_page = urlopen(j_base + indirect_url).read().decode()
                    except Exception:
                        self.status = f"[Parsing] {e}"
                        self.progress_matches += 1
                        continue

                    j_match = re.search(r"<p><a href=\".*\"><span class=\"songDownloadLink\"><i class=\"material-icons\">get_app<\/i>Click here to download as MP3<\/span><\/a>.*<\/p>", download_page)[0]
                    direct_url = re.search(r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()!@:%_\+.~#?&\/\/=]*)", j_match)[0]

                    if not direct_url:
                        self.status = "[Parsing] Couldn't find the direct url."
                        self.progress_matches += 1
                        continue

                    direct_urls.append(direct_url)

                    path = urlparse(direct_url).path
                    filename = unquote(os.path.basename(path))

                    self.status = f"[Parsing] Found: {filename}"
                    self.progress_matches += 1

            pthreads = []

            self.target_matches = len(matches)

            for i in range(0, len(matches), 5):
                pthreads.append(Thread(target=parse_direct_urls, args=(matches[i:i+5],), daemon=True))
            
            for thread in pthreads:
                thread.start()
                if not self.unsafe:
                    sleep(1)
            
            while True:
                if self.progress_matches >= self.target_matches:
                    break

            direct_urls = list(set(direct_urls))

            def download_task(direct_url):
                path = urlparse(direct_url).path
                filename = unquote(os.path.basename(path))

                try:
                    urlretrieve(direct_url, INPUT_DIR + filename)
                    self.status = f"[Downloading] Downloaded: {filename}"
                except Exception as e:
                    self.status = f"[Downloading] {e}: {filename}"
                
                self.progress += 1

                if self.progress >= self.target:
                    self.done = True
                    self.started = False
                    self.progress = 0
                    self.target = 0
            
            dthreads = []

            self.target = len(direct_urls)

            for i in range(0, len(direct_urls)):
                thread = Thread(target=download_task, args=(direct_urls[i],), daemon=True).start()
                if not self.unsafe:
                    sleep(1)

        except Exception as e:
            self.status = f"[Unexpected Error] {e}"
            print(format_exc())

    def download(self, url):
        download_thread = Thread(target=self._download, args=(url,), daemon=True)
        download_thread.start()

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
            urlretrieve("https://github.com/WilliamVenner/gmpublisher/releases/download/2.9.2/gmpublisher_2.9.2_x64.msi", "gmpublisher.msi")
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
            urlretrieve("https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2023-07-04-12-50/ffmpeg-N-111332-g9ff834c2a0-win64-gpl-shared.zip", "ffmpeg.zip")
            with zipfile.ZipFile("ffmpeg.zip", 'r') as zip_ref:
                zip_ref.extractall(".")
            os.remove("ffmpeg.zip")
            os.rename("ffmpeg-N-111332-g9ff834c2a0-win64-gpl-shared/bin/ffmpeg.exe", "ffmpeg.exe")
            os.rename("ffmpeg-N-111332-g9ff834c2a0-win64-gpl-shared/bin/ffplay.exe", "ffplay.exe")
            os.rename("ffmpeg-N-111332-g9ff834c2a0-win64-gpl-shared/bin/ffprobe.exe", "ffprobe.exe")

            os.rename("ffmpeg-N-111332-g9ff834c2a0-win64-gpl-shared/bin/avcodec-60.dll", "avcodec-60.dll")
            os.rename("ffmpeg-N-111332-g9ff834c2a0-win64-gpl-shared/bin/avdevice-60.dll", "avdevice-60.dll")
            os.rename("ffmpeg-N-111332-g9ff834c2a0-win64-gpl-shared/bin/avfilter-9.dll", "avfilter-9.dll")
            os.rename("ffmpeg-N-111332-g9ff834c2a0-win64-gpl-shared/bin/avformat-60.dll", "avformat-60.dll")
            os.rename("ffmpeg-N-111332-g9ff834c2a0-win64-gpl-shared/bin/avutil-58.dll", "avutil-58.dll")
            os.rename("ffmpeg-N-111332-g9ff834c2a0-win64-gpl-shared/bin/postproc-57.dll", "postproc-57.dll")
            os.rename("ffmpeg-N-111332-g9ff834c2a0-win64-gpl-shared/bin/swresample-4.dll", "swresample-4.dll")
            os.rename("ffmpeg-N-111332-g9ff834c2a0-win64-gpl-shared/bin/swscale-7.dll", "swscale-7.dll")
            
            shutil.rmtree("ffmpeg-N-111332-g9ff834c2a0-win64-gpl-shared/")
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
            urlretrieve("https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe", "tools/yt-dlp.exe")
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
        self.cancel = False
        self.threads = 1

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
        
        def edit(items):
            try:
                for key, info in items.items():
                    if self.cancel:
                        return
                    if info["action"] == "unknown":
                        continue
                    name, _ = os.path.splitext(info["name"])

                    audio = AudioSegment.from_file(key)
                    if info["normalize"]:
                        audio = effects.normalize(audio, 2)

                    if info["start"] > 0 and info["end"] == 0:
                        audio = audio[int(info["start"]*1000):len(audio)]
                    if info["start"] == 0 and info["end"] > 0:
                        audio = audio[0:int(info["end"]*1000)]
                    if info["start"] > 0 and info["end"] > 0:
                        audio = audio[int(info["start"]*1000):int(info["end"]*1000)]

                    if info["fade_start"]:
                        audio = audio.fade_in(int(info["fade_start"]*1000))
                    if info["fade_end"]:
                        audio = audio.fade_out(int(info["fade_end"]*1000))
                    
                    audio.export(f'output/{pack_name}/sound/am_music/{info["action"]}/{name}.ogg', format="ogg", codec="libvorbis")

                    self.progress_curr += 1
            except Exception:
                print(format_exc())
        
        ethreads = []
        length = len(self.music_list.songs)
        step = length // self.threads
        for i in range(0, length, step):
            ethreads.append(Thread(target=edit, args=(dict(list(self.music_list.songs.items())[i:i+step]),), daemon=True))
        
        for thread in ethreads:
            thread.start()

    def process(self, pack_name):
        process_thread = Thread(target=self._process, args=(pack_name,), daemon=True)
        process_thread.start()

class music_player():
    def __init__(self, path):
        self.playback = Playback()
        self.ready = False

        self.paused = True
        self.seeking = False
        self.volume = 0.75

        def load(path):
            self.playback.load_file(path)
            self.playback.play()
            self.playback.pause()
            self.ready = True

        load_thread = Thread(target=load, args=(path,), daemon=True)
        load_thread.start()

    def toggle(self):
        if not self.ready:
            return
        self.paused = not self.paused
        if self.paused:
            self.playback.pause()
        else:
            self.playback.resume()

    def seek(self, time, changed, lmb):
        if not self.ready:
            return
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
        if not self.ready:
            return
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

        self.last_key_state = {}
        self.keyboard_state = None
        self.key_pressed_time = {}
        self.switch_delay = 0
        self.in_textbox = False
        self.last_song_index = 0

        self.window_flags = imgui.WINDOW_NO_MOVE + imgui.WINDOW_NO_RESIZE + imgui.WINDOW_NO_SCROLL_WITH_MOUSE + imgui.WINDOW_NO_TITLE_BAR

        self.music_list = music_list()
        self.current_file = ""
        self.need_to_refocus = False
        self.current_settings = {}
        self.pack_name = "Pack Name"
        self.ffmpeg_threads = cpu_count()
        self.khinsider_unsafe = False

        self.music = None

        self.processor = music_processor(self.music_list)

        self.dependency_resolver = dependency_resolver()
        self.dependency_resolver.install_ffmpeg() # audio processing wont work without it. it doesnt install anything if u already have it tho

        self.khinsider = khinsider_downloader()
        self.khinsider_url = "CODE"

        self.ytdlp_url = "URL"

        self.mass_rename_pattern = ""
        self.mass_rename_replace = ""

        self.mass_cfg_start = 0
        self.mass_cfg_start_change = False

        self.mass_cfg_end = 0
        self.mass_cfg_end_change = False
        
        self.mass_cfg_normalize = False
        self.mass_cfg_normalize_change = False

        self.mass_cfg_fade_start = 0
        self.mass_cfg_fade_start_change = False

        self.mass_cfg_fade_end = 0
        self.mass_cfg_fade_end_change = False

        self.restore_last_session()
    
    def mark_text(self):
        self.in_textbox = self.in_textbox or imgui.is_item_active()

    def restore_last_session(self):
        if os.path.isfile("last_session.json"):
            data = {}
            with open("last_session.json", "r") as f:
                data = json.load(f)
                self.pack_name = data.get("pack_name", "Pack Name")
                self.ffmpeg_threads = data.get("ffmpeg_threads", cpu_count())
                self.khinsider_unsafe = data.get("khinsider_unsafe", False)
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
                "ffmpeg_threads": self.ffmpeg_threads,
                "khinsider_unsafe": self.khinsider_unsafe
            }
            json.dump(data, f)

    def push_style(self):
        imgui.push_style_var(imgui.STYLE_WINDOW_ROUNDING, 2.0)
        imgui.push_style_var(imgui.STYLE_CHILD_ROUNDING, 2.0)
        imgui.push_style_var(imgui.STYLE_POPUP_ROUNDING, 2.0)
        imgui.push_style_var(imgui.STYLE_FRAME_ROUNDING, 2.0)
        imgui.push_style_var(imgui.STYLE_SCROLLBAR_ROUNDING, 2.0)
        imgui.push_style_var(imgui.STYLE_GRAB_ROUNDING, 2.0)
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
        imgui.push_style_color(imgui.COLOR_MODAL_WINDOW_DIM_BACKGROUND, 0, 0, 0, 0.35)

    def pop_style(self):
        imgui.pop_style_var(7)
        imgui.pop_style_color(43)

    def draw_list_controls(self):
        imgui.begin_child("music_list_top", self.width-16, 38, border=True)
        if imgui.button("New"):
            imgui.open_popup("reset-all")
        imgui.same_line()
        if imgui.button("Reset selected") and self.current_file and self.current_settings:
            imgui.open_popup("reset-current")
        imgui.same_line()
        if (imgui.button("Remove selected") or (self.pressed_key(SDL_SCANCODE_DELETE)[1] and not self.in_textbox)) and self.current_file and self.current_settings:
            imgui.open_popup("remove-selected")
        imgui.same_line()
        if imgui.button("Output"):
            subprocess.Popen(f"start \"\" \"{os.path.abspath(OUTPUT_DIR)}\"", shell=True)
        imgui.same_line()
        if imgui.button("Input"):
            subprocess.Popen(f"start \"\" \"{os.path.abspath(INPUT_DIR)}\"", shell=True)
        imgui.same_line()
        if imgui.button("Rename All"):
            imgui.open_popup("mass-rename")
        imgui.same_line()
        if imgui.button("Configure All"):
            imgui.open_popup("mass-cfg")
        imgui.same_line()
        if imgui.button("Config"):
            imgui.open_popup("cfg")

        if imgui.begin_popup_modal("mass-rename", True, flags=self.window_flags)[0]:
            imgui.text("This will rename all the files in the directory using a regex pattern you pass.")

            imgui.push_item_width(self.width * 0.5)
            _, self.mass_rename_pattern = imgui.input_text('Pattern', self.mass_rename_pattern, 256)
            self.mark_text()
            _, self.mass_rename_replace = imgui.input_text('What to replace with', self.mass_rename_replace, 256)
            self.mark_text()
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

        if imgui.begin_popup_modal("mass-cfg", True, flags=self.window_flags)[0]:
            imgui.push_item_width(self.width * 0.5)
            imgui.text("You can mass configure certain options in here.")
            imgui.pop_item_width()

            imgui.push_id("mcsc")
            _, self.mass_cfg_start_change = imgui.checkbox("", self.mass_cfg_start_change)
            imgui.same_line()
            _, self.mass_cfg_start = imgui.input_float('Start', self.mass_cfg_start)
            imgui.pop_id()

            imgui.push_id("msec")
            _, self.mass_cfg_end_change = imgui.checkbox("", self.mass_cfg_end_change)
            imgui.same_line()
            _, self.mass_cfg_end = imgui.input_float('End', self.mass_cfg_end)
            imgui.pop_id()

            imgui.push_id("mcns")
            _, self.mass_cfg_normalize_change = imgui.checkbox("", self.mass_cfg_normalize_change)
            imgui.same_line()
            _, self.mass_cfg_normalize = imgui.checkbox("Normalize", self.mass_cfg_normalize)
            imgui.pop_id()

            imgui.push_id("mcfs")
            _, self.mass_cfg_fade_start_change = imgui.checkbox("", self.mass_cfg_fade_start_change)
            imgui.same_line()
            _, self.mass_cfg_fade_start = imgui.input_float('Fade Start', self.mass_cfg_fade_start)
            imgui.pop_id()
            
            imgui.push_id("mcfe")
            _, self.mass_cfg_fade_end_change = imgui.checkbox("", self.mass_cfg_fade_end_change)
            imgui.same_line()
            _, self.mass_cfg_fade_end = imgui.input_float('Fade End', self.mass_cfg_fade_end)
            imgui.pop_id()

            if imgui.button("Quit"):
                imgui.close_current_popup()
            
            imgui.same_line()
            if imgui.button("Execute"):
                self.music = None
                self.current_file = ""
                self.current_settings = {}
                for file, info in self.music_list.songs.items():
                    if self.mass_cfg_start_change:
                        self.music_list.songs[file]["start"] = self.mass_cfg_start
                    if self.mass_cfg_end_change:
                        self.music_list.songs[file]["end"] = self.mass_cfg_end
                    if self.mass_cfg_normalize_change:
                        self.music_list.songs[file]["normalize"] = self.mass_cfg_normalize
                    if self.mass_cfg_fade_start_change:
                        self.music_list.songs[file]["fade_start"] = self.mass_cfg_fade_start
                    if self.mass_cfg_fade_end_change:
                        self.music_list.songs[file]["fade_end"] = self.mass_cfg_fade_end

            imgui.end_popup()

        if imgui.begin_popup_modal("reset-all", True, flags=self.window_flags)[0]:
            imgui.text("This will wipe all the current configuration and you wont be able to return it. Continue?")
            if imgui.button("Yes!"):
                self.music = None
                self.current_settings = {}
                self.current_file = ""
                self.pack_name = "Pack Name"
                self.music_list.update()
                imgui.close_current_popup()
            imgui.same_line()
            if imgui.button("No!"):
                imgui.close_current_popup()
            imgui.end_popup()

        if imgui.begin_popup_modal("reset-current", True, flags=self.window_flags)[0]:
            imgui.text("Are you sure?")
            if imgui.button("Yes!"):
                self.current_settings = {"action": "unknown", "start": 0, "end": 0, "fade_start": 0, "fade_end": 0, "name": self.current_file.split("\\")[-1], "normalize": False}
                self.music_list.songs[self.current_file] = self.current_settings
                imgui.close_current_popup()
            imgui.same_line()
            if imgui.button("No!"):
                imgui.close_current_popup()
            imgui.end_popup()

        if imgui.begin_popup_modal("remove-selected", True, flags=self.window_flags)[0]:
            imgui.text("Are you sure? You won't be able to return this file.")
            if imgui.button("Yes!") or (self.pressed_key(SDL_SCANCODE_RETURN)[1]  and not self.in_textbox):
                self.music = None
                os.remove(self.current_file)
                del self.music_list.songs[self.current_file]
                self.current_file = ""
                self.current_settings = {}
                imgui.close_current_popup()
            imgui.same_line()
            if imgui.button("No!") or (self.pressed_key(SDL_SCANCODE_ESCAPE)[1]  and not self.in_textbox):
                imgui.close_current_popup()
            imgui.end_popup()
        
        if imgui.begin_popup_modal("cfg", True, flags=self.window_flags)[0]:
            imgui.text("Miscellaneous settings that you probably shouldn't change.")
            _, self.khinsider_unsafe = imgui.checkbox("KHInsider unsafe mode", self.khinsider_unsafe)
            _, self.ffmpeg_threads = imgui.input_int("FFMpeg threads", self.ffmpeg_threads)
            if imgui.button("Exit"):
                imgui.close_current_popup()
            imgui.end_popup()

        imgui.end_child()

    def draw_music_list(self):
        imgui.begin_child("music_list", self.width-16, -42, border=True, flags=imgui.WINDOW_HORIZONTAL_SCROLLING_BAR)
        count = 0
        for key, info in self.music_list.songs.items():
            color_button = [0.98, 0.98, 0.98, 0.4]
            color_button_hover = [0.98, 0.98, 0.98, 0.4]
            color_button_active = [0.98, 0.98, 0.98, 0.4]

            if self.current_file == key:
                color_button[3] = 0.4
                color_button_hover[3] = 0.4
                color_button_active[3] = 0.5
                if self.need_to_refocus:
                    imgui.set_scroll_here()
                    self.need_to_refocus = False
            else:
                if count % 2 == 0:
                    color_button[3] = 0.2
                    color_button_hover[3] = 0.3
                    color_button_active[3] = 0.4
                else:
                    color_button[3] = 0.1
                    color_button_hover[3] = 0.2
                    color_button_active[3] = 0.3

            if info["action"] == "unknown":
                color_button[1], color_button[2] = 0.75, 0.75  
                color_button_hover[1], color_button_hover[2] = 0.75, 0.75
                color_button_active[1], color_button_active[2] = 0.75, 0.75
            else:
                color_button[0], color_button[2] = 0.75, 0.75 
                color_button_hover[0], color_button_hover[2] = 0.75, 0.75  
                color_button_active[0], color_button_active[2] = 0.75, 0.75                
            
            imgui.push_style_color(imgui.COLOR_BUTTON, color_button[0], color_button[1], color_button[2], color_button[3])
            imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, color_button_hover[0], color_button_hover[1], color_button_hover[2], color_button_hover[3])
            imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, color_button_active[0], color_button_active[1], color_button_active[2], color_button_active[3])

            imgui.push_style_var(imgui.STYLE_BUTTON_TEXT_ALIGN, (0,0.5))
            if imgui.button(info.get("name"), width=imgui.get_content_region_available_width()):
                self.current_file = key
                self.need_to_refocus = True
                self.current_settings = info
                self.music = music_player(key)

                song_list = list(self.music_list.songs.items())

                for i, items in enumerate(song_list):
                    if self.current_file == items[0]:
                        self.last_song_index = i
                        break
            imgui.pop_style_var(1)

            imgui.pop_style_color(3)
            count += 1

        imgui.end_child()

    def draw_misc_buttons(self):
        imgui.begin_child("misc_buttons", self.width-16, 38, border=True)
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
            self.mark_text()
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
                _text = self.khinsider.status
            imgui.text(_text)

            imgui.push_item_width(self.width * 0.5)
            _, self.khinsider_url = imgui.input_text('', self.khinsider_url, 256)
            self.mark_text()
            imgui.pop_item_width()
            if imgui.button("Quit"):
                imgui.close_current_popup()
            imgui.same_line()
            if imgui.button("Execute"):
                self.khinsider.unsafe = self.khinsider_unsafe
                self.khinsider.download(self.khinsider_url)
            imgui.end_popup()
        imgui.end_child()

    def draw_pack_name(self):
        imgui.begin_child("pack_name", self.width-16, 38, border=True)
        imgui.push_item_width(self.width-32)
        imgui.push_id("packname")
        _, self.pack_name = imgui.input_text('', self.pack_name, 256)
        self.mark_text()
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
            imgui.spacing()
            
            imgui.push_item_width(imgui.get_content_region_available_width())
            imgui.push_id("newname")
            _, self.current_settings["name"] = imgui.input_text('Name', self.current_settings["name"], 256)
            self.mark_text()
            imgui.pop_id()
            imgui.pop_item_width()

            imgui.spacing()

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

            imgui.spacing()

            _, self.current_settings["normalize"] = imgui.checkbox("Normalize", self.current_settings["normalize"])

            time = 0
            duration = 0

            if self.music and self.music.ready:
                time = self.music.playback.curr_pos
                duration = self.music.playback.duration

            imgui.spacing()
            
            if imgui.button("Mark Start"):
                self.current_settings["start"] = time
            
            imgui.same_line()

            if imgui.button("Mark End"):
                self.current_settings["end"] = time
            
            imgui.same_line()

            imgui.text(f"Start: {self.current_settings['start']} | End: {self.current_settings['end']}")
            
            imgui.spacing()

            imgui.push_item_width(50)
            _, self.current_settings["fade_start"] = imgui.input_float('Fade Start', self.current_settings["fade_start"])
            imgui.same_line()
            _, self.current_settings["fade_end"] = imgui.input_float('Fade End', self.current_settings["fade_end"])
            imgui.pop_item_width()

            imgui.spacing()

            if imgui.button("|>"):
                self.music.toggle()

            imgui.same_line()

            imgui.push_item_width((self.width - 76) * 0.9)
            imgui.push_id("seek_slider")
            changed, time = imgui.slider_float(
                "", time,
                min_value=0.0, max_value=duration,
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

            self.music_list.songs[self.current_file] = self.current_settings
        imgui.end_child()

    def draw_footer(self):
        imgui.begin_child("footer", 0, 38, border=True)
        if imgui.button("Apply"):
            self.processor.cancel = False
            self.processor.threads = self.ffmpeg_threads
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
                self.processor.cancel = True
                imgui.close_current_popup()
            imgui.end_popup()
        imgui.end_child()

    def draw_bottom_segment(self):
        imgui.set_next_window_size(self.width, self.height*0.3 + 8)
        imgui.set_next_window_position(0, self.height*0.7 - 8)
        imgui.begin("main_bg", True, flags=self.window_flags)
        self.draw_song_configuration()
        self.draw_footer()
        imgui.end()
    
    def pressed_key(self, code):
        if self.keyboard_state[code] == self.last_key_state.get(code):
            if self.keyboard_state[code]:
                self.key_pressed_time[code] += 0.016
            else:
                self.key_pressed_time[code] = 0
            return [self.key_pressed_time.get(code, 0), False]
        self.last_key_state[code] = self.keyboard_state[code]
        return [self.key_pressed_time.get(code, 0), self.keyboard_state[code]]

    def handle_keybinds(self):
        if self.in_textbox:
            return

        pressed_up_time, pressed_up = self.pressed_key(SDL_SCANCODE_UP)
        pressed_down_time, pressed_down = self.pressed_key(SDL_SCANCODE_DOWN)

        delay = 0.3

        if pressed_up or pressed_up_time - self.switch_delay > delay or pressed_down or pressed_down_time - self.switch_delay > delay:
            song_list = list(self.music_list.songs.items())

            if len(song_list) <= 0:
                return
            
            for i, items in enumerate(song_list):
                if self.current_file == items[0]:
                    self.last_song_index = i
                    self.need_to_refocus = True

                    if pressed_down or (not pressed_down and pressed_down_time > delay):
                        self.current_file, self.current_settings = song_list[min(i+1, len(song_list)-1)]
                    
                    if pressed_up or (not pressed_up and pressed_up_time > delay):
                        self.current_file, self.current_settings = song_list[max(i-1, 0)]

                    self.music = music_player(self.current_file)

                    self.switch_delay += delay
                    break
            else:
                self.last_song_index = max(min(self.last_song_index, len(song_list)), 0)
                self.current_file, self.current_settings = song_list[self.last_song_index]
                self.music = music_player(self.current_file)
        else:
            self.switch_delay = 0
        
        if self.current_file and self.current_settings:
            _, pressed_normalize = self.pressed_key(SDL_SCANCODE_Q)

            _, pressed_background = self.pressed_key(SDL_SCANCODE_1)
            _, pressed_battle = self.pressed_key(SDL_SCANCODE_2)
            _, pressed_battle_intensive = self.pressed_key(SDL_SCANCODE_3)
            _, pressed_suspense = self.pressed_key(SDL_SCANCODE_4)

            _, pressed_toggle = self.pressed_key(SDL_SCANCODE_SPACE)
            pressed_backwards_time, pressed_backwards = self.pressed_key(SDL_SCANCODE_LEFT)
            pressed_forward_time, pressed_forward = self.pressed_key(SDL_SCANCODE_RIGHT)

            _, pressed_mark_start = self.pressed_key(SDL_SCANCODE_A)
            _, pressed_mark_end = self.pressed_key(SDL_SCANCODE_S)

            pressed_fade_start_up_time, pressed_fade_start_up = self.pressed_key(SDL_SCANCODE_X)
            pressed_fade_start_down_time, pressed_fade_start_down = self.pressed_key(SDL_SCANCODE_Z)
            pressed_mark_end_up_time, pressed_mark_end_up = self.pressed_key(SDL_SCANCODE_V)
            pressed_mark_end_down_time, pressed_mark_end_down = self.pressed_key(SDL_SCANCODE_C)

            if pressed_normalize:
                self.current_settings["normalize"] = not self.current_settings["normalize"]
            
            if pressed_background:
                self.current_settings["action"] = "background" 
            if pressed_battle:
                self.current_settings["action"] = "battle" 
            if pressed_battle_intensive:
                self.current_settings["action"] = "battle_intensive" 
            if pressed_suspense:
                self.current_settings["action"] = "suspense"
            
            if pressed_toggle:
                self.music.toggle()
            
            if self.music.ready:
                if pressed_backwards or (pressed_backwards_time > 0.5):
                    self.music.playback.seek(self.music.playback.curr_pos - max((pressed_backwards_time * pressed_backwards_time) / 10, 0.1))
                if pressed_forward or (pressed_forward_time > 0.5):
                    self.music.playback.seek(self.music.playback.curr_pos + max((pressed_forward_time * pressed_forward_time) / 10, 0.1))
                
                if pressed_mark_start:
                    self.current_settings["start"] = self.music.playback.curr_pos
                if pressed_mark_end:
                    self.current_settings["end"] = self.music.playback.curr_pos

                if pressed_fade_start_up or (pressed_fade_start_up_time > 0.5):
                    self.current_settings["fade_start"] += max(pressed_fade_start_up_time ** 1.5 / 10, 0.01)
                if pressed_fade_start_down or (pressed_fade_start_down_time > 0.5):
                    self.current_settings["fade_start"] -= max(pressed_fade_start_down_time ** 1.5 / 10, 0.01)
                if pressed_mark_end_up or (pressed_mark_end_up_time > 0.5):
                    self.current_settings["fade_end"] += max(pressed_mark_end_up_time ** 1.5 / 10, 0.01)
                if pressed_mark_end_down or (pressed_mark_end_down_time > 0.5):
                    self.current_settings["fade_end"] -= max(pressed_mark_end_down_time ** 1.5 / 10, 0.01)

                self.current_settings["fade_start"] = max(self.current_settings["fade_start"], 0)
                self.current_settings["fade_end"] = max(self.current_settings["fade_end"], 0)

    def render(self, width, height, mx, my, buttonstate, keyboard_state):
        self.width = width
        self.height = height
        self.mx = mx
        self.my = my
        self.buttonstate = buttonstate
        self.keyboard_state = keyboard_state
        self.in_textbox = False

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
        
        self.handle_keybinds()

        self.pop_style()

    def stop(self):
        self.save_session()