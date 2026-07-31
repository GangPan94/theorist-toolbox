import json
from pathlib import Path

import pytest

from brain.config import AgentConfig, Config, ProviderConfig, SearchConfig
from brain.ingest.latex_source import normalize_tex
from brain.ingest.pipeline import ingest_path

FIXTURES = Path(__file__).parent / "fixtures"
MINI = FIXTURES / "mini_paper"


@pytest.fixture(scope="session")
def golden_macros() -> dict:
    return json.loads((MINI / "expected_macros.json").read_text())


@pytest.fixture(scope="session")
def golden_chunks() -> dict:
    return json.loads((MINI / "expected_chunks.json").read_text())


@pytest.fixture(scope="session")
def normalized():
    return normalize_tex(MINI / "mini.tex")


@pytest.fixture()
def cfg(tmp_path: Path) -> Config:
    c = Config(
        root=tmp_path,
        provider=ProviderConfig(name="fake"),
        agent=AgentConfig(),
        search=SearchConfig(),
        papers_dir=tmp_path / "papers",
        parsed_dir=tmp_path / "parsed_papers",
        index_dir=tmp_path / "index",
        scratchpad_dir=tmp_path / "scratchpad",
    )
    c.ensure_dirs()
    return c


@pytest.fixture()
def ingested_cfg(cfg: Config) -> Config:
    result = ingest_path(cfg, MINI, paper_id="mini_paper", enrich=False)
    assert not result.skipped
    return cfg
