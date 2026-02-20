import sounddevice as sd
import queue
import json
import numpy as np
import os
import datetime
import time
from vosk import Model, KaldiRecognizer

# ---------------- SETTINGS ----------------
MODEL_PATH = "/home/pi/vosk-model-small-hi-0.22"
PIPER_MODEL = "/home/pi/piper/hi_IN-pratham-medium.onnx"

INPUT_RATE = 48000
LISTENING = True

LAST_COMMAND_TIME = 0
COMMAND_COOLDOWN = 1.5

q = queue.Queue()

# ---------------- SPEAK FUNCTION ----------------
def speak(text):
    global LISTENING, LAST_COMMAND_TIME

    LISTENING = False
    LAST_COMMAND_TIME = time.time()

    cmd = f'echo "{text}" | /home/pi/piper/piper --model {PIPER_MODEL} --output_raw | aplay -f S16_LE -r 22050 -c 1'
    os.system(cmd)

    # Clear microphone buffer
    while not q.empty():
        try:
            q.get_nowait()
        except:
            break

    LISTENING = True


# ---------------- WEATHER ----------------
def weather_report():
    return "आज मौसम साफ है और तापमान लगभग 25 डिग्री है"


# ---------------- SYSTEM STATUS ----------------
def system_status():
    cpu = os.popen("vcgencmd measure_temp").read().strip()
    ram = os.popen("free -h | grep Mem").read().split()[2]
    return f"सिस्टम तापमान {cpu} और उपयोग की गई मेमोरी {ram} है"


# ---------------- VOSK SETUP ----------------
model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(model, 16000)


# ---------------- AUDIO PROCESSING ----------------
def downsample(data):
    data = np.frombuffer(data, dtype=np.int16)
    data = data[::3]   # 48000 → 16000
    return data.tobytes()


def callback(indata, frames, time, status):
    q.put(bytes(indata))


print("Assistant listening...")

# Startup greeting
speak("मैं आपका असिस्टेंट प्रथम हूँ, बोलिए")


# ---------------- MAIN LOOP ----------------
with sd.RawInputStream(
    samplerate=INPUT_RATE,
    blocksize=2000,
    dtype='int16',
    channels=1,
    device=1,
    callback=callback
):

    while True:
        data = q.get()

        if not LISTENING:
            continue

        data = downsample(data)

        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "").strip()
        else:
            continue

        if text == "":
            continue

        # Cooldown protection
        if time.time() - LAST_COMMAND_TIME < COMMAND_COOLDOWN:
            continue

        print("You said:", text)

        # -------- COMMANDS --------

        if any(word in text for word in ["नमस्ते", "नमस्कार", "हेलो"]):
            speak("नमस्ते भाई")
            recognizer.Reset()

        elif "नाम" in text:
            speak("मेरा नाम प्रथम है")
            recognizer.Reset()

        elif any(word in text for word in ["समय", "टाइम"]):
            now = datetime.datetime.now().strftime("%H:%M")
            speak(f"अभी समय है {now}")
            recognizer.Reset()

        elif any(word in text for word in ["दिन", "डे"]):
            day = datetime.datetime.now().strftime("%A")
            speak(f"आज {day} है")
            recognizer.Reset()

        elif any(word in text for word in ["तारीख", "डेट"]):
            date = datetime.datetime.now().strftime("%d %B")
            speak(f"आज की तारीख {date} है")
            recognizer.Reset()

        elif any(word in text for word in ["मौसम", "वेदर"]):
            speak(weather_report())
            recognizer.Reset()

        elif "जोक" in text:
            speak("एक इंजीनियर इतना पढ़ता है कि गूगल भी उससे पूछे, भाई जवाब क्या है")
            recognizer.Reset()

        elif "दूसरा" in text:
            speak("इंजीनियर की नींद और वाईफाई, दोनों कभी पूरी नहीं होती")
            recognizer.Reset()

        elif "शायरी" in text:
            speak("मंजिल मिले या ना मिले ये तो मुकद्दर की बात है, हम कोशिश भी ना करें ये तो गलत बात है")
            recognizer.Reset()

        elif any(word in text for word in ["सिस्टम", "स्टेटस", "स्थिति"]):
            speak(system_status())
            recognizer.Reset()

        elif any(word in text for word in ["बंद", "रुको", "स्टॉप"]):
            speak("ठीक है, बंद हो रहा हूँ")
            recognizer.Reset()
            break
