#!/usr/bin/env python3
"""
Test question rotation and non-repeating logic.
Verifies that pick_question_unseen() doesn't repeat questions in a session.
"""

import grpc
import tutoring_pb2
import tutoring_pb2_grpc
import time

def test_question_rotation():
    """Test that correct answers pick new, non-repeating questions."""
    channel = grpc.insecure_channel('localhost:50051')
    stub = tutoring_pb2_grpc.TutoringServiceStub(channel)
    
    # Start session
    start_resp = stub.StartSession(tutoring_pb2.StartSessionRequest(student_id="test_rotation"))
    sid = start_resp.session_id
    print(f"✓ Session started: {sid}")
    print(f"  Topic: {start_resp.tutor_text.split(':')[0]}")
    print()
    
    seen_questions = set()
    correct_count = 0
    
    for round_num in range(1, 4):
        print(f"--- Round {round_num} ---")
        
        # Ask for question
        resp = stub.Turn(tutoring_pb2.TurnRequest(
            session_id=sid, 
            student_id="test_rotation", 
            user_text="next" if round_num == 1 else "ok"
        ))
        
        if resp.next_state != tutoring_pb2.QUIZ:
            print(f"  State: {resp.next_state}, Text: {resp.tutor_text}")
            continue
            
        q_id = resp.question_id
        print(f"  Question ID: {q_id[:8]}...")
        print(f"  Question: {resp.tutor_text[10:50]}...")
        
        if q_id in seen_questions:
            print(f"  ❌ ERROR: Question repeated! Already saw {q_id[:8]}...")
            return False
        seen_questions.add(q_id)
        
        # Move to evaluate
        resp = stub.Turn(tutoring_pb2.TurnRequest(
            session_id=sid,
            student_id="test_rotation",
            user_text="dummy"
        ))
        print(f"  Moved to state: {resp.next_state}")
        
        # Answer correctly
        resp = stub.Turn(tutoring_pb2.TurnRequest(
            session_id=sid,
            student_id="test_rotation",
            user_text="4" if round_num == 1 else ("5" if round_num == 2 else "2")
        ))
        
        if resp.intent == "correct":
            correct_count += 1
            print(f"  ✓ Correct! Moving to: {resp.tutor_text[:40]}...")
            print(f"  New question ID: {resp.question_id[:8]}...")
        else:
            print(f"  State: {resp.next_state}, Intent: {resp.intent}")
        print()
    
    print(f"✅ Test passed: {len(seen_questions)} unique questions in {correct_count} correct answers")
    print(f"   Seen questions: {[q[:8] for q in seen_questions]}")
    return True

if __name__ == "__main__":
    try:
        time.sleep(1)  # Wait for server
        success = test_question_rotation()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        exit(1)
