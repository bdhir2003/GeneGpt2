
# GeneGPT2 Development Walkthrough

## 🚀 Phase 1: Infrastructure & Deployment ("Going Live")
The first major milestone was ensuring the system could run reliably in a production environment (Render) rather than just locally.

### 1. **Persistent Memory System**
*   **Before:** Conversation memory (which gene you are talking about) was stored in Python's variable memory (RAM). If the server restarted, the user's session was lost.
*   **Action:** Replaced the in-memory store with a **SQLite Database (`sessions.db`)**.
*   **Key Code:** `app/session_store.py`
    *   Added `get_clinical_state` and `update_clinical_state` backed by SQL queries.
    *   Implemented auto-cleanup for old/stale sessions.

### 2. **Session Continuity**
*   **Before:** Reloading the page created a new "user" every time.
*   **Action:**
    *   **Frontend:** Modified `api.ts` to generate a unique `UUID` and store it in the browser's `localStorage`.
    *   **Backend:** Updated `api_server.py` to prioritize this incoming `session_id`, ensuring a seamless conversation even if the user refreshes the page.

### 3. **Connectivity (CORS & Security)**
*   **Action:** Configured FastAPI to strictly allow requests from your specific deployed frontend (`genegpt2-11.onrender.com`) and localhost, preventing unauthorized access while enabling cookies/credentials.

---

## 🧠 Phase 2: Pipeline Intelligence ("Fixing Logic")
Once live, we focused on "Context Contamination" — ensuring the AI doesn't confuse one patient's gene with another.

### 1. **Context Transition Guard**
*   **Problem:** Asking "What about PTEN?" after discussing "BRCA1" sometimes resulted in answers mixing both genes.
*   **Fix:** Implemented a "Guard" in `app/pipeline.py`:
    *   Detects if a **new gene symbol** is present.
    *   If found, it **wipes the previous session context** before processing, unless the user explicitly links them (e.g., "compare with...").
    *   Also clears context for broad questions like "What is DNA?".

### 2. **Anti-Hallucination Rules**
*   **Problem:** The AI would sometimes treat words like "DANGEROUS", "RISK", or "HELP" as if they were gene names.
*   **Fix:**
    *   Added a **Strict Blocklist** for generic terms.
    *   Enforced a Regex Rule: A gene symbol must look like a gene (e.g., alphanumeric, specific length) to be accepted.

### 3. **The "Clarification Gate"**
*   **Problem:** Asking "Is it dangerous?" *without* mentioning a gene caused errors or guesses.
*   **Fix:** Added logic to catch these ambiguous questions. If no gene is in the session, the system now stops and asks: *"I can help, but which gene are you referring to?"*

---

## 🩺 Phase 3: Clinical Persona ("Counselor Mode")
We refined how the AI speaks to users, shifting from "Raw Data" to "Empathetic Counselor".

### 1. **Counselor Mode Injection**
*   **Action:** modified `llm_explainer_openai.py` to inject a specialized system prompt when sensitive topics arise.
*   **Triggers:** Anxiety phrases ("scared", "worry"), High-Risk genes (BRCA1, TP53), or Variants of Uncertain Significance (VUS).
*   **Result:** The AI now prioritizes empathy, standardizes medical disclaimers, and avoids alarming language.

---

## 📱 Phase 4: Frontend UI/UX ("Mobile Polish")
Finally, we ensured the application feels like a native app on mobile devices.

### 1. **Mobile Responsiveness**
*   **Action:** Rewrote `page.tsx` padding/layout logic for screens `< 768px`.
*   **Result:**
    *   **Sidebars:** Now behave as standard "Slide-over" menus (absolute positioning) with Close buttons, instead of crushing the main chat.
    *   **Chat Area:** Takes full width on mobile.

### 2. **Input Bar Stability**
*   **Problem:** The keyboard pushed the header off-screen or hid the input bar.
*   **Fix:**
    *   Locked the Viewport Height (`100dvh`) in `globals.css` to prevent "jumping".
    *   Fixed the Input Bar to `bottom: 0` with safe-area padding for iOS (`pb-env(safe-area-inset-bottom)`).
    *   Added a visible **Send Button** so mobile users don't rely on the "Enter" key.

### 3. **Visual Accessibility**
*   **Fix:** Forced text color to pure white (`#ffffff`) in Dark Mode to solve the "light blue/low contrast" issue complained about on lab monitors.

---

## ✅ Current System State
*   **Backend:** Stable, Persistent (SQLite), Context-Aware, Hallucination-Resistant.
*   **Frontend:** Mobile-Optimized, Persistent Sessions, High Contrast.
*   **Deployment:** Live on Render (Main Branch).
