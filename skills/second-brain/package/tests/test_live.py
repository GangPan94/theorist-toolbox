"""Live smoke tests — opt-in only, one real question per provider.

    RUN_LIVE=1 BRAIN_LIVE_PROVIDERS=claude-code,anthropic .venv/bin/pytest tests/test_live.py -v

claude-code needs a logged-in Claude Code (subscription; no API key in env);
anthropic needs ANTHROPIC_API_KEY; openai needs OPENAI_API_KEY.
"""

import os

import pytest

from brain.agent import run_agent
from brain.providers.base import get_provider

RUN_LIVE = os.environ.get("RUN_LIVE") == "1"
PROVIDERS = [p.strip() for p in
             os.environ.get("BRAIN_LIVE_PROVIDERS", "claude-code").split(",") if p.strip()]

pytestmark = pytest.mark.skipif(not RUN_LIVE, reason="live tests need RUN_LIVE=1")

QUESTION = ("According to the library, why does the direct mechanism maximize "
            "welfare? Cite the exact theorem you rely on.")


@pytest.mark.parametrize("provider_name", PROVIDERS)
def test_live_answer_cites_the_fixture(ingested_cfg, provider_name):
    ingested_cfg.provider.name = provider_name
    provider = get_provider(ingested_cfg)
    answer = run_agent(ingested_cfg, QUESTION, provider=provider)
    assert answer, "empty answer"
    assert "mini_paper" in answer, f"no citation in answer:\n{answer}"
    if provider_name == "anthropic" and getattr(provider, "turns", 1) > 1:
        assert provider.cache_read_tokens > 0, "prompt cache never hit across turns"
