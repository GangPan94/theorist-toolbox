"""Offline end-to-end: question → scripted agent loop → cited answer."""

from brain.agent import run_agent, SYSTEM_PROMPT
from brain.providers.base import TextEvent, ToolCallEvent, ToolResultEvent
from brain.providers.fake import FakeProvider, ScriptedCall


def _finalize(results: list[str]) -> str:
    proof = results[-1]
    assert "REQUESTED ITEM" in proof
    return ("The direct mechanism maximizes welfare because valuations are "
            "separable and monotone [mini_paper, Theorem 1]; see the bundled "
            "prerequisites in the proof [mini_paper, Proof of Theorem 1].")


def test_end_to_end_offline(ingested_cfg):
    provider = FakeProvider(
        script=[
            ScriptedCall("search_library", {"query": "optimal direct mechanism"}),
            ScriptedCall("read_section", {"paper_id": "mini_paper",
                                          "section_name": "Model"}),
            ScriptedCall("write_to_scratchpad",
                         {"note": "mini_paper: \\val = v_i(t_i), \\mech = (x,p)"}),
            ScriptedCall("read_theorem_or_proof",
                         {"paper_id": "mini_paper",
                          "item_name": "Proof of Theorem 1"}),
        ],
        finalize=_finalize,
    )
    events = []
    answer = run_agent(ingested_cfg, "Why is the direct mechanism optimal?",
                       provider=provider, on_event=events.append)

    assert "[mini_paper, Theorem 1]" in answer
    # every scripted call executed without error
    assert [t[0] for t in provider.transcript] == [
        "search_library", "read_section", "write_to_scratchpad",
        "read_theorem_or_proof"]
    assert not any(is_err for _, _, is_err in provider.transcript)
    # event stream saw calls, results, and the final text
    kinds = [type(e).__name__ for e in events]
    assert kinds.count("ToolCallEvent") == 4
    assert kinds.count("ToolResultEvent") == 4
    assert kinds[-1] == "TextEvent"
    # scratchpad persisted
    pads = list((ingested_cfg.scratchpad_dir / "sessions").glob("*.md"))
    assert pads and "\\mech = (x,p)" in pads[0].read_text()


def test_system_prompt_contains_grounding_rules():
    for needle in ("search_library", "read_theorem_or_proof",
                   "write_to_scratchpad", "NEEDS_REVIEW", "paper_id"):
        assert needle in SYSTEM_PROMPT
