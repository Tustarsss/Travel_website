from app.services import top_k_by_score


def test_top_k_by_score_returns_sorted_items():
    items = [
        {"name": "alpha", "score": 0.2},
        {"name": "beta", "score": 0.9},
        {"name": "gamma", "score": 0.5},
    ]

    result = top_k_by_score(items, k=2, score=lambda item: item["score"])

    assert [i["name"] for i in result] == ["beta", "gamma"]


def test_top_k_by_score_handles_small_collections():
    items = [{"name": "only", "score": 1.0}]

    result = top_k_by_score(items, k=3, score=lambda item: item["score"])

    assert result == items
