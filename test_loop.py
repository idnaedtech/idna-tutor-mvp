#!/usr/bin/env python3
"""
Test question rotation across 5 iterations.
Verifies that each correct answer picks a new, unseen question.
"""

import grpc
import tutoring_pb2
import tutoring_pb2_grpc
import time

STUDENT_ID = "00000000-0000-0000-0000-000000000001"

def main():
    ch = grpc.insecure_channel("localhost:50051")
    stub = tutoring_pb2_grpc.TutoringServiceStub(ch)

    start = stub.StartSession(tutoring_pb2.StartSessionRequest(student_id=STUDENT_ID))
    sid = start.session_id
    print(f"Session: {sid}")
    print()

    seen = []
    for i in range(5):
        # Trigger question
        r1 = stub.Turn(tutoring_pb2.TurnRequest(
            student_id=STUDENT_ID, 
            session_id=sid, 
            user_text="next" if i == 0 else "ok"
        ))
        
        qid = getattr(r1, "question_id", None)
        print(f"Q{i+1}: {qid[:8] if qid else 'N/A'}... | {r1.tutor_text[:50]}")
        if qid:
            seen.append(qid)
        
        # Skip if not QUIZ state
        if r1.next_state != tutoring_pb2.QUIZ:
            print(f"  (skipped: state={r1.next_state})")
            continue

        # Move to EVALUATE
        r2 = stub.Turn(tutoring_pb2.TurnRequest(
            student_id=STUDENT_ID, 
            session_id=sid, 
            user_text="dummy"
        ))

        # Answer correctly - detect answer from prompt
        ans = "4"  # default
        if "7 + 3" in r1.tutor_text:
            ans = "10"
        elif "9 + 6" in r1.tutor_text:
            ans = "15"
        elif "3 + 2" in r1.tutor_text:
            ans = "5"
        elif "1 + 1" in r1.tutor_text:
            ans = "2"

        r3 = stub.Turn(tutoring_pb2.TurnRequest(
            student_id=STUDENT_ID, 
            session_id=sid, 
            user_text=ans
        ))
        print(f"  A: {ans} | {r3.tutor_text[:50]} | intent={r3.intent}")
        print("-" * 60)
        time.sleep(0.1)

    print(f"\n✅ Seen {len(seen)} question IDs:")
    for i, qid in enumerate(seen, 1):
        print(f"  {i}. {qid[:16]}...")
    
    # Check for duplicates
    if len(seen) == len(set(seen)):
        print(f"\n✅ All unique (no repeats)")
    else:
        print(f"\n❌ DUPLICATES FOUND!")
        for qid in seen:
            if seen.count(qid) > 1:
                print(f"  Repeated: {qid[:16]}... ({seen.count(qid)}x)")

if __name__ == "__main__":
    try:
        time.sleep(1)  # Wait for server
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
