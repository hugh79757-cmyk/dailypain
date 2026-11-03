import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "collector"))
from llama_analyze import cluster

def test_cluster_merges_same_category():
    posts = [
        {"text": "a", "category": " commute", "pain_score": 50, "author": "x"},
        {"text": "b", "category": " commute", "pain_score": 80, "author": "y"},
    ]
    out = cluster(posts)
    assert len(out) == 1
    assert out[0]["pain_score"] == 80