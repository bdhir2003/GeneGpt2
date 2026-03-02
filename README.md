GeneGPT – v1 Design 🧬

GeneGPT is a system I designed to answer questions about genes and genetic mutations. The goal of this project is to build a structured and transparent AI system that connects gene-related questions to reliable biomedical databases such as OMIM and ClinVar.

Instead of directly generating answers like a normal chatbot, GeneGPT works in layers. It first understands the question, then retrieves structured evidence, and finally prepares a response based on that evidence.

This project helped me understand how to design AI systems that are transparent and evidence-based rather than black-box models.

What Problem This Project Solves

When people ask questions like:

“What diseases are linked to BRCA1?”

“Is BRCA1 c.68_69delAG a serious mutation?”

Most AI systems just generate text answers. But in healthcare and genetics, we need structured reasoning and trusted evidence.

GeneGPT separates:

Question understanding

Evidence retrieval

Explanation generation

This makes the system more reliable and easier to audit.

How GeneGPT Works (Simple Explanation)

GeneGPT has two main layers:

Layer 1 – Question Understanding

The system first converts a natural language question into structured information.

For example:

If someone asks about a gene, the system identifies:

Gene name

Whether a mutation is mentioned

What type of answer is needed (disease links, risk level, explanation, etc.)

This taught me how important structured inputs are in AI systems.

Layer 2 – Evidence Retrieval

After understanding the question, the system retrieves structured data from:

OMIM (for gene-disease relationships)

ClinVar (for mutation classification and risk)

Instead of mixing reasoning and data, the system clearly separates them. This improves transparency.

What I Learned From This Project

This project helped me understand:

How to design layered AI architectures

The importance of structured JSON in AI pipelines

How biomedical databases like OMIM and ClinVar work

Why explainability is critical in healthcare AI

The difference between generating text and retrieving evidence

How to design systems that can later integrate with LLMs or RAG

I also learned that system design is more important than just building models. A clear architecture makes future improvements easier.

Current Capabilities (v1)

Understands gene-only questions

Understands gene + mutation questions

Separates reasoning from evidence

Uses structured data design

Designed to expand into a full research system

Future Plans

For the next version, I plan to:

Automate OMIM and ClinVar API retrieval

Add confidence scoring

Add citation linking

Build a simple user interface

Add evaluation metrics

Integrate with LLM reasoning layer

Why This Project Matters To Me

As someone interested in AI and healthcare, I wanted to explore how AI systems can be transparent and structured rather than just predictive.

GeneGPT is part of my research exploration into trustworthy AI systems for healthcare decision support.

Author

Bobby Dhir
University of Nebraska Omaha
