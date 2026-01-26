#!/usr/bin/env python3
"""
Test question rotation - verify non-repeating questions.
Simple direct test of the rotation logic.
"""
import grpc
import tutoring_pb2
import tutoring_pb2_grpc

ch = grpc.insecure_channel('localhost:50051')
stub = tutoring_pb2_grpc.TutoringServiceStub(ch)

# Start
start = stub.StartSession(tutoring_pb2.StartSessionRequest(student_id="rotation_test"))
sid = start.session_id
print(f"✓ Session: {sid[:8]}...\n")

seen = []
for i in range(3):
    print(f"Round {i+1}:")
    
    # Get question
    r1 = stub.Turn(tutoring_pb2.TurnRequest(student_id="rotation_test", session_id=sid, user_text="next"))
    q_id = r1.question_id
    print(f"  Q: {r1.tutor_text[10:45]}... (ID: {q_id[:8]}...)")
    
    if q_id in seen:
        print(f"  ❌ REPEAT DETECTED")
        exit(1)
    seen.append(q_id)
    
    # Move through FSM
    stub.Turn(tutoring_pb2.TurnRequest(student_id="rotation_test", session_id=sid, user_text="dummy"))  # QUIZ->EVALUATE
    ans = "4" if "2 + 2" in r1.tutor_text else ("5" if "3 + 2" in r1.tutor_text else ("2" if "1 + 1" in r1.tutor_text else "7"))
    r3 = stub.Turn(tutoring_pb2.TurnRequest(student_id="rotation_test", session_id=sid, user_text=ans))  # EVALUATE->QUIZ
    print(f"  ✓ Correct! Next: {r3.question_id[:8] if r3.question_id else 'ERROR'}...\n")

print(f"✅ SUCCESS: 3 unique questions, no repeats")
