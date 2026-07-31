from brain.ingest.chunker import ast_headings, chunk_sections


def test_env_records_match_golden(normalized, golden_chunks):
    got = {r.id: r for r in normalized.env_records}
    expected = golden_chunks["envs"]
    assert set(got) == set(expected)
    for cid, exp in expected.items():
        rec = got[cid]
        assert rec.env_type == exp["type"], cid
        assert rec.title == exp["title"], cid
        assert rec.label == exp["label"], cid


def test_sections_match_golden(normalized, golden_chunks):
    sections = chunk_sections(normalized.markdown)
    assert [s.id for s in sections] == golden_chunks["sections"]


def test_math_passes_through_byte_identical(normalized):
    theorem = next(r for r in normalized.env_records if r.id == "theorem_1")
    assert r"$x^{*}(t) \in \argmax_{x} \sum_i \val$" in theorem.latex
    assert "Assumption~\\ref{ass:mono}" in theorem.latex
    # inline math in prose survives untouched too
    assert r"($\val$, $\mech$, $\typespace{i}$)" in normalized.markdown


def test_title_authors_year_abstract(normalized):
    assert normalized.title == "Allocation with Monotone Valuations: A Toy Study"
    assert normalized.authors == ["A. Author", "B. Author"]
    assert normalized.year == 2026
    assert normalized.abstract.startswith("We study a toy allocation problem")
    # comment after "optimal." must be stripped, escaped \% must survive
    assert "trailing comment" not in normalized.markdown
    assert r"50\%" in normalized.markdown


def test_input_inlining_brought_notation_macro(normalized):
    assert any("\\mech" in d for d in normalized.macros)


def test_ast_heading_walk_agrees_with_split(normalized):
    titles = ast_headings(normalized.markdown, level=2)
    sections = chunk_sections(normalized.markdown)
    assert titles == [s.title for s in sections]


def test_section_content_contains_env_blocks(normalized):
    sections = {s.id: s for s in chunk_sections(normalized.markdown)}
    assert "```env:theorem id=theorem_1" in sections["main_results"].text
    assert "\\begin{theorem}" in sections["main_results"].text
    assert "myerson1981" in sections["references"].text
