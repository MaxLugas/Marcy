import datetime
import json
import os
import queue
import random
import struct
import subprocess
import sys
from num2words import num2words
import time
from ctypes import POINTER, cast
import openai
from openai import error
import pvporcupine
import simpleaudio as sa
import vosk
import yaml
from comtypes import CLSCTX_ALL
from fuzzywuzzy import fuzz
from pvrecorder import PvRecorder
from pycaw.pycaw import (
    AudioUtilities,
    IAudioEndpointVolume
)
from rich import print
import config
import tts

# some consts
CDIR = os.getcwd()
VA_CMD_LIST = yaml.safe_load(
    open('commands.yaml', 'rt', encoding='utf8'),
)

# ChatGPT vars
system_message = {"role": "system", "content": "Ты голосовой ассистент"}
message_log = [system_message]

# init openai
openai.api_key = config.OPENAI_TOKEN

# PORCUPINE
porcupine = pvporcupine.create(
    access_key=config.PICOVOICE_TOKEN,
    keyword_paths=['marcy_en_windows_v2_2_0.ppn'],
    sensitivities=[1]
)

# VOSK
model = vosk.Model("model_small")
samplerate = 16000
device = config.MICROPHONE_INDEX
kaldi_rec = vosk.KaldiRecognizer(model, samplerate)
q = queue.Queue()


def gpt_answer():
    global message_log

    model_engine = "gpt-3.5-turbo"
    max_tokens = 256  # default 1024
    try:
        response = openai.ChatCompletion.create(
            model=model_engine,
            messages=message_log,
            max_tokens=max_tokens,
            temperature=0.7,
            top_p=1,
            stop=None
        )
    except (error.TryAgain, error.ServiceUnavailableError):
        return "ChatGPT перегружен!"
    except openai.OpenAIError as ex:
        # если ошибка - это макс длина контекста, то возвращаем ответ с очищенным контекстом
        if ex.code == "context_length_exceeded":
            message_log = [system_message, message_log[-1]]
            return gpt_answer()
        else:
            return "OpenAI токен не рабочий."

    # Find the first response from the chatbot that has text in it (some responses may not have text)
    for choice in response.choices:
        if "text" in choice:
            return choice.text

    # If no response with text is found, return the first response's content (which may be empty)
    return response.choices[0].message.content


def play(phrase, wait_done=True):
    global recorder
    filename = f"{CDIR}\\sound\\"

    if phrase == "greet":  # for py 3.8
        filename += f"greet{random.choice([1, 2, 3])}.wav"
    elif phrase == "ok":
        filename += f"ok{random.choice([1, 2, 3])}.wav"
    elif phrase == "not_found":
        filename += "not_found.wav"
    elif phrase == "thanks":
        filename += "thanks.wav"
    elif phrase == "run":
        filename += "run.wav"
    elif phrase == "stupid":
        filename += "stupid.wav"
    elif phrase == "ready":
        filename += "ready.wav"
    elif phrase == "off":
        filename += "off.wav"

    if wait_done:
        recorder.stop()

    wave_obj = sa.WaveObject.from_wave_file(filename)
    play_obj = wave_obj.play()

    if wait_done:
        play_obj.wait_done()
        recorder.start()


def q_callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))


def va_respond(voice: str):
    global recorder, message_log, first_request
    print(f"Распознано: {voice}")

    cmd = recognize_cmd(filter_cmd(voice))

    print(cmd)

    if len(cmd['cmd'].strip()) <= 0:
        return False
    elif cmd['percent'] < 70 or cmd['cmd'] not in VA_CMD_LIST.keys():
        if fuzz.ratio(voice.join(voice.split()[:1]).strip(), "скажи") > 75:

            message_log.append({"role": "user", "content": voice})
            response = gpt_answer()
            message_log.append({"role": "assistant", "content": response})

            recorder.stop()
            tts.va_speak(response)
            time.sleep(0.5)
            recorder.start()
            return False
        else:
            play("not_found")
            time.sleep(1)

        return False
    else:
        execute_cmd(cmd['cmd'], voice)
        return True


def filter_cmd(raw_voice: str):
    cmd = raw_voice

    for x in config.VA_ALIAS:
        cmd = cmd.replace(x, "").strip()

    for x in config.VA_TBR:
        cmd = cmd.replace(x, "").strip()

    return cmd


def recognize_cmd(cmd: str):
    rc = {'cmd': '', 'percent': 0}
    for c, v in VA_CMD_LIST.items():
        for x in v:
            vrt = fuzz.ratio(cmd, x)
            if vrt > rc['percent']:
                rc['cmd'] = c
                rc['percent'] = vrt
    return rc


def execute_cmd(cmd: str, voice: str):
    # звук
    if cmd == 'sound_off':
        play("ok", True)

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMute(1, None)

    elif cmd == 'sound_on':
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMute(0, None)

        play("ok")

    # системные
    elif cmd == 'time':
        now = datetime.datetime.now()
        text = "Сейч+ас " + num2words(now.hour, lang='ru') + " " + num2words(now.minute, lang='ru')
        tts.va_speak(text)

    elif cmd == 'explorer':
        subprocess.Popen('explorer')

    elif cmd == 'restart':
        os.system("shutdown -f -r -t 0")

    elif cmd == 'shutdown':
        os.system("shutdown -f -s -t 0")

    elif cmd == 'off':
        play("off", True)
        porcupine.delete()
        exit(0)

    # приложения
    elif cmd == 'browser':
        os.startfile(f"{CDIR}/applications/Google Chrome.lnk")

    elif cmd == 'telegram':
        os.startfile(f"{CDIR}/applications/Telegram.lnk")

    elif cmd == 'steam':
        os.startfile(f"{CDIR}/applications/Steam.lnk")

    elif cmd == 'discord':
        os.startfile(f"{CDIR}/applications/Discord.lnk")

    elif cmd == 'thanks':
        play("thanks")

    elif cmd == 'stupid':
        play("stupid")


# `-1` is the default input audio device.
recorder = PvRecorder(device_index=config.MICROPHONE_INDEX, frame_length=porcupine.frame_length)
recorder.start()
print('Using device: %s' % recorder.selected_device)

print(f"Marcy (v1.0) начала свою работу ...")
play("run")
time.sleep(0.5)

ltc = time.time() - 1000

while True:
    try:
        pcm = recorder.read()
        keyword_index = porcupine.process(pcm)

        if keyword_index >= 0:
            recorder.stop()
            play("greet", True)
            print("Yes, sir.")
            recorder.start()  # prevent self-recording
            ltc = time.time()

        while time.time() - ltc <= 10:
            pcm = recorder.read()
            sp = struct.pack("h" * len(pcm), *pcm)

            if kaldi_rec.AcceptWaveform(sp):
                if va_respond(json.loads(kaldi_rec.Result())["text"]):
                    ltc = time.time()

                break

    except Exception as err:
        print(f"Unexpected {err=}, {type(err)=}")
        raise
