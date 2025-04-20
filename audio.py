import os
import struct
import wave
import tempfile
import time
import io
import pvporcupine
import pyaudio
from groq import Groq
from load_env import groq_API, pvporcupine

porcupine = pvporcupine.create(keywords=["Hello Amadeus"],
                               access_key=pvporcupine,
                               keyword_paths=["Hello-Amadeus.ppn"])

# Start audio stream
pa = pyaudio.PyAudio()
stream = pa.open(
    rate=porcupine.sample_rate,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    frames_per_buffer=porcupine.frame_length
)
# Initialize Groq client
client = Groq(api_key=groq_API)


def record_to_wav(duration_s: float, sample_rate: int, channels: int = 1) -> str:
    """Record `duration_s` seconds from `stream` into a temp WAV file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)  # we’ll re‑open via wave
    wf = wave.open(path, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
    wf.setframerate(sample_rate)

    frames = []
    deadline = time.time() + duration_s
    while time.time() < deadline:
        data = stream.read(porcupine.frame_length, exception_on_overflow=False)
        frames.append(data)

    wf.writeframes(b''.join(frames))
    wf.close()
    return path


def transcribe_with_groq(wav_path: str):
    """Send the recorded WAV file at `wav_path` to Groq and print the transcript."""
    with open(wav_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3-turbo",
            prompt="",
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
            language="en",
            temperature=0.0
        )
    # Print the full JSON or just the text:
    # If you only want the text:
    # print(transcription["text"])
    return transcription.text


def read(text):
    response = client.audio.speech.create(
        model="playai-tts",
        voice="Arista-PlayAI",
        input=text,
        response_format="wav"
    )
    audio_bytes = response.parse()  # contains the complete WAV payload
    wav_buffer = io.BytesIO(audio_bytes)
    wav_buffer.seek(0)

    # 2b) Open it as a Wave_read
    wf = wave.open(wav_buffer, 'rb')

    # 2c) Configure PyAudio playback stream
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pa.get_format_from_width(wf.getsampwidth()),
        channels=wf.getnchannels(),
        rate=wf.getframerate(),
        output=True
    )

    # 2d) Read & play frames in chunks
    chunk = 1024
    data = wf.readframes(chunk)
    while data:
        stream.write(data)
        data = wf.readframes(chunk)

    # 2e) Clean up
    stream.stop_stream()
    stream.close()
    pa.terminate()
    wf.close()
    return response


def listen():
    print("Listening for wake word...")
    try:
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
            if porcupine.process(pcm_unpacked) >= 0:
                print("[Wake word detected] Recording 5 seconds...")
                wav_path = record_to_wav(duration_s=5.0, sample_rate=porcupine.sample_rate)
                print("Transcribing with Groq…")
                transcribe = transcribe_with_groq(wav_path)
                os.remove(wav_path)
                return transcribe
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        porcupine.delete()


if __name__ == "__main__":
    read(listen())
