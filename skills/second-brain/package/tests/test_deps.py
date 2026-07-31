from brain.ingest.deps import compute_dependencies


def test_dependencies_match_golden(normalized, golden_chunks):
    deps = compute_dependencies(normalized.env_records, normalized.label_map,
                                normalized.name_map)
    for cid, exp in golden_chunks["envs"].items():
        assert deps[cid] == exp["dependencies"], cid


def test_proof_parent_is_first_dependency(normalized):
    deps = compute_dependencies(normalized.env_records, normalized.label_map,
                                normalized.name_map)
    proof = next(r for r in normalized.env_records if r.id == "proof_of_theorem_1")
    assert proof.parent == "theorem_1"
    assert deps["proof_of_theorem_1"][0] == "theorem_1"


def test_natural_language_and_ref_both_resolve(normalized):
    deps = compute_dependencies(normalized.env_records, normalized.label_map,
                                normalized.name_map)
    # "By Definition 2" (natural language) and \ref{def:mechanism} (explicit)
    assert "definition_2" in deps["proof_of_theorem_1"]
    assert "definition_1" in deps["proof_of_theorem_1"]
