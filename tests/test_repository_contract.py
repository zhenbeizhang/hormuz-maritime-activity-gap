from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from reproduce_all import reproduce


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_article_manifest_and_checksums_match() -> None:
    article = ROOT / "article_data"
    manifest = pd.read_csv(article / "MANIFEST.csv", dtype=str, keep_default_na=False)
    actual = {
        path.relative_to(article).as_posix(): path
        for path in article.rglob("*")
        if path.is_file()
        and path.name not in {"MANIFEST.csv", "CHECKSUMS.sha256"}
    }
    assert set(manifest["path"]) == set(actual)
    for row in manifest.itertuples(index=False):
        assert int(row.bytes) == actual[row.path].stat().st_size
        assert row.sha256 == _sha256(actual[row.path])
    declared = {}
    for line in (article / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
        checksum, path = line.split("  ", 1)
        declared[path] = checksum
    expected = {path: _sha256(file) for path, file in actual.items()}
    expected["MANIFEST.csv"] = _sha256(article / "MANIFEST.csv")
    assert declared == expected


def test_current_public_contract_supersedes_conflicting_files() -> None:
    assert not (
        ROOT / "article_data/supplementary_data/Supplementary_Data_5_acute_joint_extremeness.csv"
    ).exists()
    assert not (ROOT / "article_data/main_figures/Figure_2_source_data.csv").exists()
    current = pd.read_csv(
        ROOT
        / "article_data/supplementary_data/Supplementary_Data_5_acute_port_sar_robustness.csv"
    )
    assert len(current) == 91
    assert set(current.loc[current["record_family"].eq("sar_sparse_acquisition"), "publication_uncertainty_label"].dropna()) == {
        "sparse_acquisition_robustness_range"
    }


def test_public_text_has_no_secrets_private_paths_or_workflow_labels() -> None:
    private_path = r"[A-Za-z]" + ":" + r"\\" + "|/" + "Users/|App" + "Data"
    internal_label = r"\bD0(?:" + "44|45|46" + r")\b|Role0?[1-9]|approval[_ -]gate"
    forbidden = re.compile(
        r"eyJ[a-zA-Z0-9_-]{20,}\."
        + "|"
        + private_path
        + "|"
        + internal_label
        + r"|(?:FIRMS|MAP)[_ -]?KEY\s*[:=]",
        re.IGNORECASE,
    )
    findings = []
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        if path.relative_to(ROOT).as_posix() in {
            "src/common.py",
            "tests/test_repository_contract.py",
        }:
            continue
        if path.suffix.lower() not in {".py", ".md", ".csv", ".json", ".yml", ".yaml", ".cff"}:
            continue
        if forbidden.search(path.read_text(encoding="utf-8-sig", errors="ignore")):
            findings.append(path.relative_to(ROOT).as_posix())
    assert findings == []


def test_repository_workflow_smoke_run(tmp_path: Path) -> None:
    declared = json.loads((ROOT / "expected_outputs.json").read_text(encoding="utf-8"))
    result = reproduce(
        ROOT / "data",
        ROOT / "article_data",
        tmp_path / "output",
        replicates=2,
    )
    assert result["status"] == "PASS"
    assert result["publication_interval_run"] is False
    assert (tmp_path / "output/reproduction_manifest.json").is_file()
    actual = {
        path.relative_to(tmp_path / "output").as_posix()
        for path in (tmp_path / "output").rglob("*")
        if path.is_file()
    }
    assert actual == set(declared["expected_generated_files"])


def test_superseded_callable_modules_are_not_published() -> None:
    for relative in (
        "src/common.py",
        "src/figure_1.py",
        "src/supplementary_figures.py",
    ):
        assert not (ROOT / relative).exists()
