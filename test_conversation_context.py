"""
Test conversation context memory with follow-up questions.
"""
import os
import sys
import uuid

sys.path.append(os.path.join(os.getcwd()))

from app.pipeline import run_genegpt_pipeline
from app.llm_explainer_openai import explain_with_openai

def test_conversation_context():
    """Test conversation continuity across turns."""
    
    # Generate a session ID for this conversation
    session_id = str(uuid.uuid4())
    print(f"Session ID: {session_id}\n")
    
    # Test 1: PTEN mutation → screening follow-up
    print("="*80)
    print("TEST 1: PTEN Mutation → Screening Follow-Up")
    print("="*80)
    
    # Turn 1
    print("\n--- Turn 1 ---")
    query1 = "I was told I have a PTEN mutation. What should I do?"
    print(f"Query: {query1}")
    
    result1 = run_genegpt_pipeline(query1, session_id=session_id)
    clinical_state1 = result1.get("clinical_state", {})
    print(f"\nClinical State After Turn 1:")
    print(f"  - current_gene: {clinical_state1.get('current_gene')}")
    print(f"  - test_context: {clinical_state1.get('test_context')}")
    print(f"  - topics_discussed: {clinical_state1.get('topics_discussed')}")
    
    # Turn 2
    print("\n--- Turn 2 ---")
    query2 = "At what point do doctors start extra screening?"
    print(f"Query: {query2}")
    
    result2 = run_genegpt_pipeline(query2, session_id=session_id)
    
    # Get LLM explanation
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        explanation2 = explain_with_openai(result2)
        print(f"\nResponse:")
        print(explanation2[:500] + "..." if len(explanation2) > 500 else explanation2)
        
        # Check if PTEN context was maintained
        if "PTEN" in explanation2:
            print("\n✅ PTEN context maintained in follow-up!")
        else:
            print("\n❌ PTEN context lost in follow-up")
    
    # Test 2: PTEN VUS → inheritance follow-up
    print("\n\n" + "="*80)
    print("TEST 2: PTEN VUS → Inheritance Follow-Up")
    print("="*80)
    
    # New session for test 2
    session_id2 = str(uuid.uuid4())
    
    # Turn 1
    print("\n--- Turn 1 ---")
    query3 = "My PTEN variant is a VUS."
    print(f"Query: {query3}")
    
    result3 = run_genegpt_pipeline(query3, session_id=session_id2)
    clinical_state3 = result3.get("clinical_state", {})
    print(f"\nClinical State After Turn 1:")
    print(f"  - current_gene: {clinical_state3.get('current_gene')}")
    print(f"  - variant_classification: {clinical_state3.get('variant_classification')}")
    
    # Turn 2
    print("\n--- Turn 2 ---")
    query4 = "If this is inherited, does that mean my children will definitely have problems?"
    print(f"Query: {query4}")
    
    result4 = run_genegpt_pipeline(query4, session_id=session_id2)
    
    if api_key:
        explanation4 = explain_with_openai(result4)
        print(f"\nResponse:")
        print(explanation4[:500] + "..." if len(explanation4) > 500 else explanation4)
        
        # Check if PTEN + VUS context was maintained
        if "PTEN" in explanation4 and ("VUS" in explanation4 or "uncertain" in explanation4.lower()):
            print("\n✅ PTEN + VUS context maintained in follow-up!")
        else:
            print("\n❌ PTEN + VUS context lost in follow-up")

if __name__ == "__main__":
    test_conversation_context()
