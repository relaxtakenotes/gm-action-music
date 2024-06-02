#include <string>
#include <stdio.h>
#include <thread>
#include <mutex>

#include "misc.h"

#define STB_VORBIS_HEADER_ONLY
#include "stb_vorbis.c" 

#define MINIAUDIO_IMPLEMENTATION
#include "miniaudio.h"

#include "playback.h"

namespace playback {
	ma_decoder decoder;
    ma_device device;
    ma_device_config deviceConfig;

    int index = -1;
    bool playing = false;
    bool loaded = false;

    bool waiting_to_play = false;

    float duration = 0;
    float time = 0;
    float g_volume = 0;

    std::mutex mseek;
    std::mutex mload;
    std::mutex mshutdown;

    void data_callback(ma_device* pDevice, void* pOutput, const void* pInput, ma_uint32 frameCount)  {
        ma_decoder* pDecoder = (ma_decoder*)pDevice->pUserData;

        if (pDecoder == NULL)
            return;

        ma_decoder_read_pcm_frames(pDecoder, pOutput, frameCount, NULL);

        time = time + (float)frameCount / (float)decoder.outputSampleRate;

        if (time >= duration) {
            ma_decoder_seek_to_pcm_frame(&decoder, 0);
            time = 0;
        }

        //printf("%d\n", frameCount);

        (void)pInput;
    }

    void _init(std::string path, float volume) {
        std::lock_guard<std::mutex> guard(mload);

        printf("[PLAYBACK: %s] _init started\n", get_filename(path).c_str());

        shutdown();

        printf("[PLAYBACK: %s] shutdown previous instance\n", get_filename(path).c_str());

        if (playing)
            stop();

        playing = false;
        loaded = false;
        duration = 0;
        time = 0;

        ma_result result = ma_decoder_init_file(path.c_str(), NULL, &decoder);
        if (result != MA_SUCCESS) {
            printf("[PLAYBACK: %s] init file fail %d\n", get_filename(path).c_str(), result);
            return;
        }

        printf("[PLAYBACK: %s] init file success\n", get_filename(path).c_str());

        deviceConfig = ma_device_config_init(ma_device_type_playback);
        deviceConfig.playback.format = decoder.outputFormat;
        deviceConfig.playback.channels = decoder.outputChannels;
        deviceConfig.sampleRate = decoder.outputSampleRate;
        deviceConfig.dataCallback = data_callback;
        deviceConfig.pUserData = &decoder;

        if (ma_device_init(NULL, &deviceConfig, &device) != MA_SUCCESS) {
            printf("[PLAYBACK: %s] Failed to open playback device.\n", get_filename(path).c_str());
            ma_decoder_uninit(&decoder);
            return;
        }

        printf("[PLAYBACK: %s] device init success\n", get_filename(path).c_str());

        if (ma_device_start(&device) != MA_SUCCESS) {
            printf("[PLAYBACK: %s] Failed to start playback device.\n", get_filename(path).c_str());
            ma_device_uninit(&device);
            ma_decoder_uninit(&decoder);
            return;
        }

        ma_device_stop(&device);

        printf("[PLAYBACK: %s] device start and stop success\n", get_filename(path).c_str());

        ma_uint64 length;
        ma_decoder_get_length_in_pcm_frames(&decoder, &length);
        duration = (float)length / (float)decoder.outputSampleRate;

        g_volume = volume;
        ma_device_set_master_volume(&device, volume);

        //printf("%0.2f\n", duration);

        printf("[PLAYBACK: %s] get duration and volume set success, we're loaded\n", get_filename(path).c_str());

        loaded = true;
    }

	void init(std::string path, float volume) {
        std::thread(_init, path, volume).detach();
	}

    void shutdown() {
        std::lock_guard<std::mutex> guard(mshutdown);

        playing = false;
        loaded = false;
        duration = 0;
        time = 0;

        if (ma_device_get_state(&device) == ma_device_state_uninitialized)
            return;

        ma_device_uninit(&device);
        ma_decoder_uninit(&decoder);
    }

	void play() {
        if (!loaded || ma_device_get_state(&device) != ma_device_state_stopped) {
            return;
        }

        ma_device_start(&device);
	}

	void stop() {
        if (!loaded || ma_device_get_state(&device) != ma_device_state_started) {
            waiting_to_play = false;
            return;
        }

        ma_device_stop(&device);
	}

    float get_time() {
        ma_uint64 cursor;
        ma_decoder_get_cursor_in_pcm_frames(&decoder, &cursor);
        return (float)cursor / (float)decoder.outputSampleRate;
    }

    float get_visual_time() {
        return time;
    }

    float get_duration() {
        return duration;
    }

    float get_volume() {
        return g_volume;
    }

    void _set_time(float desired_time) {
        if (!loaded) return;

        desired_time = std::max(desired_time, 0.0f);

        std::lock_guard<std::mutex> guard(mseek);

        if (playing)
            stop();

        auto result = ma_decoder_seek_to_pcm_frame(&decoder, (ma_uint64)(desired_time * decoder.outputSampleRate));

        if (playing)
            play();
    }

    void set_time(float desired_time) {
        std::thread(_set_time, desired_time).detach();
        time = desired_time;
    }

    void set_volume(float vol) {
        if (!loaded) return;

        g_volume = vol;
        ma_device_set_master_volume(&device, vol);
    }

    void toggle() {
        if (!loaded) return;

        if (playing) {
            stop();
            playing = false;
        } else {
            play();
            playing = true;
        }
    }
}