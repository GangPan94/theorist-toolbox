from brain.index import store
from brain.index.search import Searcher

DECOY = {
    "title": "Dynamics of Social Learning in Networks",
    "authors": ["C. Author"],
    "year": 2023,
    "abstract": "We present a novel approach to information cascades and herding "
                "behavior on random graphs.",
    "keywords": ["social learning", "networks", "herding"],
    "proof_techniques": ["martingale convergence"],
    "key_theorems": ["Theorem 1 (Cascade threshold)"],
    "available_sections": ["Introduction", "Model", "Results"],
    "chunks": {"theorem_1": {"file": "theorem_1.md", "type": "theorem",
                             "dependencies": []}},
    "extraction": {"tier": 2, "qa_score": 0.6, "needs_review": True},
    "content_hash": "sha256:decoy",
}


def test_relevant_paper_ranks_first(ingested_cfg):
    index = store.load_index(ingested_cfg.index_file)
    index["social_learning_2023"] = DECOY
    hits = Searcher(ingested_cfg, index).search("monotone valuations allocation mechanism")
    assert hits, "no results"
    assert hits[0].paper_id == "mini_paper"


def test_decoy_ranks_first_on_its_own_topic(ingested_cfg):
    index = store.load_index(ingested_cfg.index_file)
    index["social_learning_2023"] = DECOY
    hits = Searcher(ingested_cfg, index).search("herding cascades social learning")
    assert hits[0].paper_id == "social_learning_2023"
    assert hits[0].needs_review is True  # flag must reach the agent


def test_hit_carries_navigation_metadata(ingested_cfg):
    index = store.load_index(ingested_cfg.index_file)
    hits = Searcher(ingested_cfg, index).search("valuation")
    hit = hits[0]
    assert "Main Results" in hit.available_sections
    assert "theorem_1" in hit.env_chunks
    assert "proof_of_theorem_1" in hit.env_chunks
    assert "model" not in hit.env_chunks  # sections are not env chunks


def test_empty_query_and_empty_index(cfg, ingested_cfg):
    assert Searcher(cfg, {}).search("anything") == []
    index = store.load_index(ingested_cfg.index_file)
    assert Searcher(ingested_cfg, index).search("   ") == []
