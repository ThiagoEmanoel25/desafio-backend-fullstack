# Retrieval eval (Phase 12)

Dataset: `tests/data/retrieval_eval.json` (v1: 18 tasks of two users, 12
queries, relevant tasks by stable key). Embedder: deterministic hashing
bag-of-words fake (64 dims), never a provider. Test:
`tests/test_retrieval_eval.py` (`pytest -s` prints the line below). The run is
invalid if any embedding or rerank call degrades; the test fails if reranking
lowers Recall@5.

| Order | Recall@5 | MRR@5 |
|---|---|---|
| RRF (before) | 1.000 | 1.000 |
| Reranked (after) | 1.000 | 1.000 |

Reading: on this small set both orders are already saturated, so the rerank
does not hurt and the gate holds; it does not prove a gain. Isolation is also
checked: no query returns a task of the other user.
