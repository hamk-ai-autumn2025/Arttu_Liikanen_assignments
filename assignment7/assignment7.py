from openai import OpenAI
import sounddevice as sd
import os
import scipy.io.wavfile as wav

client = OpenAI()
file_path = "speech.mp3"

duration = 10  # seconds
fs = 16000  # sample rate

# Step 1: Record audio from microphone
print("Please speak now...")
audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
sd.wait()

print("Translating...")

# Step 2: Transcribe audio
wav_file_path = "speech.wav"
wav.write(wav_file_path, fs, audio)

with open(wav_file_path, "rb") as audio_file:
    transcription = client.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=audio_file
    )

# Step 3: Translate transcription to English using GPT-4
translation_response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "Translate the following text to English."},
        {"role": "user", "content": transcription.text}
    ]
)

print("Translation: ", translation_response.choices[0].message.content)

with client.audio.speech.with_streaming_response.create(
    model="gpt-4o-mini-tts",
    voice="coral",
    input=translation_response.choices[0].message.content,
    instructions="Speak in a cheerful and positive tone.",
) as response:
    response.stream_to_file(file_path)
    
print("Translation audio saved to", file_path)
os.remove(wav_file_path)