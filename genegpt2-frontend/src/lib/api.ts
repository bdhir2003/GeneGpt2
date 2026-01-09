const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export interface Evidence {
    omim?: any;
    ncbi?: any;
    clinvar?: any;
    pubmed?: any;
}

export interface AnswerJson {
    question_type?: string;
    gene?: {
        symbol?: string;
        omim_id?: string;
        ncbi_id?: string;
        ncbi_gene_id?: string;
    };
    evidence?: Evidence;
    disease_focus?: {
        used?: boolean;
        top_diseases?: string[];
        total_phenotypes?: number;
    };
}

export interface ChatResponse {
    answer: string;
    answer_json: AnswerJson;
    usage?: {
        prompt_tokens: number;
        completion_tokens: number;
        total_tokens: number;
    };
    trust?: number;
    certainty?: number;
    sources?: string[];
}

export async function sendMessage(message: string): Promise<ChatResponse> {
    // 1. Get or create persistent session ID from localStorage
    let sessionId = typeof window !== 'undefined' ? localStorage.getItem("genegpt_session_id") : null;

    if (!sessionId && typeof window !== 'undefined') {
        sessionId = crypto.randomUUID();
        localStorage.setItem("genegpt_session_id", sessionId);
    }

    const res = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
            message,
            session_id: sessionId
        }),
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || "Failed to fetch response");
    }

    return res.json();
}
