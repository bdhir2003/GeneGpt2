import json
from openai import OpenAI

client = OpenAI(api_key="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")


def explain_answer_json(answer_json: dict) -> str:
    """
    Take Final Answer JSON (Layer 3) and ask an LLM
    to explain it in clear, natural language.
    Style: student-friendly, calm, not too technical.
    """

    json_text = json.dumps(answer_json, indent=2)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant explaining genetic test results. "
                "You must ONLY use the information in the JSON provided. "
                "Do NOT invent new facts or numbers. "
                "Explain things in simple, natural English, like you are talking "
                "to a college student with no medical background. "
                "Be clear and calm. You can write a few short paragraphs or bullets "
                "if needed, but avoid heavy jargon."
            ),
        },
        {
            "role": "user",
            "content": (
                "Here is the structured JSON with the result. "
                "Please explain what it means in natural language:\n\n"
                f"{json_text}"
            ),
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",   # you can change to another model if you want
        messages=messages,
        temperature=0.2,       # keep it stable, not too creative
    )

    return response.choices[0].message.content.strip()


# Tiny manual test (optional)
if __name__ == "__main__":
    demo_answer = {
        "answer_type": "gene_disease_summary",
        "gene": "BRCA1",
        "main_diseases": [
            {
                "name": "Hereditary breast and ovarian cancer",
                "inheritance": "autosomal dominant",
                "summary": "Increases risk of breast and ovarian cancer."
            }
        ],
        "key_points": [
            "These are conditions linked with BRCA1.",
            "Having this gene does not guarantee disease."
        ],
        "source_links": {
            "omim": ["113705"],
            "clinvar": []
        }
    }

    print(explain_answer_json(demo_answer))
