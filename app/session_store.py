"""
Session-based clinical state storage for conversation context memory.
Enables GeneGPT to remember clinical context across conversation turns.
"""
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
import threading


class SessionStore:
    """In-memory storage for clinical state across conversation turns."""
    
    def __init__(self, ttl_minutes: int = 60):
        """
        Initialize session store.
        
        Args:
            ttl_minutes: Time-to-live for sessions in minutes (default: 60)
        """
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._lock = threading.Lock()
    
    def get_clinical_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get clinical state for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Clinical state dict with default values if session doesn't exist
        """
        with self._lock:
            self._cleanup_expired()
            
            if session_id not in self._sessions:
                return self._create_default_state()
            
            # Update timestamp on access
            self._timestamps[session_id] = datetime.now()
            return self._sessions[session_id].copy()
    
    def update_clinical_state(self, session_id: str, updates: Dict[str, Any]) -> None:
        """
        Update clinical state for a session.
        
        Args:
            session_id: Unique session identifier
            updates: Dict of updates to merge into clinical state
        """
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = self._create_default_state()
            
            # Merge updates
            state = self._sessions[session_id]
            
            # Update simple fields
            for key in ["current_gene", "current_variant", "variant_classification", 
                       "test_context", "user_emotion"]:
                if key in updates and updates[key] is not None:
                    state[key] = updates[key]
            
            # Merge topics_discussed (set)
            if "topics_discussed" in updates:
                state["topics_discussed"].update(updates["topics_discussed"])
            
            # -----------------------------------------------------------
        # MEMORY DECAY & RELEVANCE UPDATES
        # -----------------------------------------------------------
        for key in ["recent_facts", "user_concerns"]:
            # 1. Normalize existing structure to dicts {"text": "...", "score": N}
            current_list = []
            for item in state[key]:
                if isinstance(item, str):
                    current_list.append({"text": item, "score": 5})
                elif isinstance(item, dict):
                    current_list.append(item)
            
            # 2. Decay logic: decrease score by 1 for all items
            decayed_list = []
            for item in current_list:
                item["score"] -= 1
                if item["score"] > 0:
                    decayed_list.append(item)
            
            # 3. Process new updates
            new_items_text = updates.get(key, [])
            if new_items_text:
                # SPECIAL COMMAND: Clear memory
                if "__CLEAR__" in new_items_text:
                    decayed_list = []
                else:
                    for text in new_items_text:
                        if not text: continue
                        # Check if exists (refresh score)
                        found = False
                        for existing in decayed_list:
                            if existing["text"].lower() == text.lower():
                                existing["score"] = 5
                                found = True
                                break
                        # If new, add with score 5
                        if not found:
                            decayed_list.append({"text": text, "score": 5})
            
            state[key] = decayed_list

        # Merge unresolved_questions (simple list)
        if "unresolved_questions" in updates:
            for q in updates["unresolved_questions"]:
                if q not in state["unresolved_questions"]:
                    state["unresolved_questions"].append(q)
            
            # Update timestamp
            self._timestamps[session_id] = datetime.now()
    
    def clear_session(self, session_id: str) -> None:
        """Clear a specific session."""
        with self._lock:
            self._sessions.pop(session_id, None)
            self._timestamps.pop(session_id, None)
    
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
    
    def _cleanup_expired(self) -> None:
        """Remove expired sessions (called internally)."""
        now = datetime.now()
        expired = [
            sid for sid, ts in self._timestamps.items()
            if now - ts > self._ttl
        ]
        for sid in expired:
            self._sessions.pop(sid, None)
            self._timestamps.pop(sid, None)


# Global session store instance
_session_store = SessionStore(ttl_minutes=60)


def get_session_store() -> SessionStore:
    """Get the global session store instance."""
    return _session_store
