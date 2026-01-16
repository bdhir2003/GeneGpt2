import sys
import os
from unittest.mock import MagicMock, patch

# Ensure app is in path
sys.path.append(os.path.join(os.getcwd(), 'app'))

from app.pipeline import run_genegpt_pipeline

def test_v2_pipeline():
    print("=== Testing GeneGPT V2 Pipeline ===")

    # Mock the LLM controller to avoid needing real API key
    with patch('app.llm_controller.classify_question_with_llm') as mock_classify:

        # TEST 1: General Gene Question
        print("\n--- Test 1: Gene Question (BRCA1) ---")
        mock_classify.return_value = {
            "gene": "BRCA1",
            "question_type": "risk",
            "target": "self",
            "needs_clarification": False,
            "confidence": 0.9
        }
        
        # We also need to mock the evidence fetchers to avoid real network calls if we want speed,
        # but let's allow them if we want real integration test. 
        # For now, let's assume network is fine or we just care about logic flow.
        # Actually, without network, this might fail. Let's patch get_omim_summary etc.
        
        with patch('app.pipeline.get_omim_summary') as mock_omim, \
             patch('app.pipeline.get_ncbi_summary') as mock_ncbi, \
             patch('app.pipeline.get_pubmed_summary') as mock_pubmed, \
             patch('app.pipeline.get_genereviews_summary') as mock_gr, \
             patch('app.pipeline.get_gnomad_summary') as mock_gnomad:
             
            mock_omim.return_value = {"used": True, "phenotypes": [{"name": "Breast-ovarian cancer"}]}
            mock_ncbi.return_value = {"used": True, "full_name": "BRCA1 DNA Repair Associated"}
            mock_pubmed.return_value = {"used": True, "papers": []}
            mock_gr.return_value = {"used": True}
            mock_gnomad.return_value = {"used": True}

            result = run_genegpt_pipeline("Is BRCA1 dangerous?")
            
            print(f"Intent detected: {result['intent']}")
            # In normal flow, result IS the answer_json
            print(f"Evidence keys: {result['evidence'].keys()}")
            
            assert result['intent']['intent'] == 'risk_question'
            assert result['evidence']['omim']['used'] == True

        # TEST 2: Clarification Needed
        print("\n--- Test 2: Vague Question (Clarification) ---")
        mock_classify.return_value = {
            "gene": None,
            "question_type": "unknown",
            "needs_clarification": True,
            "reason": "No gene specified"
        }

        result = run_genegpt_pipeline("Is it bad?")
        print(f"Answer: {result['answer']}")
        print(f"Answer: {result['answer']}")
        assert "ensure" in result['answer']

        # TEST 3: No Evidence Safety Gate
        print("\n--- Test 3: Medical Question with NO Evidence ---")
        mock_classify.return_value = {
            "gene": "FAKE123",
            "question_type": "gene",
            "needs_clarification": False
        }
        
        with patch('app.pipeline.get_omim_summary') as mock_omim, \
             patch('app.pipeline.get_ncbi_summary') as mock_ncbi, \
             patch('app.pipeline.get_pubmed_summary') as mock_pubmed, \
             patch('app.pipeline.get_genereviews_summary') as mock_gr, \
             patch('app.pipeline.get_gnomad_summary') as mock_gnomad:
             
            # All return unused/empty
            mock_omim.return_value = {"used": False}
            mock_ncbi.return_value = {"used": False}
            mock_pubmed.return_value = {"used": False}
            mock_gr.return_value = {"used": False}
            mock_gnomad.return_value = {"used": False}

            result = run_genegpt_pipeline("What is FAKE123?")
            print(f"Answer: {result['answer']}")
            assert "could not find specific genetic evidence" in result['answer']

    print("\n✅ All V2 Logic Tests Passed!")

if __name__ == "__main__":
    test_v2_pipeline()
