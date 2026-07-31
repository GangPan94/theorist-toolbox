from brain.ingest.qa import evaluate


def test_clean_fixture_scores_high(normalized):
    report = evaluate(normalized.markdown, tier=0, n_sections=6,
                      n_envs=len(normalized.env_records))
    assert report.score >= 0.9
    assert not report.needs_review
    assert report.checks["math_dollars_balanced"]
    assert report.checks["env_begin_end_balanced"]


def test_corrupted_text_is_flagged():
    garbage = ("# T\n\n## Body\n\nunbalanced $math and \\begin{theorem} never closed\n"
               + "�" * 50 + "\n")
    report = evaluate(garbage, tier=2, n_sections=1, n_envs=0)
    assert report.score < 0.7
    assert report.needs_review
    assert not report.checks["math_dollars_balanced"]
    assert not report.checks["env_begin_end_balanced"]


def test_tier2_penalty_applies():
    text = "# T\n\n## Body\n\nclean text, no math\n"
    t0 = evaluate(text, tier=0, n_sections=1, n_envs=0)
    t2 = evaluate(text, tier=2, n_sections=1, n_envs=0)
    assert t0.score > t2.score
