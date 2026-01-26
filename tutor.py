"""
IDNA EdTech - Interactive Math Tutor
Class 8 Mathematics - All 5 Chapters
"""

import os
import random
from dotenv import load_dotenv
from openai import OpenAI
from questions import ALL_CHAPTERS, CHAPTER_NAMES, check_answer

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class MathTutor:
    def __init__(self):
        self.current_chapter = None
        self.current_question = None
        self.attempt_count = 0
        self.score = 0
        self.total = 0
        self.session_questions = []
    
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
    
    def show_welcome(self):
        """Display welcome message"""
        print("\n" + "=" * 55)
        print("       IDNA MATH TUTOR - Class 8 Mathematics")
        print("=" * 55)
        print(self.ai_say("Welcome a Class 8 student to math practice. Be brief."))
        print("\nType 'quit' anytime to exit.")
        print("Type 'change' to switch chapters.\n")
    
    def select_chapter(self):
        """Let user select a chapter"""
        print("-" * 55)
        print("CHAPTERS:")
        print("-" * 55)
        
        chapters = list(ALL_CHAPTERS.keys())
        for i, ch in enumerate(chapters, 1):
            print(f"  {i}. {CHAPTER_NAMES[ch]}")
        
        print(f"  {len(chapters) + 1}. Random (All Chapters)")
        print("-" * 55)
        
        while True:
            choice = input("Select chapter (1-6): ").strip()
            
            if choice == 'quit':
                return None
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(chapters):
                    self.current_chapter = chapters[choice_num - 1]
                    print(f"\nGreat! Let's practice {CHAPTER_NAMES[self.current_chapter]}.")
                    return self.current_chapter
                elif choice_num == len(chapters) + 1:
                    self.current_chapter = "random"
                    print("\nGreat! Let's practice questions from all chapters.")
                    return "random"
                else:
                    print("Please enter a number between 1 and 6.")
            except ValueError:
                print("Please enter a valid number.")
    
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
        print(f"\n   {self.current_question['text']}\n")
        
        while self.attempt_count < 3:
            ans = input("Your answer: ").strip()
            
            if ans.lower() == 'quit':
                return 'quit'
            
            if ans.lower() == 'change':
                return 'change'
            
            if check_answer(self.current_question['answer'], ans):
                self.score += 1
                praise = self.ai_say(f"Student correctly solved: {self.current_question['text']}. Give brief praise.")
                print(f"\n✓ Correct! {praise}")
                return 'correct'
            else:
                self.attempt_count += 1
                if self.attempt_count < 3:
                    hint_key = f"hint{self.attempt_count}"
                    print(f"\n✗ Not quite right.")
                    print(f"   Hint: {self.current_question[hint_key]}")
                    print(f"   (Attempt {self.attempt_count}/3)\n")
                else:
                    print(f"\n✗ The correct answer is: {self.current_question['answer']}")
                    print(f"\n   Solution:")
                    for line in self.current_question['solution'].split('\n'):
                        print(f"   {line}")
                    encouragement = self.ai_say("Student couldn't solve after 3 tries. Give brief encouragement.")
                    print(f"\n   {encouragement}")
                    return 'wrong'
        
        return 'wrong'
    
    def show_summary(self):
        """Display session summary"""
        print("\n" + "=" * 55)
        print("               SESSION COMPLETE!")
        print("=" * 55)
        print(f"\n   Questions attempted: {self.total}")
        print(f"   Correct answers:     {self.score}")
        print(f"   Wrong answers:       {self.total - self.score}")
        
        if self.total > 0:
            accuracy = (self.score / self.total) * 100
            print(f"   Accuracy:            {accuracy:.0f}%")
            
            # Performance message
            if accuracy >= 80:
                msg = "Excellent work! You're mastering this topic!"
            elif accuracy >= 60:
                msg = "Good job! Keep practicing to improve further."
            else:
                msg = "Keep trying! Practice makes perfect."
            
            print(f"\n   {msg}")
        
        closing = self.ai_say(f"Student completed {self.total} questions with {self.score} correct. Give brief closing encouragement.")
        print(f"\n   {closing}")
        print("\n" + "=" * 55)
    
    def run(self):
        """Main tutor loop"""
        self.show_welcome()
        
        # Select initial chapter
        if self.select_chapter() is None:
            print("\nGoodbye!")
            return
        
        # Main question loop
        while True:
            result = self.ask_question()
            
            if result == 'quit':
                break
            
            if result == 'change':
                self.total -= 1  # Don't count this as a question
                if self.select_chapter() is None:
                    break
                continue
            
            # After every 5 questions, ask if they want to continue
            if self.total > 0 and self.total % 5 == 0:
                print(f"\n   You've completed {self.total} questions!")
                cont = input("   Continue practicing? (yes/no): ").strip().lower()
                if cont not in ['yes', 'y', '']:
                    break
        
        # Show final summary
        self.show_summary()


if __name__ == "__main__":
    tutor = MathTutor()
    tutor.run()
