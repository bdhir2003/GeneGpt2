"""
Session-based clinical state storage for conversation context memory.
Enables GeneGPT to remember clinical context across conversation turns.
Uses SQLite for persistence.
"""
from typing import Dict, Any, Optional, Set, List
from datetime import datetime, timedelta
import threading
import sqlite3
import json
import os

DB_PATH = "sessions.db"

class SessionStore:
    """SQLite-backed storage for clinical state across conversation turns."""
    
    def __init__(self, ttl_minutes: int = 60000): # Increased default TTL
        """
        Initialize persistent session store.
        """
        self._ttl = timedelta(minutes=ttl_minutes)
        self._lock = threading.Lock()
        
        # Initialize DB
        self._init_db()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
            
    def _get_connection(self):
        return sqlite3.connect(DB_PATH, check_same_thread=False)
            
    def get_clinical_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get clinical state for a session.
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Cleanup expired (lazy cleanup)
            expires_before = datetime.now() - self._ttl
            cursor.execute("DELETE FROM sessions WHERE updated_at < ?", (expires_before,))
            conn.commit()
            
            cursor.execute("SELECT data FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                try:
                    state = json.loads(row[0])
                    # Deserialize 'topics_discussed' from list to set
                    if "topics_discussed" in state and isinstance(state["topics_discussed"], list):
                        state["topics_discussed"] = set(state["topics_discussed"])
                    return state
                except json.JSONDecodeError:
                    return self._create_default_state()
            else:
                return self._create_default_state()
    
    def update_clinical_state(self, session_id: str, updates: Dict[str, Any]) -> None:
        """
        Update clinical state for a session.
        """
        # Load current state first (to apply merge logic)
        state = self.get_clinical_state(session_id)
        
        with self._lock:
            # -----------------------------------------------------------
            # MERGE LOGIC
            # -----------------------------------------------------------
            
            # Update simple fields
            for key in ["current_gene", "current_variant", "variant_classification", 
                       "test_context", "user_emotion"]:
                if key in updates:
                    state[key] = updates[key]
            
            # Merge topics_discussed (set)
            if "topics_discussed" in updates:
                # Ensure current state has a set
                if "topics_discussed" not in state or not isinstance(state["topics_discussed"], set):
                    state["topics_discussed"] = set()
                
                # updates["topics_discussed"] might be list or set
                new_topics = updates["topics_discussed"]
                if isinstance(new_topics, list):
                    state["topics_discussed"].update(set(new_topics))
                elif isinstance(new_topics, set):
                    state["topics_discussed"].update(new_topics)

            # MEMORY DECAY & RELEVANCE UPDATES
            for key in ["recent_facts", "user_concerns"]:
                if key not in state: state[key] = []
                
                # 1. Normalize existing structure
                current_list = []
                for item in state[key]:
                    if isinstance(item, str):
                        current_list.append({"text": item, "score": 5})
                    elif isinstance(item, dict):
                        current_list.append(item)
                
                # 2. Decay logic
                decayed_list = []
                for item in current_list:
                    item["score"] -= 1
                    if item["score"] > 0:
                        decayed_list.append(item)
                
                # 3. Process new updates
                new_items_text = updates.get(key, [])
                if new_items_text:
                    if "__CLEAR__" in new_items_text:
                        decayed_list = []
                    else:
                        for text in new_items_text:
                            if not text: continue
                            found = False
                            for existing in decayed_list:
                                if existing["text"].lower() == text.lower():
                                    existing["score"] = 5
                                    found = True
                                    break
                            if not found:
                                decayed_list.append({"text": text, "score": 5})
                
                state[key] = decayed_list

            # Merge unresolved_questions
            if "unresolved_questions" in updates:
                if "unresolved_questions" not in state: state["unresolved_questions"] = []
                for q in updates["unresolved_questions"]:
                    if q not in state["unresolved_questions"]:
                        state["unresolved_questions"].append(q)

            # -----------------------------------------------------------
            # SAVE TO DB
            # -----------------------------------------------------------
            
            # Prepare for JSON serialization (sets -> lists)
            save_state = state.copy()
            if isinstance(save_state.get("topics_discussed"), set):
                save_state["topics_discussed"] = list(save_state["topics_discussed"])
            
            json_data = json.dumps(save_state)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (session_id, data, updated_at) 
                VALUES (?, ?, ?)
            """, (session_id, json_data, datetime.now()))
            conn.commit()
            conn.close()

    def clear_session(self, session_id: str) -> None:
        """Clear a specific session."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()
    
    def _create_default_state(self) -> Dict[str, Any]:
        """Create default clinical state."""
        return {
            "current_gene": None,
            "current_variant": None,
            "variant_classification": "unknown",
            "test_context": "unknown",
            "topics_discussed": set(),
            "user_emotion": None,
            "unresolved_questions": [],
            "recent_facts": [],
            "user_concerns": []
        }

# Global session store instance
_session_store = SessionStore()

def get_session_store() -> SessionStore:
    """Get the global session store instance."""
    return _session_store
