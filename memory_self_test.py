import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def run_test():
    # 1. Start fresh session to get initial state
    try:
        r0 = requests.post(f"{BASE_URL}/ask", json={"message": "Hello"})
        r0.raise_for_status()
        data0 = r0.json()
        session_id = data0.get("session_id")
        memory_before = data0.get("clinical_state", {})
    except Exception as e:
        print(json.dumps({"error": f"Init failed: {e}"}))
        return

    # 2. Simulate processing input
    # "I have a KRAS mutation in my tumor and I'm worried about my kids."
    try:
        payload1 = {"message": "I have a KRAS mutation in my tumor and I'm worried about my kids.", "session_id": session_id}
        r1 = requests.post(f"{BASE_URL}/ask", json=payload1)
        r1.raise_for_status()
        data1 = r1.json()
        memory_after = data1.get("clinical_state", {})
    except Exception as e:
        print(json.dumps({"error": f"Turn 1 failed: {e}"}))
        return

    # 3. Simulate next user input
    # "Which gene were we talking about again?"
    try:
        payload2 = {"message": "Which gene were we talking about again?", "session_id": session_id}
        r2 = requests.post(f"{BASE_URL}/ask", json=payload2)
        r2.raise_for_status()
        data2 = r2.json()
        answer = data2.get("answer", "")
        # Memory used is effectively the state present *before* this turn generated the answer.
        # Which is memory_after from the previous turn.
    except Exception as e:
        print(json.dumps({"error": f"Turn 2 failed: {e}"}))
        return

    # Filter memory output to relevant fields for brevity
    def clean_mem(m):
        return {
            "recent_facts": m.get("recent_facts"),
            "user_concerns": m.get("user_concerns"),
            "emotional_state": m.get("user_emotion"),
            "topics": list(m.get("topics_discussed", [])) if isinstance(m.get("topics_discussed"), (list, set)) else m.get("topics_discussed")
        }

    output = {
        "session_id": session_id,
        "memory_before": clean_mem(memory_before),
        "memory_after": clean_mem(memory_after),
        "answer_to_gene_question": answer,
        "memory_used": clean_mem(memory_after) 
    }
    
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    run_test()
