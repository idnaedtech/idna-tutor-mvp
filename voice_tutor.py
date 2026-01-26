"""
IDNA EdTech - Voice-Enabled Math Tutor
Class 8 Mathematics - Speak to Learn!
"""

import os
import random
from dotenv import load_dotenv
from openai import OpenAI
from questions import ALL_CHAPTERS, CHAPTER_NAMES, check_answer

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Voice modules
from voice_output import VoiceOutput, PYGAME_AVAILABLE, PLAYSOUND_AVAILABLE
from voice_input import VoiceInput, PYAUDIO_AVAILABLE


class VoiceMathTutor:
    def __init__(self):
        self.current_chapter = None
        self.current_question = None
        self.attempt_count = 0
        self.score = 0
        self.total = 0
        
        # Voice components
        self.tts = VoiceOutput(voice="nova")  # Female tutor voice
        self.stt = VoiceInput() if PYAUDIO_AVAILABLE else None
        
        # Voice mode setting
        self.voice_input_enabled = PYAUDIO_AVAILABLE
        self.voice_output_enabled = PYGAME_AVAILABLE or PLAYSOUND_AVAILABLE
    
    def ai_say(self, prompt):
        """Get a natural response from GPT"""
        try:
            r = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a friendly, encouraging math tutor for Class 8 students in India. Keep responses to 1-2 sentences. Be warm and supportive. Use simple language."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=60
            )
            return r.choices[0].message.content
        except Exception as e:
            return "Great effort! Let's continue."
    
    def speak(self, text, also_print=True):
        """Speak text (and optionally print it)"""
        if also_print:
            print(f"🔊 {text}")
        
        if self.voice_output_enabled:
            self.tts.speak(text)
    
    def listen(self, prompt="Your answer", duration=5):
        """Get input - voice or text"""
        if self.voice_input_enabled:
            print(f"\n{prompt}")
            print("[Press ENTER to speak, or type your answer]")
            
            choice = input("> ").strip()
            
            if choice == "":
                # Use voice
                text = self.stt.listen(duration)
                return text if text else ""
            else:
                return choice
        else:
            return input(f"{prompt}: ").strip()
    
    def show_welcome(self):
        """Display and speak welcome message"""
        print("\n" + "=" * 55)
        print("       🎤 IDNA VOICE MATH TUTOR 🔊")
        print("           Class 8 Mathematics")
        print("=" * 55)
        
        welcome = self.ai_say("Welcome a Class 8 student to voice-based math practice. Be brief and excited.")
        self.speak(welcome)
        
        print("\nCommands:")
        print("  'quit'   - End session")
        print("  'change' - Switch chapters")
        print("  'text'   - Switch to text-only mode")
        print("  'voice'  - Switch to voice mode")
        
        # Show voice status
        print("\n" + "-" * 55)
        print(f"Voice Input:  {'✅ Enabled' if self.voice_input_enabled else '❌ Disabled (install pyaudio)'}")
        print(f"Voice Output: {'✅ Enabled' if self.voice_output_enabled else '❌ Disabled (install pygame)'}")
        print("-" * 55 + "\n")
    
    def select_chapter(self):
        """Let user select a chapter"""
        print("\n" + "-" * 55)
        print("CHAPTERS:")
        print("-" * 55)
        
        chapters = list(ALL_CHAPTERS.keys())
        for i, ch in enumerate(chapters, 1):
            print(f"  {i}. {CHAPTER_NAMES[ch]}")
        print(f"  {len(chapters) + 1}. Random (All Chapters)")
        print("-" * 55)
        
        self.speak("Which chapter would you like to practice? Say the number or type it.")
        
        while True:
            choice = self.listen("Select chapter (1-6)", duration=3)
            
            if choice.lower() == 'quit':
                return None
            
            # Extract number from speech (e.g., "one" -> "1", "chapter 2" -> "2")
            choice = self._extract_number(choice)
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(chapters):
                    self.current_chapter = chapters[choice_num - 1]
                    msg = f"Great! Let's practice {CHAPTER_NAMES[self.current_chapter]}."
                    self.speak(msg)
                    return self.current_chapter
                elif choice_num == len(chapters) + 1:
                    self.current_chapter = "random"
                    self.speak("Great! Let's practice questions from all chapters.")
                    return "random"
                else:
                    self.speak("Please say a number between 1 and 6.")
            except ValueError:
                self.speak("I didn't catch that. Please say a number between 1 and 6.")
    
    def _extract_number(self, text):
        """Extract number from text (handles spoken numbers)"""
        text = text.lower().strip()
        
        # Word to number mapping
        word_to_num = {
            'one': '1', 'two': '2', 'three': '3', 
            'four': '4', 'five': '5', 'six': '6',
            'first': '1', 'second': '2', 'third': '3',
            'fourth': '4', 'fifth': '5', 'sixth': '6'
        }
        
        # Check for word numbers
        for word, num in word_to_num.items():
            if word in text:
                return num
        
        # Extract digits
        digits = ''.join(c for c in text if c.isdigit())
        if digits:
            return digits
        
        return text
    
    def get_next_question(self):
        """Get the next question"""
        if self.current_chapter == "random":
            return random.choice(
                [q for questions in ALL_CHAPTERS.values() for q in questions]
            )
        else:
            return random.choice(ALL_CHAPTERS[self.current_chapter])
    
    def ask_question(self):
        """Ask a question and handle the response"""
        self.current_question = self.get_next_question()
        self.attempt_count = 0
        self.total += 1
        
        print("\n" + "-" * 55)
        print(f"Question {self.total}:")
        question_text = self.current_question['text']
        print(f"\n   {question_text}\n")
        
        # Speak the question
        self.speak(f"Question {self.total}. {question_text}", also_print=False)
        
        while self.attempt_count < 3:
            ans = self.listen("Your answer", duration=5)
            
            if ans.lower() == 'quit':
                return 'quit'
            
            if ans.lower() == 'change':
                return 'change'
            
            if ans.lower() == 'text':
                self.voice_input_enabled = False
                self.voice_output_enabled = False
                print("Switched to text-only mode.")
                continue
            
            if ans.lower() == 'voice':
                self.voice_input_enabled = PYAUDIO_AVAILABLE
                self.voice_output_enabled = PYGAME_AVAILABLE or PLAYSOUND_AVAILABLE
                print("Switched to voice mode.")
                continue
            
            # Extract answer (handle spoken numbers)
            ans = self._extract_number(ans)
            
            if check_answer(self.current_question['answer'], ans):
                self.score += 1
                praise = self.ai_say(f"Student correctly solved: {question_text}. Give very brief praise.")
                print(f"\n✓ Correct!")
                self.speak(f"Correct! {praise}", also_print=False)
                print(f"   {praise}")
                return 'correct'
            else:
                self.attempt_count += 1
                if self.attempt_count < 3:
                    hint_key = f"hint{self.attempt_count}"
                    hint = self.current_question[hint_key]
                    print(f"\n✗ Not quite right.")
                    print(f"   Hint: {hint}")
                    print(f"   (Attempt {self.attempt_count}/3)\n")
                    self.speak(f"Not quite. Here's a hint: {hint}", also_print=False)
                else:
                    answer = self.current_question['answer']
                    solution = self.current_question['solution']
                    print(f"\n✗ The correct answer is: {answer}")
                    print(f"\n   Solution:")
                    for line in solution.split('\n'):
                        print(f"   {line}")
                    
                    self.speak(f"The correct answer is {answer}. Let's try another one!", also_print=False)
                    return 'wrong'
        
        return 'wrong'
    
    def show_summary(self):
        """Display and speak session summary"""
        print("\n" + "=" * 55)
        print("               SESSION COMPLETE!")
        print("=" * 55)
        print(f"\n   Questions attempted: {self.total}")
        print(f"   Correct answers:     {self.score}")
        print(f"   Wrong answers:       {self.total - self.score}")
        
        accuracy = 0
        if self.total > 0:
            accuracy = (self.score / self.total) * 100
            print(f"   Accuracy:            {accuracy:.0f}%")
            
            if accuracy >= 80:
                msg = "Excellent work! You're mastering this topic!"
            elif accuracy >= 60:
                msg = "Good job! Keep practicing to improve further."
            else:
                msg = "Keep trying! Practice makes perfect."
            
            print(f"\n   {msg}")
        
        # Speak summary
        summary = f"Great session! You got {self.score} out of {self.total} questions correct. That's {accuracy:.0f} percent accuracy."
        self.speak(summary)
        
        closing = self.ai_say(f"Student completed {self.total} questions with {accuracy:.0f}% accuracy. Give brief closing.")
        print(f"\n   {closing}")
        self.speak(closing, also_print=False)
        
        print("\n" + "=" * 55)
    
    def run(self):
        """Main tutor loop"""
        self.show_welcome()
        
        # Select initial chapter
        if self.select_chapter() is None:
            self.speak("Goodbye! Keep learning!")
            return
        
        # Main question loop
        while True:
            result = self.ask_question()
            
            if result == 'quit':
                break
            
            if result == 'change':
                self.total -= 1
                if self.select_chapter() is None:
                    break
                continue
            
            # After every 5 questions, ask if they want to continue
            if self.total > 0 and self.total % 5 == 0:
                print(f"\n   You've completed {self.total} questions!")
                self.speak(f"You've completed {self.total} questions. Want to continue?")
                cont = self.listen("Continue practicing? (yes/no)", duration=3).lower()
                if cont not in ['yes', 'y', 'yeah', 'yep', '']:
                    break
        
        # Show final summary
        self.show_summary()
        
        # Cleanup
        if self.stt:
            self.stt.cleanup()


if __name__ == "__main__":
    tutor = VoiceMathTutor()
    tutor.run()
