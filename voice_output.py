"""
IDNA EdTech - Voice Output Module
Uses OpenAI TTS for Text-to-Speech
"""

import os
import tempfile
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Check if playsound is available
PLAYSOUND_AVAILABLE = False
try:
    from playsound import playsound
    PLAYSOUND_AVAILABLE = True
except ImportError:
    pass

# Alternative: pygame
PYGAME_AVAILABLE = False
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    pass


class VoiceOutput:
    """Handle voice output using OpenAI TTS"""
    
    def __init__(self, voice="nova"):
        """
        Initialize TTS
        
        Voices available:
        - alloy: Neutral
        - echo: Male
        - fable: Expressive
        - onyx: Deep male
        - nova: Female (recommended for tutor)
        - shimmer: Soft female
        """
        self.voice = voice
        self.model = "tts-1"  # Use tts-1-hd for higher quality
    
    def speak(self, text, wait=True):
        """Convert text to speech and play it"""
        if not text:
            return
        
        try:
            # Generate speech
            response = client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text
            )
            
            # Save to temp file
            temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_file.close()
            
            response.stream_to_file(temp_file.name)
            
            # Play the audio
            self._play_audio(temp_file.name)
            
            # Cleanup with delay to ensure file is released
            import time
            time.sleep(0.5)
            try:
                if os.path.exists(temp_file.name):
                    os.remove(temp_file.name)
            except:
                pass  # Ignore cleanup errors
                
        except Exception as e:
            print(f"TTS Error: {e}")
            # Fallback: just print the text
            print(f"🔊 {text}")
    
    def _play_audio(self, file_path):
        """Play audio file"""
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                return
            except Exception as e:
                print(f"Pygame error: {e}")
        
        if PLAYSOUND_AVAILABLE:
            try:
                playsound(file_path)
                return
            except Exception as e:
                print(f"Playsound error: {e}")
        
        # Fallback: use system command
        if os.name == 'nt':  # Windows
            os.system(f'start /min wmplayer "{file_path}"')
        elif os.name == 'posix':  # Linux/Mac
            os.system(f'afplay "{file_path}" 2>/dev/null || mpg123 "{file_path}" 2>/dev/null')


def speak(text, voice="nova"):
    """Simple function to speak text"""
    tts = VoiceOutput(voice=voice)
    tts.speak(text)


# Test the module
if __name__ == "__main__":
    print("=" * 50)
    print("   VOICE OUTPUT TEST")
    print("=" * 50)
    
    if not PYGAME_AVAILABLE and not PLAYSOUND_AVAILABLE:
        print("\n⚠️  No audio library installed.")
        print("To enable voice output, run ONE of:")
        print("   pip install pygame")
        print("   pip install playsound")
        print("\nUsing system default player as fallback.\n")
    
    print("\nTest 1: Speaking a greeting...")
    speak("Hello! I am your math tutor. Let's learn together!")
    
    print("\nTest 2: Speaking a question...")
    speak("What is 5 plus 7?")
    
    print("\nTest 3: Speaking encouragement...")
    speak("Great job! You got it right!")
    
    print("\n" + "=" * 50)
    print("Voice output test complete!")
