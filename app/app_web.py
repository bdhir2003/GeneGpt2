import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from pipeline import run_genegpt_pipeline
from llm_explainer_openai import explain_with_openai
from name_normalizer import normalize_gene_name
from conversation_memory import ConversationMemory   # ✅ in-session chat memory


st.set_page_config(
    page_title="GeneGPT2 — Evidence-based Genomic Helper",
    layout="wide",
)

# -------------------------------------------------------------------
# Session state setup: temporary memory (only for this browser session)
# -------------------------------------------------------------------
if "messages" not in st.session_state:
    # Chat history: list of {"role": "user"/"assistant", "content": str}
    st.session_state["messages"] = []

if "answers" not in st.session_state:
    # For each Q&A we store: {"question": str, "answer_json": dict}
    st.session_state["answers"] = []

if "convo" not in st.session_state:
    # 🧠 Temporary conversation memory (like CLI), not saved to disk
    st.session_state["convo"] = ConversationMemory(max_turns=10)

convo: ConversationMemory = st.session_state["convo"]

# -------------------------------------------------------------------
# Sidebar: Evidence / Debug view for this session
# -------------------------------------------------------------------
with st.sidebar:
    st.title("🧪 GeneGPT2 – Evidence View")

    if st.session_state["answers"]:
        # Let user pick which past question to inspect
        questions = [a["question"] for a in st.session_state["answers"]]
        selected_index = st.selectbox(
            "Select a question to inspect:",
            options=list(range(len(questions))),
            format_func=lambda i: questions[i][:60] + ("..." if len(questions[i]) > 60 else ""),
        )
        selected_answer = st.session_state["answers"][selected_index]
        answer_json = selected_answer["answer_json"]

        st.markdown("### 🧱 Raw Answer JSON")
        st.json(answer_json)

        evidence = answer_json.get("evidence", {}) or {}
        omim = evidence.get("omim") or {}
        ncbi = evidence.get("ncbi") or {}
        clinvar = evidence.get("clinvar") or {}
        pubmed = evidence.get("pubmed") or {}

        st.markdown("### 📚 Evidence by Source")

        with st.expander("OMIM"):
            st.json(omim)
            link = omim.get("link")
            if link:
                st.markdown(f"[Open OMIM entry]({link})")

        with st.expander("NCBI Gene"):
            st.json(ncbi)
            link = ncbi.get("link")
            if link:
                st.markdown(f"[Open NCBI Gene]({link})")

        with st.expander("ClinVar"):
            st.json(clinvar)
            link = clinvar.get("link")
            if link:
                st.markdown(f"[Open ClinVar]({link})")

        with st.expander("PubMed"):
            st.json(pubmed)
            link = pubmed.get("link")
            if link:
                st.markdown(f"[Open PubMed]({link})")

    else:
        st.info("Ask a question to see evidence and JSON here.")


# -------------------------------------------------------------------
# Main page: Chat-style interface with temporary memory
# -------------------------------------------------------------------
st.title("🧬 GeneGPT2 – Evidence-based Genomic Helper")

st.markdown(
    "Ask a question about a gene or variant, e.g.: "
    "`BRCA1 c.68_69delAG. Is this mutation serious?`\n\n"
    "This app always fetches **evidence** from OMIM, NCBI Gene, PubMed, and ClinVar. "
    "It remembers the conversation **temporarily** while this page is open, "
    "to make the answers more contextual."
)

# Show chat history
for msg in st.session_state["messages"]:
    # ❌ avatar=\"\" removed (this caused the error)
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input (Enter to send)
user_input = st.chat_input("Type your question about genes/variants (or say hi)...")

