from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import uuid
import datetime
from dotenv import load_dotenv

load_dotenv()

from app.pipeline import run_genegpt_pipeline
from app.llm_explainer_openai import explain_with_openai
from app.name_normalizer import normalize_gene_name

app = FastAPI(title="GeneGPT2 API")

# DEV CORS (allow both localhost + 127.0.0.1, and 3000/3001)
ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    message: str
    session_id: str | None = None  # Optional session ID for conversation context


@app.get("/")
def root():
    return {
        "name": "GeneGPT2 API",
        "status": "running",
        "endpoints": ["/health", "/ask", "/docs"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(req: AskRequest, request: Request, response: Response):
    text = (req.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="message cannot be empty")

    try:
        # SESSION LOGIC: Cookie > Body > New
        cookie_session_id = request.cookies.get("session_id")
        body_session_id = req.session_id
        
        session_id = cookie_session_id or body_session_id
        
        if not session_id:
            session_id = str(uuid.uuid4())
            print(f"[SESSION] Generated new session_id: {session_id}")
        else:
             # Debug log for reuse
             source = "cookie" if cookie_session_id else "body"
             print(f"[SESSION] Reusing session_id: {session_id} (Source: {source})")

        # Set persistent cookie (30 days)
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=3600 * 24 * 30,
            httponly=True,
            samesite="lax", 
            secure=False
        )

        # AUDIT LOG
        print(f"[AUDIT] route=/ask session_id={session_id} timestamp={datetime.datetime.now().isoformat()}")
        
        # 0) Normalize gene name if it looks like a single token
        clean_text = text.strip()
        if clean_text and " " not in clean_text:
             clean_text = normalize_gene_name(clean_text)

        # 1) Evidence-based structured JSON with session context
        answer_json = run_genegpt_pipeline(clean_text, session_id=session_id)

        # 2) LLM explanation (optional: only if key exists)
        # If key is missing, we fallback to evidence-only response.
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        usage_stats = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        if api_key:
            result = explain_with_openai(answer_json)
            if isinstance(result, dict):
                explanation = result.get("answer", "")
                usage_stats = result.get("usage", usage_stats)
            else:
                # Fallback if return type didn't match expectation
                explanation = str(result)
        else:
            explanation = (
                "OpenAI key not set, so I'm returning evidence-only output.\n\n"
                "Check answer_json for OMIM/NCBI/PubMed sources."
            )

        # 3) Trust Score Calculation
        trust_weights = {
            "clinvar": 0.40,
            "genereviews": 0.35,
            "omim": 0.25,
            "pubmed": 0.20,
            "gnomad": 0.15
        }
        
        evidence = answer_json.get("evidence", {})
        current_score = 0.0
        used_sources = []
        
        # Display name mapping
        display_names = {
            "clinvar": "ClinVar",
            "genereviews": "GeneReviews",
            "omim": "OMIM",
            "pubmed": "PubMed",
            "gnomad": "gnomAD"
        }

        for key, weight in trust_weights.items():
            source_data = evidence.get(key, {})
            # Check if source was actually used
            if source_data.get("used"):
                current_score += weight
                used_sources.append(display_names.get(key, key))
        
        trust_score = min(current_score, 1.0)

        # 4) Certainty Score Calculation
        certainty_score = 1.0
        
        # - Subtract 20% if only PubMed literature is used
        if len(used_sources) == 1 and "PubMed" in used_sources:
            certainty_score -= 0.20
            
        # - Subtract 15% if no clinical guideline source is used
        # We use GeneReviews as the proxy for guidelines in this context
        if "GeneReviews" not in used_sources:
            certainty_score -= 0.15
            
        # - Subtract 10% if the variant is VUS
        clinvar_sig = (evidence.get("clinvar", {}).get("clinical_significance") or "").lower()
        if "uncertain" in clinvar_sig or "vus" in clinvar_sig:
            certainty_score -= 0.10
            
        # - Subtract 15% if the gene is rare or has limited known phenotypes
        # We check total_phenotypes from disease_focus
        disease_focus = answer_json.get("disease_focus", {})
        pheno_count = disease_focus.get("total_phenotypes") if disease_focus else 0
        if pheno_count is None or (isinstance(pheno_count, int) and pheno_count < 2):
            certainty_score -= 0.15
            
        # - Subtract 10% if conflicting sources are detected
        if "conflicting" in clinvar_sig:
             certainty_score -= 0.10
             
        # Clamp between 0.30 and 0.95
        certainty_score = max(0.30, min(certainty_score, 0.95))

        return {
            "answer": explanation,
            "usage": usage_stats,
            "trust": trust_score,
            "certainty": certainty_score,
            "sources": used_sources,
            "answer_json": answer_json,
            "session_id": session_id,
            "clinical_state": answer_json.get("clinical_state", {}),
        }

    except HTTPException:
        raise
    except Exception as e:
        # Don’t leak huge traces to frontend
        raise HTTPException(status_code=500, detail=f"Backend error: {str(e)}")
