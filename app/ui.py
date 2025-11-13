# ui.py – Streamlit front-end for GeneGPT v1

import streamlit as st
from pipeline import run_genegpt_pipeline  # adjust path if your ui.py is inside app/


def set_example(text: str):
    st.session_state["user_question"] = text


def main():
    st.set_page_config(
        page_title="GeneGPT v1 – Explain My Gene or Variant",
        layout="wide",
        page_icon="🧬",
    )

    # ----- Sidebar -----
    with st.sidebar:
        st.title("🧬 GeneGPT v1")
        st.markdown(
            """
Prototype tool for **explaining genetic test results**.

**Data sources (v1):**
- OMIM (gene → disease)
- NCBI Gene (gene summary & metadata)
- ClinVar (variant classification – mock/real mix)

> ⚠️ This is a research prototype, **not a medical device**.  
> Always discuss results with a qualified healthcare professional.
"""
        )

    # ----- Main title -----
    st.markdown("## GeneGPT – Explain My Gene or Variant")

    st.markdown(
        """
Type your question in **natural language**.

**Examples:**
- `BRCA1 c.68_69delAG. Is this mutation serious?`
- `What does the BRCA1 gene do and what diseases is it linked to?`
- `I have a BRCA1 variant. What kind of risk does it carry?`
"""
    )

    # ----- Quick example buttons -----
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("BRCA1 c.68_69delAG. Is this mutation serious?"):
            set_example("BRCA1 c.68_69delAG. Is this mutation serious?")
    with col2:
        if st.button("What conditions are associated with the BRCA1 gene?"):
            set_example("What conditions are associated with the BRCA1 gene?")
    with col3:
        if st.button("Explain what the BRCA1 gene normally does."):
            set_example("Explain what the BRCA1 gene normally does.")

    # ----- User input -----
    user_question = st.text_area(
        "Enter your question here:",
        key="user_question",
        height=80,
    )

    run_col, _ = st.columns([1, 5])
    with run_col:
        run_clicked = st.button("▶ Run GeneGPT")

    if run_clicked and user_question.strip():
        with st.spinner("Running GeneGPT pipeline..."):
            try:
                answer_json, explanation_text = run_genegpt_pipeline(user_question.strip())
            except Exception as e:
                st.error(f"Something went wrong in the backend: {e}")
                return

        # ----- Explanation block -----
        st.markdown("### 📝 Explanation")
        st.write(explanation_text)

        # ----- Technical details (JSON) -----
        with st.expander("🔍 Technical details (JSON view)", expanded=False):
            st.markdown(
                """
This is the **structured answer JSON** that GeneGPT built before
asking the language model to explain it.  
It includes gene IDs, ClinVar classification, OMIM diseases, and NCBI Gene summary.
"""
            )
            st.json(answer_json)


if __name__ == "__main__":
    main()
