"""
IDNA EdTech - Voice Input Module
Uses OpenAI Whisper for Speech-to-Text
"""

import os
import tempfile
import wave
import threading
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Check if pyaudio is available
PYAUDIO_AVAILABLE = False
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    print("Note: PyAudio not installed. Using file-based input.")


class VoiceInput:
    """Handle voice input using OpenAI Whisper"""
    
    def __init__(self):
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
        self.record_seconds = 5  # Default recording duration
        
        if PYAUDIO_AVAILABLE:
            self.audio = pyaudio.PyAudio()
        else:
            self.audio = None
    
    def record_audio(self, duration=5):
        """Record audio from microphone"""
        if not PYAUDIO_AVAILABLE:
            print("PyAudio not available. Cannot record.")
            return None
        
        print(f"\n🎤 Recording for {duration} seconds... SPEAK NOW!")
        
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        frames = []
        for _ in range(0, int(self.sample_rate / self.chunk_size * duration)):
            data = stream.read(self.chunk_size)
            frames.append(data)
        
        print("✓ Recording complete!")
        
        stream.stop_stream()
        stream.close()
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(temp_file.name, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
        
        return temp_file.name
    
    def transcribe(self, audio_file_path):
        """Transcribe audio file using Whisper"""
        try:
            with open(audio_file_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
            return response.text.strip()
        except Exception as e:
            print(f"Transcription error: {e}")
            return None
        finally:
            # Clean up temp file
            if os.path.exists(audio_file_path):
                os.remove(audio_file_path)
    
    def listen(self, duration=5):
        """Record and transcribe in one step"""
        audio_file = self.record_audio(duration)
        if audio_file:
            text = self.transcribe(audio_file)
            if text:
                print(f"   You said: \"{text}\"")
            return text
        return None
    
    def cleanup(self):
        """Clean up audio resources"""
        if self.audio:
            self.audio.terminate()


def get_voice_input(prompt="Your answer", duration=5):
    """Simple function to get voice input"""
    if not PYAUDIO_AVAILABLE:
        # Fallback to text input
        return input(f"{prompt}: ").strip()
    
    voice = VoiceInput()
    try:
        print(f"\n{prompt}")
        print("(Press Enter to start recording, or type your answer)")
        
        choice = input("> ").strip()
        
        if choice == "":
            # Record voice
            text = voice.listen(duration)
            return text if text else ""
        else:
            # User typed instead
            return choice
    finally:
        voice.cleanup()


# Test the module
if __name__ == "__main__":
    print("=" * 50)
    print("   VOICE INPUT TEST")
    print("=" * 50)
    
    if not PYAUDIO_AVAILABLE:
        print("\n⚠️  PyAudio is not installed.")
        print("To enable voice input, run:")
        print("   pip install pyaudio")
        print("\nOn Windows, you may need:")
        print("   pip install pipwin")
        print("   pipwin install pyaudio")
        print("\nFalling back to text input for now.\n")
    
    print("\nTest 1: Get voice input")
    result = get_voice_input("Say a number", duration=3)
    print(f"Result: {result}")
    
    print("\n" + "=" * 50)
    print("Voice input test complete!")
