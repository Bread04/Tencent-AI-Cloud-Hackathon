# Precedents are anonymised and human-verified, and retrieved by tags with an optional local embedding rerank

The Policy & Precedent Agent serves Policy Clauses without retrieval and Precedents with it. Clauses are a fixed set per Dispute Category (the Applicable Clauses); the policy is about a dozen clauses, so similarity search could only drop one. Precedents are the store that grows, so they are filtered by category, ranked by tag overlap, and optionally reranked by embedding similarity from a small open-source model run locally (proposed: `BAAI/bge-small-en-v1.5` through `fastembed`, which runs on ONNX without PyTorch; the model name is a default, not a contract). A switch selects tags or embeddings, and retrieval falls back to tags if the model cannot load.

Only seeded Precedents and Rulings a Human Reviewer confirmed or overrode are retrievable, and a Precedent stores no party identifier, trip ID or History-derived fact. We chose this so that a wrong model Ruling cannot become authority for the next one, and so that retrieval cannot reintroduce the History that [ADR 0001](0001-history-withheld-from-judge.md) keeps from the Judge.

## Considered Options

- **RAG over the policy clauses as well.** Rejected: about a dozen short clauses, and retrieval can only lose one the Judge is expected to cite.
- **Tencent Cloud embeddings or Vector DB.** Rejected by decision (Braedon, 12 Oct 2026): we use an open-source model instead. A local model also has no network dependency during the demo and no credentials.
- **Embeddings only, no tag layer.** Rejected: no fallback if the model fails on Demo Day, and no explainable "similar because" reason.
- **Let every past model Ruling be a Precedent.** Rejected: errors compound. Not worth the extra Precedents.

## Consequences

- A new optional dependency (`fastembed`) and a model download of roughly 100 MB. It sits in its own dependency group so the tags-only build stays small.
- Each Precedent served carries its source (seeded, confirmed, override), shown in the Communication Log.
- The Learning Feedback Loop (ticket 16) is what grows the store, and only through a Human Reviewer's decision.
- Anonymisation is enforced by a test, not by convention.
