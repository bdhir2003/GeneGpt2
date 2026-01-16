# GeneGPT V2: Complete Technical Walkthrough & Pipeline Review

**Date:** January 16, 2026  
**Version:** V2.0 ("The Cortex Upgrade")  
**Repository:** [bdhir2003/GeneGpt2](https://github.com/bdhir2003/GeneGpt2)

---

## 1. System Overview
GeneGPT is an **Advanced Agentic Genetic Counselor**. Unlike standard chatbots that hallucinate medical facts, GeneGPT uses a **Retreival-Augmented Generation (RAG)** pipeline designed for safety, accuracy, and empathy. It strictly separates "Reasoning" (deciding what to do) from "Knowledge" (verified external databases), preventing the AI from making up genetic data.

---

## 2. High-Level Architecture
The system consists of two main components:

1.  **Frontend (The Interface):** A Next.js/React application (`genegpt2-frontend`) designed for accessibility and trust.
2.  **Backend (The Brain):** A FastAPI Python server (`app/`) that runs the intelligence pipeline.

---

## 3. The Full Pipeline: Step-by-Step

When a user asks a question (e.g., *"Is my BRCA1 variant dangerous?"*), the following chain of events occurs:

### **Step 1: Receipt & Session Management**
*   **File:** `app/api_server.py`
*   **Action:** The `/ask` endpoint receives the question.
*   **Session:** It checks for a `session_id`. If none exists, it creates one to track conversation history (Context).

### **Step 2: Question Understanding "The Cortex" (NEW in V2)**
*   **File:** `app/llm_controller.py`
*   **Action:** Before looking for data, we send the raw question to a specialized LLM Step.
*   **Goal:** Classify the **Intent**, **Gene**, and **Type**.
*   **Strict Output:** It returns a JSON object like:
    ```json
    {
      "gene": "BRCA1",
      "question_type": "risk",
      "needs_clarification": false
    }
    ```
*   **The Clarification Gate:** If the user asks *"Is it bad?"* (with no context), this step returns `needs_clarification: true`. The pipeline **stops here** and asks the user: *"Which gene are you referring to?"*

### **Step 3: Strategic Evidence Planning**
*   **File:** `app/pipeline.py`
*   **Action:** Based on the `question_type`, the system decides **which databases to call**.
    *   **"Risk" Question:** Fetches OMIM (Phenotypes), GeneReviews (Clinical Guidelines), and PubMed (Literature).
    *   **"Variant" Question:** Prioritizes ClinVar (Classifications) and gnomAD (Population Frequency).
    *   **"Education" Question:** Fetches only basic NCBI/OMIM definitions (Relevance Optimization).

### **Step 4: Live Evidence Retrieval**
*   **Files:** `app/*_client.py` (omim, ncbi, clinvar, etc.)
*   **Action:** The system connects to trusted external APIs in real-time.
*   **Data:** It pulls the latest classifications, phenotypes, and papers.
    *   *Note: This data is formatted into a strict "Evidence JSON" object.*

### **Step 5: The "No Evidence" Safety Gate (NEW in V2)**
*   **File:** `app/pipeline.py`
*   **Action:** The system checks if **Any** valid data was returned for a medical question.
*   **Safety Rule:** If `question_type` is medical (e.g., "variant") but **ClinVar/OMIM returned nothing**, the pipeline **ABORTS**.
*   **Why?** To prevent the LLM from hallucinating an answer when it has no real data.
*   **Output:** *"I verified the medical databases but could not find specific evidence for your query."*

### **Step 6: The Genetic Counselor Persona (Synthesis)**
*   **File:** `app/llm_explainer_openai.py`
*   **Action:** The structured Evidence JSON + User Question are sent to GPT-4o.
*   **System Prompt:** "You are a coordinated memory-aware genetic counselor."
*   **Critical Guardrails:**
    1.  **Evidence Boundaries:** "You must ONLY use the provided JSON evidence. Do not use internal training data for facts."
    2.  **No Diagnosis:** "Never diagnose. Always refer to a clinician."
    3.  **Empathetic Tone:** "Speak clearly, calmly, and supportively."

### **Step 7: Delivery & Trust Metrics**
*   **File:** `app/api_server.py` & Frontend Components
*   **Action:** The backend calculates a **Trust Score** and **Certainty Score** based on the quality of sources used (e.g., ClinVar > PubMed > Nothing).
*   **Frontend Display:**
    *   **Chat Bubble:** Displays the empathetic response (White Text on Dark Background).
    *   **Evidence Panel:** Shows the raw data source (e.g., "ClinVar: Pathogenic").
    *   **Trust Meter:** Visualizes how reliable the answer is.

---

## 4. Key V2 Upgrades Summary

| Feature | Before V2 | **After V2 (Current)** |
| :--- | :--- | :--- |
| **Intent Detection** | Regex (Simple patterns) | **LLM Cortex** (Deep understanding of context) |
| **Ambiguity** | Often guessed or failed | **Clarification Gate** (Asks user to clarify) |
| **Evidence Fetching** | Fetched everything (Slow) | **Selective Planning** (Only what's needed) |
| **No Data Handling** | LLM might hallucinate | **Safety Gate** (Blocks response if no data) |
| **UI Visibility** | Hard to read on some screens | **High Contrast** (Forced White Text) |

---

## 5. Deployment
*   **Codebase:** All code is pushed to `main`.
*   **Tests:** `test_pipeline_v2.py` validates the Logic Gates.
*   **Status:** Ready for production use.
