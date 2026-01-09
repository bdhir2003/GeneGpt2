const API_BASE_URL = "http://localhost:8000";

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
    const res = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ message }),
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || "Failed to fetch response");
    }

    return res.json();
}
