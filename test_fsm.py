#!/usr/bin/env python3
"""Test the FSM tutoring flow."""
import grpc
import tutoring_pb2
import tutoring_pb2_grpc

def test_fsm_flow():
    channel = grpc.insecure_channel("localhost:50051")
    stub = tutoring_pb2_grpc.TutoringServiceStub(channel)

    print("=" * 60)
    print("FSM TUTOR TEST")
    print("=" * 60)

    # 1. Start Session -> EXPLAIN
    print("\n[1] StartSession")
    start = stub.StartSession(tutoring_pb2.StartSessionRequest(
        student_id="test-student-001"
    ))
    print(f"State: {start.state} (expect EXPLAIN=1)")
    print(f"Session: {start.session_id}")
    print(f"Tutor: {start.tutor_text[:100]}...")
    assert start.state == 1, f"Expected EXPLAIN(1), got {start.state}"

    sid = start.session_id

    # 2. Any input -> QUIZ (first question)
    print("\n[2] Turn: 'ok' -> QUIZ")
    resp = stub.Turn(tutoring_pb2.TurnRequest(
        student_id="test-student-001",
        session_id=sid,
        user_text="ok"
    ))
    print(f"State: {resp.next_state} (expect QUIZ=2)")
    print(f"Tutor: {resp.tutor_text}")
    assert resp.next_state == 2, f"Expected QUIZ(2), got {resp.next_state}"

    # 3. Wrong answer -> HINT (attempt 1)
    print("\n[3] Turn: 'wrong' -> HINT1")
    resp = stub.Turn(tutoring_pb2.TurnRequest(
        student_id="test-student-001",
        session_id=sid,
        user_text="999"
    ))
    print(f"State: {resp.next_state} (expect HINT=4)")
    print(f"Intent: {resp.intent}")
    print(f"Attempts: {resp.attempt_count}")
    print(f"Tutor: {resp.tutor_text[:100]}...")
    assert resp.next_state == 4, f"Expected HINT(4), got {resp.next_state}"
    assert resp.intent == "hint1"
    assert resp.attempt_count == 1

    # 4. Wrong again -> HINT2 (attempt 2)
    print("\n[4] Turn: 'wrong again' -> HINT2")
    resp = stub.Turn(tutoring_pb2.TurnRequest(
        student_id="test-student-001",
        session_id=sid,
        user_text="888"
    ))
    print(f"State: {resp.next_state} (expect HINT=4)")
    print(f"Intent: {resp.intent}")
    print(f"Attempts: {resp.attempt_count}")
    print(f"Tutor: {resp.tutor_text[:100]}...")
    assert resp.next_state == 4, f"Expected HINT(4), got {resp.next_state}"
    assert resp.intent == "hint2"
    assert resp.attempt_count == 2

    # 5. Wrong third time -> REVEAL (attempt 3)
    print("\n[5] Turn: 'wrong third time' -> REVEAL + next question")
    resp = stub.Turn(tutoring_pb2.TurnRequest(
        student_id="test-student-001",
        session_id=sid,
        user_text="777"
    ))
    print(f"State: {resp.next_state} (expect REVEAL=5)")
    print(f"Intent: {resp.intent}")
    print(f"Attempts: {resp.attempt_count}")
    print(f"Tutor: {resp.tutor_text[:150]}...")
    assert resp.next_state == 5, f"Expected REVEAL(5), got {resp.next_state}"
    assert resp.intent == "reveal"
    assert resp.attempt_count == 3

    # 6. Now we're on question 2, test correct answer
    print("\n[6] Answering remaining questions correctly...")

    for i in range(4):  # Questions 2-5
        # Get current question from tutor text and answer correctly
        # We'll just try numbers 2-20 until one works
        for guess in range(2, 21):
            resp = stub.Turn(tutoring_pb2.TurnRequest(
                student_id="test-student-001",
                session_id=sid,
                user_text=str(guess)
            ))
            if resp.intent in ["correct", "complete"]:
                print(f"  Q{i+2}: Correct with {guess}! State={resp.next_state}")
                break
            elif resp.intent == "reveal":
                print(f"  Q{i+2}: Revealed after wrong guesses. State={resp.next_state}")
                break

        if resp.intent == "complete":
            break

    print(f"\nFinal response: {resp.tutor_text}")
    print(f"Final intent: {resp.intent}")

    print("\n" + "=" * 60)
    print("FSM TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_fsm_flow()
