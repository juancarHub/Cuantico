from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
import os

load_dotenv()

elevenlabs = ElevenLabs(
  api_key="sk_ab33848bb556754b7d22d5e073710e8fcd97c5e03b3076a3",
)

audio = elevenlabs.text_to_speech.convert(
    text="hola esto es una prueba de audio, me cagonnnn tó",
    voice_id="JBFqnCBsd6RMkjVDRZzb",  # "George" - browse voices at elevenlabs.io/app/voice-libraryweA4Q36twV5kwSaTEL0Q", 
    model_id="eleven_v3",
    output_format="mp3_44100_128",
)

play(audio)

