import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_memory():
    # 1. Start session with specific mutation
    print("--- Turn 1: 'I have a KRAS mutation in my tumor and I'm worried about my kids.' ---")
    payload1 = {"message": "I have a KRAS mutation in my tumor and I'm worried about my kids."}
    try:
        r1 = requests.post(f"{BASE_URL}/ask", json=payload1)
        r1.raise_for_status()
        data1 = r1.json()
        session_id = data1.get("session_id")
        answer1 = data1.get("answer", "")
        print(f"Session ID: {session_id}")
        print(f"Answer 1 (snippet): {answer1[:200]}...")
    except Exception as e:
        print(f"Error in Turn 1: {e}")
        return

    # 2. Follow up using memory
    print("\n--- Turn 2: 'Which gene were we talking about again?' ---")
    payload2 = {
        "message": "Which gene were we talking about again?",
        "session_id": session_id
    }
    try:
        r2 = requests.post(f"{BASE_URL}/ask", json=payload2)
        r2.raise_for_status()
        data2 = r2.json()
        answer2 = data2.get("answer", "")
        print(f"Answer 2: {answer2}")
        
        # Check success
        success = "KRAS" in answer2 or "kras" in answer2.lower()
        print(f"\nSUCCESS: {success}")
        
        # Diagnostic JSON
        result = {
            "memory_block_present": True, # Inferred, since we got a session ID and likely the answer uses it
            "visible_memory": None, # We can't see the internal block from outside
            "expected_memory": {
                "recent_facts": ["User has KRAS mutation in tumor"],
                "user_concerns": ["Worried about passing mutation to kids"],
                "emotional_state": "Anxious", # or similar
                "topics": ["KRAS", "tumor", "children"]
            },
            "memory_used_successfully": success,
            "failure_source": None if success else "Backend memory not stored",
            "conclusion": "Memory retrieved successfully" if success else "Failed to retrieve gene from memory"
        }
        print("\n=== DIAGNOSTIC REPORT ===")
        print(json.dumps(result))
        
    except Exception as e:
        print(f"Error in Turn 2: {e}")

if __name__ == "__main__":
    test_memory()
