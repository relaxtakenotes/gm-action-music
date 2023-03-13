import imgui
import os
from subprocess import Popen, CREATE_NEW_CONSOLE, PIPE
from subprocess import run as sp_run
from random import randint
from time import time
from pydub import AudioSegment
from pydub import effects
from threading import Thread
import urllib.request
import khinsider
import zipfile
from winreg import ConnectRegistry, OpenKey, HKEY_LOCAL_MACHINE, QueryValue
from pathlib import Path
from shutil import rmtree

WINDOWFLAGS = imgui.WINDOW_NO_MOVE + imgui.WINDOW_NO_RESIZE + imgui.WINDOW_NO_SCROLL_WITH_MOUSE + imgui.WINDOW_NO_TITLE_BAR

initialized = False

pack_name = "Music pack name"
current_song = ""
current_dict = {}
music_list = {}

ytdlp_url = "Enter URL"
khinsider_url = "Enter Code"

funnies = ["All UI abnormalities are sponsored by tf2modest!", "This wont leak your ip.", "Featuring highly unproductive code.", "Python and imgui together? Urgh.", "Teleporter Aimcone Triangulation Hack (c) forest 2023"]
funny = randint(0, len(funnies)-1)
last_funny = 0

progress_f = 0
mpv_installed = False
gmpublisher_ready_to_install = False
gmpublisher_installed = ""
ffmpeg_installed = False
ffmpeg_install_status = "      "
ytdlp_installed = False

khinsider_done = False
khinsider_started = False

backslash = os.sep#"\\" # SyntaxError: f-string expression part cannot include a backslash ?????????????????????????

def update_list(dirs=["input/"]):
    global music_list
    music_list = {}
    for dirr in dirs:
        for file in Path(dirr).rglob('*.*'):
            file = str(file)
            if not file.endswith(".mp3") and not file.endswith(".wav") and not file.endswith(".mp4a") and not file.endswith(".ogg") and not file.endswith(".flac") and not file.endswith(".webm") and not file.endswith(".wma") and not file.endswith(".aac"):
                continue
            action = "unknown"
            try:
                if file.split("\\")[4] and file.split("\\")[3] == "am_music":
                    action = file.split("\\")[4]
            except IndexError:
                pass
            music_list.update({file: {"action": action, "start": 0, "end": 0, "name": file.split(backslash)[-1], "normalize": False}})

def correct_pos_y(pix):
    cursor_pos = imgui.get_cursor_pos()
    imgui.set_cursor_pos((cursor_pos.x, cursor_pos.y - pix))

def _install_ffmpeg():
    global ffmpeg_installed
    global ffmpeg_install_status
    ffmpeg_install_status = "Installing."
    try:
        urllib.request.urlretrieve("https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip", "ffmpeg.zip")
        with zipfile.ZipFile("ffmpeg.zip", 'r') as zip_ref:
            zip_ref.extractall(".")
        os.remove("ffmpeg.zip")
        os.rename("ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe", "ffmpeg.exe")
        rmtree("ffmpeg-master-latest-win64-gpl/")
    except Exception as e:
        ffmpeg_install_status = e
    ffmpeg_install_status = "Installed."
    ffmpeg_installed = True

def install_ffmpeg():
    process_thread = Thread(target=_install_ffmpeg)
    process_thread.start()    

def _khinsider_download(url):
    global khinsider_done
    global khinsider_started
    khinsider.download(url, "input/", makeDirs=False, verbose=True)
    khinsider_done = True
    khinsider_started = False
    #imgui.open_popup("khinsider-done")

def khinsider_download(url):
    global khinsider_done
    global khinsider_started
    khinsider_started = True
    khinsider_done = False
    process_thread = Thread(target=_khinsider_download, args=(url,))
    process_thread.start()

def _process_songs():
    global progress_f
    for key, value in music_list.items():
        value["name"] = os.path.splitext(value["name"])[0].encode("ascii", errors="ignore")
        value["name"] = value["name"].decode().replace(".", "")
        audio = AudioSegment.from_file(key)
        if value["normalize"]:
            audio = effects.normalize(audio)

        if value["start"] > 0 and value["end"] == 0:
            audio = audio[value["start"]*1000:len(audio)]
        if value["start"] == 0 and value["end"] > 0:
            audio = audio[len(audio):value["end"]*1000]
        if value["start"] > 0 and value["end"] > 0:
            audio = audio[value["start"]*1000:value["end"]*1000]

        audio.export(f'output/{pack_name}/sound/am_music/{value["action"]}/{value["name"]}.ogg', format="ogg")
        progress_f += 1

