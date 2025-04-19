
import os
import time
import json
import numpy as np
import sounddevice as sd
import soundfile as sf
import subprocess
import webrtcvad
from groq import Groq
from load_env import groq_API


# Query and print all available audio devices.
print(sd.query_devices())


# -------------------------------
# Configuration for Recording and VAD
# -------------------------------
SAMPLE_RATE = 16000       # Sampling rate in Hz (16 kHz works well with webrtcvad)
FRAME_DURATION_MS = 30    # Duration of each frame in milliseconds
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)  # Number of samples per frame
VAD_MODE = 2              # VAD mode (0-3): 0 is most aggressive about filtering out non-speech, 3 is least aggressive.
MAX_SILENCE_FRAMES = 10   # Number of consecutive silent frames to trigger stop recording

# Create a VAD instance with the desired sensitivity level
vad = webrtcvad.Vad(VAD_MODE)

# A list to hold recorded audio blocks (each block corresponds to a frame with speech)
recorded_frames = []

# A counter for consecutive frames that contain silence
silence_counter = 0

def audio_callback(indata, frames, time_info, status):
    """
    Callback function called for each audio block captured by sounddevice.
    It converts the incoming float32 data to int16 (required for webrtcvad) and determines
    if the block contains speech. If speech is detected, it resets the silence counter.
    Otherwise, it increments the counter and stops the stream if silence persists.
    """
    global silence_counter, recorded_frames

    # Ensure the input is mono. If indata has more channels, pick the first one.
    mono_data = indata[:, 0]

    # Convert float data (-1.0 to 1.0) to 16-bit PCM
    int16_data = (mono_data * 32767).astype(np.int16)

    # webrtcvad requires raw bytes of little-endian 16-bit PCM audio
    is_speech = vad.is_speech(int16_data.tobytes(), SAMPLE_RATE)

    if is_speech:
        recorded_frames.append(int16_data.copy())
        silence_counter = 0  # reset silence counter when speech is detected
    else:
        # Append even silence frames if you want a continuous audio stream.
        recorded_frames.append(int16_data.copy())
        silence_counter += 1
        # If enough consecutive silent frames are detected, stop the stream
        if silence_counter > MAX_SILENCE_FRAMES:
            raise sd.CallbackStop

# -------------------------------
# Step 1: Record audio until silence is detected
# -------------------------------
print("Recording... Speak now. The recording will automatically stop after prolonged silence.")

try:
    # Use sounddevice InputStream with the defined callback
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,           # mono recording
        blocksize=FRAME_SIZE, # process in chunks of FRAME_SIZE samples (~30ms)
        callback=audio_callback
    ):
        # Keep the stream active until CallbackStop is raised (when silence is detected)
        while True:
            time.sleep(0.1)
except sd.CallbackStop:
    print("Silence detected. Stopping recording...")

# Combine all recorded frames into one continuous numpy array
recorded_audio = np.concatenate(recorded_frames)

# Save the recorded audio as a WAV file
wav_filename = "Recording.wav"
sf.write(wav_filename, recorded_audio, SAMPLE_RATE)
print(f"Audio has been saved to {wav_filename}")

# -------------------------------
# Step 2: Convert WAV to M4A using ffmpeg
# -------------------------------
m4a_filename = "Recording.m4a"
conversion_command = ['ffmpeg', '-y', '-i', wav_filename, m4a_filename]
subprocess.run(conversion_command, check=True)
print(f"Converted {wav_filename} to {m4a_filename}")

# -------------------------------
# Step 3: Transcribe the M4A audio file using Groq
# -------------------------------
# Initialize the Groq client (replace with your actual API key)
groq_API = ''  # Insert your Groq API key here
client = Groq(api_key=groq_API)

# Build the file path to the audio file assuming it's in the same directory as this script
filename = os.path.join(os.path.dirname(__file__), m4a_filename)

# Open the audio file and send it for transcription
with open(filename, "rb") as file:
    transcription = client.audio.transcriptions.create(
        file=file,                                  # Audio file input
        model="distil-whisper-large-v3-en",          # The model to use for transcription
        prompt="Specify context or spelling",        # Optional context prompt
        response_format="verbose_json",              # Verbose output format with timestamps
        timestamp_granularities=["word", "segment"], # Detailed time information for words and segments
        language="en",                               # Language of the audio
        temperature=0.0                              # Decoding temperature (for determinism)
    )
    # Print the complete transcription result as a formatted JSON
    print(json.dumps(transcription, indent=2, default=str))
