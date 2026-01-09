import os
import sys
import time

# Ensure we can import from app
sys.path.append(os.path.join(os.getcwd()))

from app.pipeline import run_genegpt_pipeline
from app.llm_explainer_openai import explain_with_openai

def test_edge_case(query, test_name, expected_behaviors):
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"Query: {query}")
    print(f"{'='*80}\n")
    
    try:
        # Run pipeline
        result = run_genegpt_pipeline(query)
        
        # Get LLM explanation
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if api_key:
            explanation = explain_with_openai(result)
            print("RESPONSE:")
            print(explanation)
            print(f"\n{'-'*80}")
            
            # Check expected behaviors
            print("VALIDATION:")
            for behavior in expected_behaviors:
                if behavior.lower() in explanation.lower():
                    print(f"  ✅ Contains: '{behavior}'")
                else:
                    print(f"  ⚠️  Missing: '{behavior}'")
        else:
            print("⚠️  No OpenAI API key")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    time.sleep(2)  # Rate limit protection

if __name__ == "__main__":
    print("Testing Edge Case Safety and VUS Handling\n")
    
    # Test A: VUS case
    test_edge_case(
        "My PTEN variant is a VUS. What does that mean?",
        "A) VUS (Variant of Uncertain Significance)",
        [
            "VUS means",
            "not yet clearly understood",
            "should NOT be treated as pathogenic",
            "periodic re-evaluation"
        ]
    )
    
    # Test B: Somatic-only case
    test_edge_case(
        "PTEN mutation found only in tumor. Should my family worry?",
        "B) Somatic-Only Mutation",
        [
            "specific to the tumor",
            "not inherited",
            "does not affect family members"
        ]
    )
    
    # Test C: No family history case
    test_edge_case(
        "I have a PTEN mutation but no family history.",
        "C) PTEN Mutation - No Family History",
        [
            "germline",
            "somatic",
            "information needed"
        ]
    )
