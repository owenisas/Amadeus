import os
import struct
import wave
import tempfile
import time
import io
import pvporcupine
import pyaudio
from groq import Groq
from load_env import groq_API, pvporcupine_mac_API, pvporcupine_win_API

porcupine = pvporcupine.create(keywords=["Hello Amadeus"],
                               access_key=pvporcupine_win_API,
                               keyword_paths=["Hello-Amadeus_win.ppn"])

# Initialize Groq client
client = Groq(api_key=groq_API)


def record_to_wav(pa, stream, duration_s, channels=1):
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    wf = wave.open(path, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
    wf.setframerate(porcupine.sample_rate)

    frames = []
    end = time.time() + duration_s
    while time.time() < end:
        frames.append(stream.read(porcupine.frame_length))
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


def start_stream():
    pa = pyaudio.PyAudio()
    try:
        stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length,
            # you can optionally pick a specific device here
        )
        return pa, stream
    except Exception:
        pa.terminate()
        raise


def listen():
    print("Listening for wake word...")
    pa, stream = start_stream()
    try:
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
            if porcupine.process(pcm_unpacked) >= 0:
                print("[Wake word detected] Recording 5 seconds...")
                wav_path = record_to_wav(stream=stream, duration_s=5.0)
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
