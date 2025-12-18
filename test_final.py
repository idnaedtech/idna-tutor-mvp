#!/usr/bin/env python3
"""
Final comprehensive test: question rotation with progress signals.
"""
import grpc
import tutoring_pb2
import tutoring_pb2_grpc

ch = grpc.insecure_channel("localhost:50051")
stub = tutoring_pb2_grpc.TutoringServiceStub(ch)

# Start session
start = stub.StartSession(tutoring_pb2.StartSessionRequest(student_id="final_test"))
sid = start.session_id
print(f"✅ Session: {sid}")
print(f"   Topic: {start.tutor_text[:50]}...\n")

seen_questions = []

for round in range(1, 4):
    print(f"--- ROUND {round} ---")
    
    # Ask for question
    r1 = stub.Turn(tutoring_pb2.TurnRequest(student_id="final_test", session_id=sid, user_text="next" if round == 1 else "ok"))
    
    if r1.next_state != tutoring_pb2.QUIZ:
        print(f"Skipped (state={r1.next_state})")
        continue
    
    qid = r1.question_id
    seen_questions.append(qid)
    print(f"Question: {qid[:8]}... | {r1.tutor_text[10:45]}")
    print(f"  topic_id: {r1.topic_id[:8] if r1.topic_id else 'N/A'}...")
    
    # Answer transition
    r2 = stub.Turn(tutoring_pb2.TurnRequest(student_id="final_test", session_id=sid, user_text="dummy"))
    
    # Answer correctly
    ans = "4" if "2 + 2" in r1.tutor_text else ("5" if "3 + 2" in r1.tutor_text else "2")
    r3 = stub.Turn(tutoring_pb2.TurnRequest(student_id="final_test", session_id=sid, user_text=ans))
    
    print(f"✓ Answered {ans}, got: {r3.tutor_text[:40]}...")
    if r3.question_id:
        print(f"  Next: {r3.question_id[:8]}...")
    print()

print(f"✅ Seen questions: {[q[:8] for q in seen_questions]}")
unique = len(set(seen_questions))
total = len(seen_questions)
print(f"   Unique: {unique}/{total}")
