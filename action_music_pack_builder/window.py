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
from just_playback import Playback

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
gmpublisher_ready_to_install = False
gmpublisher_installed = ""
ffmpeg_installed = False
ffmpeg_install_status = "      "
ytdlp_installed = False

khinsider_done = False
khinsider_started = False

playback = Playback()
player_volume = 0.75
player_paused = False

backslash = os.sep #"\\" # SyntaxError: f-string expression part cannot include a backslash ?????????????????????????

def update_list(dirs=["input/"]):
    global music_list
    music_list = {}
    for dirr in dirs:
        for file in Path(dirr).rglob('*.*'):
            file = str(file)
            try:
                name, ext = os.path.splitext(file)
                os.rename(file, name.encode("ascii", errors="ignore").decode().replace(".", "") + ext)
                file = name.encode("ascii", errors="ignore").decode().replace(".", "") + ext
            except PermissionError:
                pass

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
        if value["action"] == "unknown":
            continue

        audio = AudioSegment.from_file(key)
        if value["normalize"]:
            audio = effects.normalize(audio)

        if value["start"] > 0 and value["end"] == 0:
            audio = audio[value["start"]*1000:len(audio)]
        if value["start"] == 0 and value["end"] > 0:
            audio = audio[len(audio):value["end"]*1000]
        if value["start"] > 0 and value["end"] > 0:
            audio = audio[value["start"]*1000:value["end"]*1000]

        name, _ = os.path.splitext(value["name"])
        audio.export(f'output/{pack_name}/sound/am_music/{value["action"]}/{name}.ogg', format="ogg")
        progress_f += 1

_show_progress = False

def process_songs(bypass=False):
    global progress_f
    global _show_progress

    progress_f = 0

    if not bypass:
        for key, value in music_list.items():
            if value["action"] == "unknown":
                _show_progress = False
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

def progress_popup():
    imgui.text("This might take a while.")
    len_music_list = 0
    for key, value in music_list.items():
        if value["action"] != "unknown":
            len_music_list += 1
    imgui.text(f"Processed {progress_f} out of {len_music_list}")
    if imgui.button("Exit"):
        if progress_f >= len_music_list:
            imgui.close_current_popup()

def footer():
    global funny
    global last_funny
    global _show_progress

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
        progress_popup()
        imgui.end_popup()
    if imgui.begin_popup_modal("warning-unknown", True, flags=WINDOWFLAGS)[0]:
        if not _show_progress:
            imgui.text("Not all songs are configured. Are you sure you want to ignore them?")
            if imgui.button("no..."):
                imgui.close_current_popup()
            if imgui.button("YES!"):
                #imgui.close_current_popup()
                _show_progress = True
                process_songs(bypass=True)
        else:
            progress_popup()
        imgui.end_popup()

    imgui.end_child()

def main(width):
    global current_song
    global current_dict
    global initialized
    global gmpublisher_installed
    global ffmpeg_installed
    global ffmpeg_install_status
    global ytdlp_installed
    global player_paused
    global player_volume
    global player_pause_timer

    if not initialized:
        result = sp_run("where yt-dlp", stdout=PIPE)
        if "yt-dlp" in result.stdout.decode('utf-8'):
            ytdlp_installed = True

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
        imgui.same_line()
        if imgui.button("battle"):
            current_dict["action"] = "battle"
        imgui.same_line()
        if imgui.button("intensive battle"):
            current_dict["action"] = "battle_intensive"
        imgui.same_line()
        if imgui.button("suspense"):
            current_dict["action"] = "suspense"
        imgui.same_line()
        imgui.text(f"Action Type: {current_dict.get('action')}")

        _, current_dict["normalize"] = imgui.checkbox("Normalize", current_dict["normalize"])
        
        if playback:
            value = playback.curr_pos

            if imgui.button("Mark Start"):
                current_dict["start"] = value
            imgui.same_line()
            if imgui.button("Mark End"):
                current_dict["end"] = value
            imgui.same_line()

            imgui.text(f"Start: {current_dict['start']} | End: {current_dict['end']}")

            if imgui.button("|>"):
                playback.set_volume(player_volume)
                if player_paused:
                    playback.resume()
                else:
                    playback.pause()
                player_paused = not player_paused

            imgui.same_line()

            imgui.push_item_width((width - 76) * 0.9)
            imgui.push_id("seek_slider")
            changed, value = imgui.slider_float(
                "", value,
                min_value=0.0, max_value=playback.duration,
                format="%.2f",
                power=1.0
            )
            imgui.pop_id()
            imgui.pop_item_width()

            if changed:
                playback.seek(value)

            if value >= playback.duration - 0.05:
                playback.seek(0)

            imgui.same_line()
            imgui.push_item_width((width - 9) * 0.1)
            imgui.push_id("volume_slider")
            volume_changed, player_volume = imgui.slider_float(
                "", player_volume,
                min_value=0.0, max_value=1.0,
                format="%.2f",
                power=1.0
            )
            imgui.pop_id()
            imgui.pop_item_width()

            if volume_changed:
                playback.set_volume(player_volume)
        music_list[current_song] = current_dict
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
    global player
    global player_paused

    imgui.begin_child("pack_name", width-16, 35, border=True)

    imgui.push_item_width(width-32)
    imgui.push_id("packname")
    _, pack_name = imgui.input_text('', pack_name, 256)
    imgui.pop_id()
    imgui.pop_item_width()

    imgui.end_child()

    imgui.begin_child("music_list_top", width-16, 35, border=True)


    if imgui.button("reset all"):
        imgui.open_popup("reset-all")
    imgui.same_line()
    if imgui.button("reset current") and current_song and current_dict:
        imgui.open_popup("reset-current")
    imgui.same_line()
    if imgui.button("remove selected") and current_song and current_dict:
        imgui.open_popup("remove-selected")
    imgui.same_line()
    if imgui.button("open output"):
        Popen(f"start \"\" \"{os.path.abspath('output/')}\"", shell=True)
    imgui.same_line()
    if imgui.button("open input"):
        Popen(f"start \"\" \"{os.path.abspath('input/')}\"", shell=True)
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
            playback.load_file(key)
            playback.play()
            playback.pause()
            player_paused = True
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