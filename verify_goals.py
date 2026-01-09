import os
import sys
import time

# Ensure we can import from app
sys.path.append(os.path.join(os.getcwd()))

from app.pipeline import run_genegpt_pipeline
from app.intent_classifier import classify_intent

def test_query(query, expected_intent_type, expected_evidence_key):
    print(f"\n--- Testing: '{query}' ---")
    
    # 1. Check raw intent
    intent = classify_intent(query)
    print(f"  [Intent Classifier] Detected: {intent.get('intent')} (Expected: {expected_intent_type})")
    
    # 2. Run full pipeline
    try:
        result = run_genegpt_pipeline(query)
        final_type = result.get("question_type")
        evidence = result.get("evidence", {})
        
        print(f"  [Pipeline] Final Type: {final_type}")
        
        # Check evidence
        sources = []
        if evidence.get("omim", {}).get("used"): sources.append("OMIM")
        if evidence.get("ncbi", {}).get("used"): sources.append("NCBI")
        if evidence.get("clinvar", {}).get("used"): sources.append("ClinVar")
        if evidence.get("pubmed", {}).get("used"): sources.append("PubMed")
        
        print(f"  [Evidence] Sources Used: {sources}")
        
        # Validation
        intent_match = (intent.get("intent") == expected_intent_type) or (expected_intent_type == "ANY_RELEVANT")
        # Note: mapping might vary (e.g. disease -> gene type in pipeline, but checking classification here)
        
        has_evidence = False
        if expected_evidence_key == "pubmed":
             has_evidence = evidence.get("pubmed", {}).get("used")
        elif expected_evidence_key == "variant_sources":
             has_evidence = evidence.get("clinvar", {}).get("used") or evidence.get("omim", {}).get("used")
        elif expected_evidence_key == "gene_sources":
             has_evidence = evidence.get("omim", {}).get("used") or evidence.get("ncbi", {}).get("used")
             
        if has_evidence:
            print("  ✅ Evidence check passed")
        else:
            print("  ❌ Evidence check FAILED")
            
    except Exception as e:
        print(f"  ❌ Pipeline CRASHED: {e}")

    time.sleep(2)  # Rate limit protection

if __name__ == "__main__":
    print("Running Goal Verification tests...\n")
    
    # A) "tell me about heart diseases" -> broad_science / disease
    test_query("tell me about heart diseases", "disease_question", "pubmed")
    
    # B) "I have been told I have a BRCA1 mutation. what should I do?" -> guidance
    test_query("I have been told I have a BRCA1 mutation. what should I do?", "guidance_question", "gene_sources")
    
    # C) "BRCA1 c.68_69delAG. is this mutation serious?" -> variant / risk
    test_query("BRCA1 c.68_69delAG. is this mutation serious?", "variant_question", "variant_sources")
    
    # D) "what is diabetes?" -> broad_science / disease
    test_query("what is diabetes?", "disease_question", "pubmed")
