"""Regenerate public inventories and checksums after source-data updates."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tabular_shape(path: Path) -> tuple[str, str]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader, [])
            rows = sum(1 for _ in reader)
        return str(rows), str(len(header))
    if path.suffix.lower() in {".geojson", ".json"}:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(payload, dict) and isinstance(payload.get("features"), list):
                properties = set()
                for feature in payload["features"]:
                    properties.update((feature.get("properties") or {}).keys())
                return str(len(payload["features"])), str(len(properties) + 1)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    return "", ""


def unit_for(field: str) -> str:
    name = field.lower()
    if "date" in name or "time" in name:
        return "UTC/ISO 8601 or source-native date label"
    if "mol_m2" in name or "mol m-2" in name:
        return "mol m-2"
    if "density_per_100_km2" in name:
        return "detections per 100 km2"
    if name.endswith("_km2"):
        return "km2"
    if "percent" in name or name.endswith("_pct"):
        return "percent"
    if "fraction" in name or "score" in name:
        return "dimensionless"
    if "count" in name or "calls_per_day" in name:
        return "count or calls per UTC day"
    return "source-native or not applicable"


def update_field_dictionary(data_root: Path) -> None:
    path = data_root / "FIELD_DICTIONARY.csv"
    columns = [
        "file",
        "field",
        "storage_type",
        "unit",
        "missing_value_semantics",
        "description",
    ]
    if path.exists():
        existing = pd.read_csv(path, dtype=str, keep_default_na=False)
        existing = existing[existing["file"].map(lambda item: (data_root / item).is_file())]
    else:
        existing = pd.DataFrame(columns=columns)
    present = set(zip(existing["file"], existing["field"]))
    additions: list[dict[str, str]] = []
    for source in sorted((data_root / "files").rglob("*.csv")):
        relative = source.relative_to(data_root).as_posix()
        frame = pd.read_csv(source, nrows=200, low_memory=False)
        for field in frame.columns:
            if (relative, field) in present:
                continue
            additions.append(
                {
                    "file": relative,
                    "field": field,
                    "storage_type": str(frame[field].dtype),
                    "unit": unit_for(field),
                    "missing_value_semantics": (
                        "Blank/null means missing or not applicable; numeric zero remains "
                        "an observed zero unless the named field states otherwise."
                    ),
                    "description": "Public processed field; see the source-specific method and crosswalk.",
                }
            )
    combined = pd.concat([existing, pd.DataFrame(additions, columns=columns)], ignore_index=True)
    combined = combined[columns].sort_values(["file", "field"], kind="stable")
    combined.to_csv(path, index=False, lineterminator="\n")


def write_article_inventory(article_root: Path) -> None:
    content = sorted(
        path
        for path in article_root.rglob("*")
        if path.is_file() and path.name not in {"MANIFEST.csv", "CHECKSUMS.sha256"}
    )
    rows = []
    for path in content:
        row_count, column_count = tabular_shape(path)
        rows.append(
            {
                "path": path.relative_to(article_root).as_posix(),
                "rows": row_count,
                "columns": column_count,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    pd.DataFrame(rows).to_csv(article_root / "MANIFEST.csv", index=False, lineterminator="\n")
    checksum_members = sorted(
        path for path in article_root.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256"
    )
    text = "".join(
        f"{sha256(path)}  {path.relative_to(article_root).as_posix()}\n"
        for path in checksum_members
    )
    (article_root / "CHECKSUMS.sha256").write_text(text, encoding="utf-8", newline="\n")


def write_data_inventory(data_root: Path) -> None:
    sources = sorted(path for path in (data_root / "files").rglob("*") if path.is_file())
    rows = []
    for path in sources:
        row_count, column_count = tabular_shape(path)
        rows.append(
            {
                "path": path.relative_to(data_root).as_posix(),
                "rows": row_count,
                "columns": column_count,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    pd.DataFrame(rows).to_csv(
        data_root / "SOURCE_DATA_INVENTORY.csv", index=False, lineterminator="\n"
    )
    manifest_members = sorted(
        path
        for path in data_root.rglob("*")
        if path.is_file() and path.name not in {"FILE_MANIFEST.json", "CHECKSUMS.sha256"}
    )
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "files": [
            {
                "path": path.relative_to(data_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in manifest_members
        ],
    }
    (data_root / "FILE_MANIFEST.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    checksum_members = sorted(
        path for path in data_root.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256"
    )
    text = "".join(
        f"{sha256(path)}  {path.relative_to(data_root).as_posix()}\n"
        for path in checksum_members
    )
    (data_root / "CHECKSUMS.sha256").write_text(text, encoding="utf-8", newline="\n")


def write_expected_outputs(repository: Path) -> None:
    key_sources = [
        repository / "data/files/statistical_inputs/khor_fakkan_port_daily.csv",
        repository / "data/files/statistical_inputs/no2_full_refit_daily_design.csv",
        repository
        / "data/files/analysis_ready/Supplementary_Data_5_acute_port_sar_robustness.csv",
        repository / "article_data/main_figures/Figure_3_source_data.csv",
        repository / "article_data/main_figures/Figure_4_source_data.csv",
    ]
    payload = {
        "schema_version": "1.0",
        "publication_bootstrap_replicates": 5000,
        "key_sources": {
            path.relative_to(repository).as_posix(): {
                "sha256": sha256(path),
                "shape": list(map(int, tabular_shape(path))),
            }
            for path in key_sources
        },
        "expected_generated_files": [
            "port_sar/port_point_estimates.csv",
            "port_sar/port_block_bootstrap_summary.csv",
            "port_sar/port_sar_validation.json",
            "no2/no2_full_refit_bootstrap_summary.csv",
            "no2/no2_model_diagnostics.csv",
            "no2/no2_population_coverage.csv",
            "no2/no2_reproduction.json",
            "figures/Figure_3_verification.png",
            "figures/Figure_3_verification.pdf",
            "figures/Figure_4_verification.png",
            "figures/Figure_4_verification.pdf",
            "figures/figure_validation.json",
            "reproduction_manifest.json",
        ],
        "excluded_from_public_reproduction": [
            "raw provider downloads",
            "satellite pixel preprocessing",
            "detector inference and weights",
            "coordinate-level detector outputs and spatial opportunity-null rerun",
        ],
    }
    (repository / "expected_outputs.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    data_root = repository / "data"
    update_field_dictionary(data_root)
    write_article_inventory(repository / "article_data")
    write_data_inventory(data_root)
    write_expected_outputs(repository)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
