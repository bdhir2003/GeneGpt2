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

GeneGPT works in two main layers.

Layer 1 – Question Understanding

The system first converts a natural language question into structured information.

It identifies:

The gene name

Whether a mutation is mentioned

The type of query (gene-disease or gene-variant risk)

What information is needed (disease links, risk level, explanation)

This taught me how important structured input is in AI system design.

Layer 2 – Evidence Retrieval

After understanding the question, the system retrieves structured evidence from trusted biomedical databases.

OMIM is used for gene–disease relationships.

ClinVar is used for variant classification and mutation risk interpretation.

The reasoning layer and the evidence layer are kept separate. This improves transparency and allows the system to clearly show where information comes from.

What I Learned From This Project

Through this project, I learned:

How to design layered AI architectures

Why separating reasoning and evidence improves reliability

How biomedical databases like OMIM and ClinVar work

The importance of structured JSON pipelines

How to design systems that can later integrate with LLMs or RAG

Why explainability is critical in healthcare AI

I also learned that system design and architecture are just as important as building machine learning models.

Current Capabilities (v1)

Understands gene-only questions

Understands gene + mutation questions

Separates question logic from evidence retrieval

Uses structured data design

Built as a foundation for future research expansion

Future Improvements

For the next version, I plan to:

Automate OMIM and ClinVar API integration

Add citation linking

Add confidence scoring

Add evaluation metrics

Integrate a reasoning LLM layer

Build a simple user interface

Research Context

GeneGPT is part of my research exploration in AI for healthcare and structured reasoning systems.

The goal is to design AI systems that are transparent, trustworthy, and suitable for biomedical applications.

Author

Bobby Dhir
University of Nebraska Omaha
