from brain.tools.spec import build_toolset, TRUNCATION_NOTE


def test_search_tool_lists_papers_and_items(ingested_cfg):
    tools = build_toolset(ingested_cfg)
    result, is_error = tools.execute("search_library",
                                     {"query": "monotone valuations"})
    assert not is_error
    assert "paper_id: mini_paper" in result
    assert "theorem_1" in result


def test_read_section_injects_macros_and_fuzzy_matches(ingested_cfg):
    tools = build_toolset(ingested_cfg)
    result, is_error = tools.execute(
        "read_section", {"paper_id": "mini_paper", "section_name": "model"})
    assert not is_error
    assert "CUSTOM MACROS" in result
    assert "\\newcommand{\\val}{v_i(t_i)}" in result
    assert "\\begin{definition}" in result
    # fuzzy: 'Main results' should find 'Main Results'
    result2, is_error2 = tools.execute(
        "read_section", {"paper_id": "mini_paper", "section_name": "main results"})
    assert not is_error2 and "\\begin{theorem}" in result2


def test_read_theorem_bundles_macros_prereqs_then_item(ingested_cfg):
    tools = build_toolset(ingested_cfg)
    result, is_error = tools.execute(
        "read_theorem_or_proof",
        {"paper_id": "mini_paper", "item_name": "Proof of Theorem 1"})
    assert not is_error
    i_macro = result.find("CUSTOM MACROS")
    i_prereq = result.find("PREREQUISITES")
    i_item = result.find("REQUESTED ITEM")
    assert -1 < i_macro < i_prereq < i_item
    # parent statement and both referenced definitions are bundled
    prereq_block = result[i_prereq:i_item]
    assert "Theorem 1 (Optimality" in prereq_block
    assert "Definition 2 (Valuation)" in prereq_block
    assert "Assumption 1 (Monotonicity)" in prereq_block
    assert "\\begin{proof}" in result[i_item:]


def test_errors_are_results_not_exceptions(ingested_cfg):
    tools = build_toolset(ingested_cfg)
    r1, e1 = tools.execute("read_section",
                           {"paper_id": "nope", "section_name": "Model"})
    assert e1 and r1.startswith("Error:") and "mini_paper" in r1
    r2, e2 = tools.execute("read_theorem_or_proof",
                           {"paper_id": "mini_paper", "item_name": "Theorem 99"})
    assert e2 and "Available items" in r2
    r3, e3 = tools.execute("no_such_tool", {})
    assert e3
    r4, e4 = tools.execute("read_section", {"paper_id": "mini_paper"})
    assert e4 and "bad arguments" in r4


def test_oversized_results_are_truncated(ingested_cfg):
    tools = build_toolset(ingested_cfg)
    tools.max_result_chars = 200
    result, _ = tools.execute(
        "read_section", {"paper_id": "mini_paper", "section_name": "Main Results"})
    assert result.endswith(TRUNCATION_NOTE)
    assert len(result) <= 200 + len(TRUNCATION_NOTE)


def test_scratchpad_appends(ingested_cfg):
    tools = build_toolset(ingested_cfg)
    r1, e1 = tools.execute("write_to_scratchpad", {"note": "\\val is agent i's value"})
    assert not e1 and "Saved" in r1
    pads = list((ingested_cfg.scratchpad_dir / "sessions").glob("*.md"))
    assert len(pads) == 1
    assert "\\val is agent i's value" in pads[0].read_text()