if user_input:
    # 1) Add user message to history (for UI)
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # 1b) Also add to conversation memory (for LLM context)
    convo.add_user_message(user_input)

    # 2) Normalize very simple one-token gene queries (e.g., "tp53" -> "TP53")
    clean_question = user_input.strip()
    if clean_question and " " not in clean_question:
        clean_question = normalize_gene_name(clean_question)

    # 3) Call the GeneGPT2 pipeline + explainer (with conversation context)
    with st.chat_message("assistant"):
        with st.spinner("Running GeneGPT2 pipeline..."):
            try:
                answer_json = run_genegpt_pipeline(clean_question)

                # Build conversation context text from recent history
                conversation_context = convo.as_text()

                explanation = explain_with_openai(
                    answer_json,
                    conversation_context=conversation_context,  # ✅ same pattern as CLI
                )
            except Exception as e:
                st.error(f"Error running GeneGPT2: {e}")
                st.stop()

        # 4) Show explanation in chat
        st.write(explanation)

        # 5) Add assistant message to history (for UI)
        st.session_state["messages"].append(
            {"role": "assistant", "content": explanation}
        )

        # 5b) Add assistant message to conversation memory (for future turns)
        convo.add_assistant_message(explanation)

        # 6) Store this answer_json in session for sidebar evidence view
        st.session_state["answers"].append(
            {"question": user_input, "answer_json": answer_json}
        )

        # 7) Also show a compact "Sources used" section under the explanation
        evidence = answer_json.get("evidence", {}) or {}
        omim = evidence.get("omim") or {}
        ncbi = evidence.get("ncbi") or {}
        clinvar = evidence.get("clinvar") or {}
        pubmed = evidence.get("pubmed") or {}

        # ⭐ NEW: pull disease_focus block from pipeline
        disease_focus = answer_json.get("disease_focus") or {}

        # ⭐ NEW: show gene IDs if pipeline provides them
        gene = answer_json.get("gene", {}) or {}
        symbol = gene.get("symbol")
        omim_id = gene.get("omim_id")
        ncbi_gene_id = gene.get("ncbi_gene_id")

        if symbol or omim_id or ncbi_gene_id:
            st.markdown("#### 🧾 Gene IDs used")
            if symbol:
                st.write(f"**Gene symbol:** `{symbol}`")
            if omim_id or ncbi_gene_id:
                st.write("**Database IDs:**")
            if omim_id:
                st.write(f"- OMIM: `{omim_id}`")
            if ncbi_gene_id:
                st.write(f"- NCBI Gene ID: `{ncbi_gene_id}`")

        # ⭐ NEW: Disease summary (from OMIM phenotypes)
                # ⭐ NEW: Disease summary (from OMIM phenotypes)
        if disease_focus.get("used"):
            st.markdown("#### 🦠 Disease summary (from OMIM)")
            df_gene = disease_focus.get("gene_symbol") or symbol
            raw_top_diseases = disease_focus.get("top_diseases") or []
            total = disease_focus.get("total_phenotypes")

            # Clean up disease names: remove { } and extra spaces
            top_diseases = []
            for name in raw_top_diseases:
                # ensure string
                if not isinstance(name, str):
                    name = str(name)
                clean = name.strip().strip("{}").strip()
                if clean:
                    top_diseases.append(clean)

            if df_gene:
                st.write(f"**Gene:** `{df_gene}`")
            if total is not None:
                st.write(f"**Total OMIM phenotypes:** {total}")

            if top_diseases:
                st.write("**Top associated diseases:**")
                for name in top_diseases:
                    st.markdown(f"- {name}")

        # ⭐ PubMed papers used — nicer display (limit to first 5)
        papers = pubmed.get("papers") or []
        if papers:
            st.markdown("#### 📄 PubMed papers used")

            for i, p in enumerate(papers[:5], start=1):  # show at most 5
                pmid = p.get("pmid")
                title = p.get("title") or "PubMed article"
                year = p.get("year")
                journal = p.get("journal")
                snippet = p.get("snippet")

                # Build main title line with real PubMed link
                if pmid:
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    header = f"{i}. [{title}]({url})"
                    sub = f"PMID: `{pmid}`"
                else:
                    header = f"{i}. {title}"
                    sub = ""

                # Optional: add year + journal if the PubMed client provides them
                meta_bits = []
                if year:
                    meta_bits.append(str(year))
                if journal:
                    meta_bits.append(journal)

                if meta_bits:
                    meta_text = " • ".join(meta_bits)
                    if sub:
                        sub = sub + " • " + meta_text
                    else:
                        sub = meta_text

                # Show header
                st.markdown(header)

                # Small gray line under the title (PMID, year, journal)
                if sub:
                    st.markdown(f"<small>{sub}</small>", unsafe_allow_html=True)

                # Show snippet as a quoted summary if present
                if snippet:
                    st.markdown(f"> {snippet}")

        # ⭐ ClinVar summary box for variant questions
        if clinvar.get("used"):
            st.markdown("#### 🧬 ClinVar variant summary")

            acc = clinvar.get("accession") or "not available"
            sig = clinvar.get("clinical_significance") or "not clearly classified"
            cond = clinvar.get("condition") or "not specified"
            review = clinvar.get("review_status") or "not specified"
            link = clinvar.get("link")

            lines = [
                f"- **Accession:** `{acc}`",
                f"- **Clinical significance:** {sig}",
                f"- **Condition:** {cond}",
                f"- **Review status:** {review}",
            ]
            st.markdown("\n".join(lines))

            if link:
                st.markdown(f"[Open full ClinVar record]({link})")
