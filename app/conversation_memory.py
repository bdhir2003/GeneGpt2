# conversation_memory.py
#
# Lightweight, in-session chat history for the GeneGPT2 CLI.
# ❗ This memory is temporary — it resets when the program restarts.
# It does NOT save to disk and does NOT mix with gene-answer memory.

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class ConversationMemory:
    """
    Simple rolling conversation buffer used only during a single CLI session.

    - Stores user and assistant messages in sequence.
    - Keeps the last N turns (each turn ≈ user + assistant).
    - Produces a compact text format for the LLM to understand context.
    """

    max_turns: int = 10                   # keep last 10 conversational turns
    messages: List[Dict[str, str]] = field(default_factory=list)

    def add_user_message(self, text: str) -> None:
        """Add user message to the buffer."""
        if not text:
            return
        self.messages.append({"role": "user", "content": text})
        self._trim()

    def add_assistant_message(self, text: str) -> None:
        """Add assistant message to the buffer."""
        if not text:
            return
        self.messages.append({"role": "assistant", "content": text})
        self._trim()

    def _trim(self) -> None:
        """
        Keep only MOST RECENT messages.
        max_turns = 10 ⇒ keep ~20 messages (10 user + 10 assistant).
        """
        max_msgs = self.max_turns * 2
        if len(self.messages) > max_msgs:
            self.messages = self.messages[-max_msgs:]

    def as_text(self) -> str:
        """
        Convert the stored history into a readable transcript for the LLM.

        Example:
            User: hi
            GeneGPT: hello, how can I help?
            User: what is BRCA1?
        """
        if not self.messages:
            return "No prior conversation. Answer this as the first question."

        lines: List[str] = []
        for msg in self.messages:
            role = msg.get("role", "user")
            prefix = "User" if role == "user" else "GeneGPT"

            content = msg.get("content", "")

            # Avoid feeding extremely long messages back to the model
            if len(content) > 500:
                content = content[:500] + " ..."

            lines.append(f"{prefix}: {content}")

        return "\n".join(lines)