def process_songs():
    global progress_f

    progress_f = 0

    for key, value in music_list.items():
        if value["action"] == "unknown":
            imgui.open_popup("warning-unknown")
            return
    try:
        os.mkdir(f"output/{pack_name}")
        os.mkdir(f"output/{pack_name}/sound")
        os.mkdir(f"output/{pack_name}/sound/am_music/")
        os.mkdir(f"output/{pack_name}/sound/am_music/background")
        os.mkdir(f"output/{pack_name}/sound/am_music/battle")
        os.mkdir(f"output/{pack_name}/sound/am_music/battle_intensive")
        os.mkdir(f"output/{pack_name}/sound/am_music/suspense")
    except FileExistsError:
        pass

    imgui.open_popup("progress-stuff")

    process_thread = Thread(target=_process_songs)
    process_thread.start()

def footer():
    global funny
    global last_funny

    imgui.begin_child("footer", 0, 0, border=True)
    if time() - last_funny > 10:
        funny += 1
        if funny >= len(funnies):
            funny = 0
        last_funny = time()

    correct_pos_y(-2)

    imgui.text(funnies[funny])
    imgui.same_line(position=imgui.get_window_width() - 51)

    correct_pos_y(2)

    if imgui.button("Apply"):
        process_songs()

    if imgui.begin_popup_modal("progress-stuff", True, flags=WINDOWFLAGS)[0]:
        imgui.text("This might take a while.")
        imgui.text(f"Processed {progress_f} out of {len(music_list)}")
        if imgui.button("Exit"):
            if progress_f >= len(music_list):
                imgui.close_current_popup()
        imgui.end_popup()

    if imgui.begin_popup_modal("warning-unknown", True, flags=WINDOWFLAGS)[0]:
        imgui.text("Not all songs are configured. Go configure them, noob!")
        if imgui.button("that's mean, but ok"):
            imgui.close_current_popup()
        imgui.end_popup()

    imgui.end_child()

def main(width):
    global current_song
    global current_dict
    global initialized
    global mpv_installed
    global gmpublisher_installed
    global ffmpeg_installed
    global ffmpeg_install_status
    global ytdlp_installed

    if not initialized:
        result = sp_run("where yt-dlp", stdout=PIPE)
        if "yt-dlp" in result.stdout.decode('utf-8'):
            ytdlp_installed = True

        result = sp_run("where mpv", stdout=PIPE)
        if "mpv.exe" in result.stdout.decode('utf-8'):
            mpv_installed = True

        result = sp_run("where ffmpeg", stdout=PIPE)
        if "ffmpeg.exe" in result.stdout.decode('utf-8'):
            ffmpeg_installed = True
        if os.path.isfile("ffmpeg.exe"):
            ffmpeg_installed = True

        if not ffmpeg_installed:
            imgui.open_popup("ffmpeg-install")
            install_ffmpeg()

        try:
            reg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
            k = OpenKey(reg, r'SOFTWARE\Classes\gmpublisher.gma.Document\shell\open\command')
            gmpublisher_installed = QueryValue(k, None).replace(" -e \"%1\"", "")
        except Exception as e:
            pass

        update_list()
        initialized = True

    if imgui.begin_popup_modal("ffmpeg-install", True, flags=WINDOWFLAGS)[0]:
        imgui.text(f"Installing FFMPEG (Status):")
        imgui.text(ffmpeg_install_status)
        if imgui.button("Quit"):
            imgui.close_current_popup()
        imgui.end_popup()

    imgui.begin_child("main", 0, -39, border=True)

    if current_song and current_dict:
        imgui.text(f"Current Song: {current_song.split(backslash)[-1]}")
        imgui.spacing()
        imgui.separator()
        imgui.spacing()

        imgui.push_item_width(width - 72)
        imgui.text("Name:")
        imgui.same_line()
        correct_pos_y(2)
        imgui.push_id("newname")
        _, current_dict["name"] = imgui.input_text('', current_dict["name"], 256)
        imgui.pop_id()
        imgui.pop_item_width()
        
        if imgui.button("background"):
            current_dict["action"] = "background"
            music_list[current_song] = current_dict
        imgui.same_line()
        if imgui.button("battle"):
            current_dict["action"] = "battle"
            music_list[current_song] = current_dict
        imgui.same_line()
        if imgui.button("intensive battle"):
            current_dict["action"] = "battle_intensive"
            music_list[current_song] = current_dict
        imgui.same_line()
        if imgui.button("suspense"):
            current_dict["action"] = "suspense"
            music_list[current_song] = current_dict
        imgui.same_line()
        imgui.text(f"Action Type: {current_dict.get('action')}")

        correct_pos_y(-3)
        imgui.push_item_width(100)
        start_m, start_s = divmod(current_dict.get("start"), 60)
        end_m, end_s = divmod(current_dict.get("end"), 60)
        start_str = f'{start_m:02d}:{start_s:02d}'
        end_str =  f'{end_m:02d}:{end_s:02d}'
        imgui.text("Start:")
        imgui.same_line()
        correct_pos_y(3)
        imgui.push_id("startstr")
        _, start_str = imgui.input_text('', start_str, 256)
        imgui.same_line()
        imgui.pop_id()
        imgui.text("End:")
        imgui.same_line()
        imgui.push_id("endstr")
        _, end_str = imgui.input_text('', end_str, 256)
        imgui.pop_id()
        imgui.pop_item_width()
        try:
            new_start = int(start_str.split(":")[0])*60 + min(int(start_str.split(":")[1]), 59)
            new_end = int(end_str.split(":")[0])*60 + min(int(end_str.split(":")[1]), 59)
        
            current_dict["start"] = new_start
            current_dict["end"] = new_end
        except (ValueError, IndexError):
            pass

        _, current_dict["normalize"] = imgui.checkbox("Normalize", current_dict["normalize"])

        if os.path.isdir("tools/mpv/") and os.path.isfile("tools/mpv/mpv.exe"):
            if imgui.button("Open external audio player"):
                Popen('"' + os.path.abspath("tools/mpv/mpv.exe") + '"' + ' "' + os.path.abspath(current_song) + '"')
        elif mpv_installed:
            if imgui.button("Open external audio player"):
                Popen("mpv " + '"' + os.path.abspath(current_song) + '"')
        
    imgui.end_child()

