# GeneGPT – v1 Design

This system answers gene and mutation questions using OMIM and ClinVar.

## Question JSON (Layer 1)

### 1. Gene → Disease
{
  "user_question": "I have BRCA1 gene, what diseases are linked to it?",
  "query_type": "gene_disease",
  "gene": {
    "input": "BRCA1",
    "symbol": "BRCA1",
    "gene_id": null
  },
  "variant": null,
  "needs": [
    "disease_links",
    "basic_explanation"
  ]
}


### 2. Gene + Mutation → Risk
{
  "user_question": "I have BRCA1 c.68_69delAG. Is this mutation serious?",
  "query_type": "gene_variant_risk",
  "gene": {
    "input": "BRCA1",
    "symbol": "BRCA1",
    "gene_id": null
  },
  "variant": {
    "input": "c.68_69delAG",
    "hgvs": "c.68_69delAG",
    "clinvar_id": null
  },
  "needs": [
    "variant_classification",
    "disease_risk",
    "basic_explanation"
  ]
}

### Evidence JSON (Layer 2)
Case 1: query_type = "gene_disease" (gene → disease)

{
  "gene": {
    "symbol": "BRCA1",
    "gene_id_omim": "113705"
  },
  "variant": null,
  "omim": {
    "diseases": [
      {
        "name": "Hereditary breast and ovarian cancer",
        "omim_id": "113705",
        "inheritance": "autosomal dominant",
        "short_note": "Increases risk of breast and ovarian cancer."
      },
      {
        "name": "Pancreatic cancer susceptibility",
        "omim_id": "614320",
        "inheritance": "autosomal dominant",
        "short_note": "Higher chance of pancreatic cancer in some carriers."
      }
    ]
  },
  "clinvar": null
}

🟦 Case 2: query_type = "gene_variant_risk" (gene + mutation → OMIM + ClinVar)

{
  "gene": {
    "symbol": "BRCA1",
    "gene_id_omim": "113705"
  },
  "variant": {
    "hgvs": "c.68_69delAG",
    "clinvar_id": "17661"
  },
  "omim": {
    "diseases": [
      {
        "name": "Hereditary breast and ovarian cancer",
        "omim_id": "113705",
        "inheritance": "autosomal dominant",
        "short_note": "Increases risk of breast and ovarian cancer."
      }
    ]
  },
  "clinvar": {
    "classification": "Pathogenic",
    "confidence": "high",
    "submitter_count": 9,
    "conflicting_calls": false,
    "last_evaluated": "2023-05-01"
  }
}

### Final Answer JSON (Layer 3)

🟦 Case 1: gene_disease (Gene → disease)

{
  "answer_type": "gene_disease_summary",
  "gene": "BRCA1",
  "main_diseases": [
    {
      "name": "Hereditary breast and ovarian cancer",
      "inheritance": "autosomal dominant",
      "summary": "This condition increases the risk of breast and ovarian cancer."
    },
    {
      "name": "Pancreatic cancer susceptibility",
      "inheritance": "autosomal dominant",
      "summary": "Some carriers have increased pancreatic cancer risk."
    }
  ],
  "key_points": [
    "These conditions are known to be linked with BRCA1.",
    "Having a gene associated with a condition does not guarantee disease.",
    "Risk depends on personal and family history."
  ],
  "source_links": {
    "omim": ["113705", "614320"],
    "clinvar": []
  }
}

Case 2: gene_variant_risk (Gene + Mutation → Risk)

{
  "answer_type": "variant_risk_summary",
  "gene": "BRCA1",
  "variant": "c.68_69delAG",
  "clinvar_classification": "Pathogenic",
  "risk_level": "high",
  "associated_conditions": [
    "Hereditary breast cancer",
    "Hereditary ovarian cancer"
  ],
  "inheritance": "autosomal dominant",
  "key_points": [
    "This mutation is classified as pathogenic, meaning it is a harmful change.",
    "People with this mutation have higher chances of developing breast and ovarian cancer.",
    "It increases risk but does not guarantee that cancer will occur."
  ],
  "suggested_next_steps": [
    "Consider speaking with a genetic counselor.",
    "Discuss screening and prevention options with a healthcare professional.",
    "Ask about whether family members might also need testing."
  ],
  "source_links": {
    "omim": ["113705"],
    "clinvar": ["17661"]
  }
}

🏗️ Big Architecture Overview

