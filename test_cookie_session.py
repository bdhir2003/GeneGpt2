import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def run_session_cookie_test():
    print("--- Starting Cookie Session Test ---")
    s = requests.Session()
    
    # 1. First Request (No cookie)
    try:
        r1 = s.post(f"{BASE_URL}/ask", json={"message": "Initialize session"})
        r1.raise_for_status()
        sid1_cookie = s.cookies.get("session_id")
        data1 = r1.json()
        print(f"Request 1: Cookie SID = {sid1_cookie}")
        
        if not sid1_cookie:
            print("FAIL: Backend did not set session_id cookie.")
            return

    except Exception as e:
        print(f"Error Req 1: {e}")
        return

    # 2. Second Request (Should send cookie)
    try:
        r2 = s.post(f"{BASE_URL}/ask", json={"message": "Follow up"})
        r2.raise_for_status()
        # Backend should see the cookie and reuse the session ID
        # Wait, how do I verify reuse?
        # I can check the audit log if I could see it, but I can check if the returned answer_json's session_id matches?
        # My backend code doesn't explicitly put the reused SID in the response body if it came from cookie 
        # (It puts `req.session_id` or generated. Wait, let's check `api_server.py`)
        
        # In api_server.py: 
        # session_id = cookie_session_id or body_session_id or new
        # answer_json = run_pipeline(..., session_id=session_id)
        # return { ..., "session_id": session_id }
        
        data2 = r2.json()
        sid2_body = data2.get("session_id")
        
        print(f"Request 2: Returned Body SID = {sid2_body}")
        
        if sid1_cookie == sid2_body:
            print("SUCCESS: Session ID persisted via cookie!")
        else:
            print(f"FAIL: Session ID changed! Cookie: {sid1_cookie} vs Body: {sid2_body}")
            
    except Exception as e:
         print(f"Error Req 2: {e}")

if __name__ == "__main__":
    run_session_cookie_test()
