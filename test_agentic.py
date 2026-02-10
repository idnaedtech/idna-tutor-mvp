"""
Quick test for the Agentic Tutor
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from agentic_tutor import AgenticTutor


async def test_tutor():
    print("=" * 50)
    print("IDNA Agentic Tutor Test")
    print("=" * 50)

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set in .env")
        return

    # Create tutor
    print("\n1. Creating tutor...")
    tutor = AgenticTutor(student_name="Test Student", chapter="rational_numbers")
    print(f"   Chapter: {tutor.session['chapter']}")
    print(f"   Questions: {tutor.session['total_questions']}")

    # Start session
    print("\n2. Starting session...")
    greeting = await tutor.start_session()
    print(f"   Tutor: {greeting}")

    # Test correct answer
    print("\n3. Testing correct answer (-1/7)...")
    response = await tutor.process_input("minus 1 by 7")
    print(f"   Tutor: {response}")
    print(f"   Score: {tutor.session['score']}/{tutor.session['questions_completed']}")

    # Test wrong answer
    print("\n4. Testing wrong answer...")
    response = await tutor.process_input("5")
    print(f"   Tutor: {response}")
    print(f"   Hints given: {tutor.session['hint_count']}")

    # Test IDK
    print("\n5. Testing 'I don't know'...")
    response = await tutor.process_input("I don't know")
    print(f"   Tutor: {response}")

    # Test stop
    print("\n6. Testing stop request...")
    response = await tutor.process_input("bye")
    print(f"   Tutor: {response}")
    print(f"   Session ended: {tutor.session['session_ended']}")

    print("\n" + "=" * 50)
    print("Test complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_tutor())
