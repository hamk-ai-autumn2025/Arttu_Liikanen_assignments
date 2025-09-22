from openai import OpenAI
import openai
import sounddevice as sd
import numpy as np
import queue
import wave
import tempfile
import keyboard

client = OpenAI()

# Audio recording parameters
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 1024
DURATION = 20  # seconds to record per message

def record_audio(duration=DURATION):
    q = queue.Queue()

    def callback(indata, *_):
        q.put(indata.copy())

    print("Recording... Press SPACE to stop early.")
    frames = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback, blocksize=BLOCK_SIZE):
        for _ in range(int(SAMPLE_RATE / BLOCK_SIZE * duration)):
            if keyboard.is_pressed('space'):
                break
            frames.append(q.get())
    audio = np.concatenate(frames, axis=0)
    print("Recording stopped.")
    return audio

def save_wav(audio, filename):
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())

def transcribe_audio(filename):
    with open(filename, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return transcript.text

def chat_with_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt},
            {"role": "system", "content": "You are an old friend of the user. Respond in a friendly, familiar, and informal manner. Only natural and short."}
        ]
    )
    return response.choices[0].message.content

def main():
    conversation = [
        {"role": "system", "content": "You are an old friend of the user. Respond in a friendly, familiar, and informal manner. Only natural and short."}
    ]
    while True:
        audio = record_audio()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            save_wav(audio, temp_wav.name)
            text = transcribe_audio(temp_wav.name)
        print(f"You said: {text}", flush=True)
        conversation.append({"role": "user", "content": text})
        print("Waiting for AI reply...", flush=True)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=conversation,
            stream=True
        )
        reply = ""
        print("AI reply: ", end="", flush=True)
        for chunk in response:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
                reply += chunk.choices[0].delta.content
        print()
        conversation.append({"role": "assistant", "content": reply})
        cont = input("Record another message? (y/n): ")
        if cont.lower().strip() != 'y':
            break

if __name__ == "__main__":
    main()