Think of GeneGPT v1 as 4 big blocks:

Streamlit UI – where the user types and sees the answer

Question Layer (JSON 1) – understand what they asked

Evidence Layer (JSON 2) – OMIM + ClinVar filtered truth

Answer Layer (JSON 3 + LLM) – final structured summary → natural language

Let’s walk it in order.

1️⃣ Streamlit UI (Front-end)

User sees:

Title: “GeneGPT (Prototype)”

One big text box: “Enter your question”

Button: “Analyze”

Answer text area

Button: “Start again”

What it does:

Takes the raw text question from user

Sends it to one function in backend:

run_genegpt_pipeline(user_question)

Shows the final answer that comes back

When user clicks Start again, it just clears the screen (no memory kept)

So the UI has one job:

“Get question → show answer.”

All JSON and database stuff happens behind the scenes.

2️⃣ Question Layer – Question JSON (Layer 1)

This is the first “thinking step” inside the backend.

Input: user_question (normal text)
Output: Question JSON with:

query_type → "gene_disease" or "gene_variant_risk"

gene → symbol, maybe later gene_id

variant → only if present (mutation)

needs → what kind of answer we want (disease links, risk, explanation)

This step belongs to one logical block:

🧠 Question Parser

It doesn’t call any external API.
It only understands what user is asking and converts it into clean structure.

3️⃣ Evidence Layer – OMIM + ClinVar → Evidence JSON (Layer 2)

Now the system knows:

what gene

whether there is a mutation

what type of query

Based on query_type, it does:

If gene_disease:

Call OMIM only

Get diseases linked to gene

Filter to a small list

Build OMIM evidence block

If gene_variant_risk:

Call OMIM → get disease context

Call ClinVar → get variant submissions

Apply your ClinVar algorithm:

filter by review status

count votes

decide classification + confidence

Build OMIM evidence + ClinVar evidence blocks

Then we combine everything into:

Evidence JSON (Layer 2)

with fields like:

gene (symbol, omim id)

variant (hgvs, clinvar id)

omim (disease list, inheritance, short notes)

clinvar (classification, confidence, submitter count, conflicts, last evaluated)

This whole layer is your “truth builder”.

The LLM still doesn’t see anything here.
All work is done by your code + OMIM + ClinVar.

4️⃣ Answer Layer – Final Answer JSON (Layer 3)

Now we have clean evidence.
Next we create the message we want to tell the human, but still in JSON.

From Evidence JSON, your logic builds:

For gene_disease:

answer_type: "gene_disease_summary"

gene

main_diseases → names, inheritance, short summary

key_points → simple high-level bullets

source_links → OMIM IDs

For gene_variant_risk:

answer_type: "variant_risk_summary"

gene, variant

clinvar_classification (Pathogenic / Benign / Uncertain)

risk_level (high / low / uncertain)

associated_conditions

inheritance

key_points

suggested_next_steps

source_links → OMIM/ClinVar IDs

This JSON is:

“The final structured story we want to explain.”

Still not shown to the user.

5️⃣ LLM Explainer – OpenAI turns JSON → natural language

Now we pass the Final Answer JSON + a safe instruction to your OpenAI model:

“Explain this JSON in simple English.”

“Don’t add new facts.”

“Talk like a calm, clear genetic counselor.”

The model:

Reads the JSON

Uses fields like key_points, risk_level, associated_conditions

Produces 1–3 paragraphs in normal language

Example-style output:

“This BRCA1 mutation is usually considered a harmful (pathogenic) change…
It increases the risk of hereditary breast and ovarian cancer…
It does not guarantee cancer but raises the chances…
You should… etc.”

This text is what we finally send back to:

Streamlit UI → user sees it.

6️⃣ After Answer → Reset

Because v1 has:

No cache

No memory

No history

After the answer is shown:

The JSON objects (Question, Evidence, Answer) are just temporary variables in code

For the next question, we start fresh again

“Start again” button just refreshes the app

So each question is like:

One full run of the pipeline, from scratch.

🧩 Architecture in Simple Flow

If we write it as a chain:

Streamlit UI
⬇

Question Parser → Question JSON (L1)
⬇

OMIM Client + ClinVar Client + Filters → Evidence JSON (L2)
⬇

Answer Builder → Final Answer JSON (L3)
⬇

OpenAI LLM Explainer → final text answer
⬇

Streamlit UI shows text

That’s the full architecture idea of GeneGPT v1.