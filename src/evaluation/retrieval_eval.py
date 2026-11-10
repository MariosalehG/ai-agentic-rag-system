"""Retrieval evaluation: Recall@k and MRR across search strategies."""

import json
from pathlib import Path

from src.services.opensearch.hybrid import hybrid_search
from src.services.opensearch.search import bm25_search, vector_search

STRATEGIES = {
    "keyword": bm25_search,
    "vector": vector_search,
    "hybrid": hybrid_search,
}


def load_golden_set(path: str = "tests/golden_set.json") -> list[dict]:
    return json.loads(Path(path).read_text())


def evaluate_one(question: dict, search_fn, k: int = 5) -> dict:
    results = search_fn(question["question"], None, k)

    # chunk-level results collapse to paper-level, order preserved
    retrieved_ids = list(dict.fromkeys(r.arxiv_id for r in results))
    expected = set(question["expected_arxiv_ids"])

    if not expected:
        # out-of-scope: success means retrieving nothing relevant
        return {"recall": 1.0 if not retrieved_ids else 0.0, "rr": 0.0, "scored": False}

    recall = 1.0 if expected & set(retrieved_ids) else 0.0

    rr = 0.0
    for rank, arxiv_id in enumerate(retrieved_ids, start=1):
        if arxiv_id in expected:
            rr = 1.0 / rank
            break

    return {"recall": recall, "rr": rr, "scored": True}


def evaluate_strategy(golden_set: list[dict], name: str, k: int = 5) -> dict:
    search_fn = STRATEGIES[name]
    scored = [evaluate_one(q, search_fn, k) for q in golden_set]
    in_scope = [s for s in scored if s["scored"]]

    return {
        "strategy": name,
        f"recall@{k}": sum(s["recall"] for s in in_scope) / len(in_scope),
        "mrr": sum(s["rr"] for s in in_scope) / len(in_scope),
        "out_of_scope_correct": sum(
            s["recall"] for s in scored if not s["scored"]
        ),
    }


def run_comparison(k: int = 5) -> None:
    golden_set = load_golden_set()
    print(f"Evaluating {len(golden_set)} questions at k={k}\n")
    print(f"{'strategy':10} {'recall@k':>10} {'MRR':>8}")
    print("-" * 30)

    for name in STRATEGIES:
        m = evaluate_strategy(golden_set, name, k)
        print(f"{m['strategy']:10} {m[f'recall@{k}']:>10.3f} {m['mrr']:>8.3f}")