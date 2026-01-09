# cli.py — simple terminal interface for GeneGPT2

from pipeline import run_genegpt_pipeline
from llm_explainer_openai import explain_with_openai   # ✅ uses OpenAI for simple English
from conversation_memory import ConversationMemory      # ✅ chat-style, in-session memory only


def main():
    print("🔬 GeneGPT2 — Terminal Demo (with temporary memory)")
    print("Ask about a gene or variant.")
    print("Example: BRCA1 c.68_69delAG. Is this mutation serious?")
    print("Type 'quit' or 'exit' to stop.\n")

    # 🧠 Short-term chat memory for this CLI session (not saved to disk)
    convo = ConversationMemory(max_turns=10)

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye 👋")
            break

        if not question:
            continue

        if question.lower() in {"quit", "exit"}:
            print("Goodbye 👋")
            break

        # 1️⃣ Add the user's message to the conversation buffer
        convo.add_user_message(question)

        print("\n[Running GeneGPT2 pipeline...]\n")

        try:
            # STEP 1 → get evidence JSON (no explanation, just structured info)
            answer_json = run_genegpt_pipeline(question)

            # ❌ No permanent memory right now.
            # We are NOT calling save_answer_to_memory here.
            # When we deploy on a real server, we can add that back.

            # STEP 2 → convert JSON to simple English using OpenAI,
            # now with the conversation history included.
            conversation_context = convo.as_text()
            explanation = explain_with_openai(
                answer_json,
                conversation_context=conversation_context,
            )

        except Exception as e:
            print(f"❌ Error running GeneGPT2: {e}")
            print("\n" + "=" * 80 + "\n")
            # Don't crash the whole app; just continue to next question
            continue

        # Optional: keep this for debugging the raw structured output
        print("🧱 DEBUG — Raw Answer JSON:")
        print(answer_json)

        print("\n📝 Final Explanation (simple English):\n")
        print(explanation)

        # 2️⃣ Add assistant reply to conversation memory AFTER printing
        convo.add_assistant_message(explanation)

        print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
