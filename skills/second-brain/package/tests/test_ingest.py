import json

from brain.index import store
from brain.ingest.pipeline import ingest_path

from conftest import MINI


def test_ingest_writes_chunks_index_and_qa(ingested_cfg, golden_chunks):
    paper_dir = ingested_cfg.parsed_dir / "mini_paper"
    assert (paper_dir / "source.md").is_file()
    assert (paper_dir / "qa_report.json").is_file()
    for cid in golden_chunks["envs"]:
        assert (paper_dir / "chunks" / f"{cid}.md").is_file(), cid
    for sid in golden_chunks["sections"]:
        assert (paper_dir / "chunks" / f"{sid}.md").is_file(), sid

    index = store.load_index(ingested_cfg.index_file)
    entry = index["mini_paper"]
    assert entry["title"].startswith("Allocation with Monotone")
    assert entry["extraction"]["tier"] == 0
    assert entry["extraction"]["needs_review"] is False
    assert entry["chunks"]["theorem_1"]["dependencies"] == \
        golden_chunks["envs"]["theorem_1"]["dependencies"]
    assert len(entry["custom_macros"]) == 5
    qa = json.loads((paper_dir / "qa_report.json").read_text())
    assert qa["score"] == entry["extraction"]["qa_score"]


def test_reingest_is_noop_on_same_content(ingested_cfg):
    result = ingest_path(ingested_cfg, MINI, paper_id="mini_paper", enrich=False)
    assert result.skipped


def test_force_reingest_runs(ingested_cfg):
    result = ingest_path(ingested_cfg, MINI, paper_id="mini_paper",
                         enrich=False, force=True)
    assert not result.skipped
    assert result.n_chunks > 0