def render_music_list(width):
    global current_song
    global current_dict
    global pack_name
    global ytdlp_url
    global khinsider_url
    global gmpublisher_ready_to_install
    global khinsider_done
    global ytdlp_installed

    imgui.begin_child("pack_name", width-16, 35, border=True)

    imgui.push_item_width(width-32)
    imgui.push_id("packname")
    _, pack_name = imgui.input_text('', pack_name, 256)
    imgui.pop_id()
    imgui.pop_item_width()

    imgui.end_child()

    imgui.begin_child("music_list_top", width-16, 35, border=True)

    imgui.push_item_width((width-16)/3)
    if imgui.button("reset all"):
        imgui.open_popup("reset-all")
    imgui.same_line()
    if imgui.button("reset current") and current_song and current_dict:
        imgui.open_popup("reset-current")
    imgui.same_line()
    if imgui.button("remove selected") and current_song and current_dict:
        imgui.open_popup("remove-selected")
    imgui.pop_item_width()
    imgui.same_line()

    if imgui.begin_popup_modal("reset-all", True, flags=WINDOWFLAGS)[0]:
        imgui.text("Are you sure?")
        if imgui.button("yes!"):
            update_list()
            imgui.close_current_popup()
        imgui.same_line()
        if imgui.button("no!"):
            imgui.close_current_popup()
        imgui.end_popup()

    if imgui.begin_popup_modal("reset-current", True, flags=WINDOWFLAGS)[0]:
        imgui.text("Are you sure?")
        if imgui.button("yes!"):
            current_dict = {"action": "unknown", "start": 0, "end": 0, "name": current_song.split(backslash)[-1], "normalize": False}
            music_list[current_song] = current_dict
            imgui.close_current_popup()
        imgui.same_line()
        if imgui.button("no!"):
            imgui.close_current_popup()
        imgui.end_popup()

    if imgui.begin_popup_modal("remove-selected", True, flags=WINDOWFLAGS)[0]:
        imgui.text("Are you sure?")
        if imgui.button("yes!"):
            del music_list[current_song]
            current_song = ""
            current_dict = ""
            imgui.close_current_popup()
        imgui.same_line()
        if imgui.button("no!"):
            imgui.close_current_popup()
        imgui.end_popup()

    imgui.end_child()

    imgui.begin_child("music_list", width-16, -39, border=True, flags=imgui.WINDOW_HORIZONTAL_SCROLLING_BAR)

    for key, value in music_list.items():
        if value["action"] == "unknown":
            correct_pos_y(-3)
            imgui.text("X")
        else:
            correct_pos_y(-3)
            imgui.text("V")
        imgui.same_line()
        correct_pos_y(3)
        if imgui.button(key.split(backslash)[-1]):
            current_song = key
            current_dict = value

    imgui.end_child()

    imgui.begin_child("misc_buttons", width-16, 0, border=True)

    if imgui.button("yt-dlp"):
        imgui.open_popup("ytdownload")
    imgui.same_line()
    if imgui.button("khinsider"):
        imgui.open_popup("khinsiderdownload")
    imgui.same_line()

    if (not os.path.isdir("tools/mpv/") or not os.path.isfile("tools/mpv/mpv.exe")) and not mpv_installed:
        if imgui.button("install mpv"):
            Popen(os.path.abspath("tools/mpv/updater.bat"), creationflags=CREATE_NEW_CONSOLE)

    if not gmpublisher_installed:
        imgui.same_line()
        if imgui.button("gmpublisher install"):
            urllib.request.urlretrieve("https://github.com/WilliamVenner/gmpublisher/releases/download/2.9.2/gmpublisher_2.9.2_x64.msi", "gmpublisher.msi")
            gmpublisher_ready_to_install = True

        if gmpublisher_ready_to_install and os.path.isfile("gmpublisher.msi"):
            gmpublisher_ready_to_install = False
            Popen("gmpublisher.msi", shell=True)

    if gmpublisher_installed:
        imgui.same_line()
        if imgui.button("gmpublisher"):
            Popen(gmpublisher_installed, shell=True)

    if imgui.begin_popup_modal("ytdownload", True, flags=WINDOWFLAGS)[0]:
        if not ytdlp_installed:
            _text = "yt-dlp is not installed"
            _btn = "Install"
            if os.path.isdir("tools/yt-dlp/") and os.path.isfile("tools/yt-dlp/yt-dlp.exe"):
                _text = "yt-dlp is installed"
                _btn = "Update"

            imgui.text(_text)
            
            if imgui.button(_btn):
                try:
                    os.mkdir("tools/yt-dlp/")
                except FileExistsError:
                    pass
                urllib.request.urlretrieve("https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe", "tools/yt-dlp/yt-dlp.exe")

        imgui.push_item_width(width * 0.3)
        _, ytdlp_url = imgui.input_text('', ytdlp_url, 256)
        imgui.pop_item_width()
        if imgui.button("Quit"):
            imgui.close_current_popup()
        imgui.same_line()
        if imgui.button("Execute"):
            Popen(f"\"{os.path.abspath('tools/yt-dlp/yt-dlp.exe')}\" -o \"{os.path.abspath('input/')}\\%(title)s.%(ext)s\" --extract-audio --audio-format mp3 --audio-quality 0 {ytdlp_url} && pause", creationflags=CREATE_NEW_CONSOLE)
        imgui.end_popup()

    if imgui.begin_popup_modal("khinsiderdownload", True, flags=WINDOWFLAGS)[0]:
        _text = "            "
        if khinsider_done:
            _text = "Download done."
        if khinsider_started:
            _text = khinsider.last_line
        imgui.text(_text)

        imgui.push_item_width(width * 0.3)
        _, khinsider_url = imgui.input_text('', khinsider_url, 256)
        imgui.pop_item_width()
        if imgui.button("Quit"):
            imgui.close_current_popup()
        imgui.same_line()
        if imgui.button("Execute"):
            khinsider_download(khinsider_url)
        imgui.end_popup()

    imgui.end_child()

def render(width, height):
    imgui.push_style_var(imgui.STYLE_WINDOW_ROUNDING, 0.0)
    imgui.push_style_var(imgui.STYLE_CHILD_ROUNDING, 0.0)
    imgui.push_style_var(imgui.STYLE_POPUP_ROUNDING, 0.0)
    imgui.push_style_var(imgui.STYLE_FRAME_ROUNDING, 0.0)
    imgui.push_style_var(imgui.STYLE_SCROLLBAR_ROUNDING, 0.0)
    imgui.push_style_var(imgui.STYLE_GRAB_ROUNDING, 0.0)
    imgui.push_style_var(imgui.STYLE_WINDOW_BORDERSIZE, 0.0)
    
    imgui.set_next_window_size(width, height*0.7)
    imgui.set_next_window_position(0, 0)
    imgui.begin("music_list_bg", True, flags=WINDOWFLAGS)

    render_music_list(width)

    imgui.end()

    imgui.set_next_window_size(width, height*0.3)
    imgui.set_next_window_position(0, height*0.7)
    imgui.begin("main_bg", True, flags=WINDOWFLAGS)

    main(width)
    footer()

    imgui.end()

    imgui.pop_style_var(7)