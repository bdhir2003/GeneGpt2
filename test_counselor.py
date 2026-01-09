import os
import sys
import time

# Ensure we can import from app
sys.path.append(os.path.join(os.getcwd()))

from app.pipeline import run_genegpt_pipeline
from app.llm_explainer_openai import explain_with_openai

def test_counselor_response(query, test_name):
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
            
            # Show context flags
            context = result.get("intent", {}).get("context", {})
            print(f"Context Flags:")
            print(f"  - New diagnosis: {context.get('implies_new_diagnosis', False)}")
            print(f"  - Anxious: {context.get('user_likely_anxious', False)}")
            print(f"  - Needs next steps: {context.get('needs_next_steps', False)}")
            
            # Show evidence sources
            evidence = result.get("evidence", {})
            sources = []
            if evidence.get("omim", {}).get("used"): sources.append("OMIM")
            if evidence.get("ncbi", {}).get("used"): sources.append("NCBI")
            if evidence.get("clinvar", {}).get("used"): sources.append("ClinVar")
            if evidence.get("pubmed", {}).get("used"): sources.append("PubMed")
            print(f"  - Evidence sources: {', '.join(sources) if sources else 'None'}")
        else:
            print("⚠️  No OpenAI API key - showing raw pipeline output only")
            print(result)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    time.sleep(2)  # Rate limit protection

if __name__ == "__main__":
    print("Testing Genetic Counselor Response Style\n")
    
    # Test A: PTEN mutation with anxiety/next steps
    test_counselor_response(
        "I was told I have a PTEN mutation. What should I do?",
        "A) PTEN Mutation - Guidance Request"
    )
    
    # Test B: BRCA1 variant - serious concern
    test_counselor_response(
        "BRCA1 c.68_69delAG — is this serious?",
        "B) BRCA1 Variant - Risk Assessment"
    )
    
    # Test C: General disease question
    test_counselor_response(
        "Tell me about heart diseases",
        "C) Heart Diseases - General Query"
    )
    
    # Test D: Diabetes question
    test_counselor_response(
        "What is diabetes?",
        "D) Diabetes - General Query"
    )
