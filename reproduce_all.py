from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from src.common import (  # noqa: E402
    TABLE_FILES,
    file_manifest,
    security_scan,
    sha256,
    validate_data_package,
    write_json,
)
from src.figure_1 import reproduce as reproduce_figure_1  # noqa: E402
from src.figure_2 import reproduce as reproduce_figure_2  # noqa: E402
from src.statistical_analysis import reproduce as reproduce_statistics  # noqa: E402
from src.supplementary_figures import reproduce_all as reproduce_supplementary  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_empty_output(output_root: Path) -> None:
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"Output directory must be absent or empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)


def _validate_and_copy_tables(data_root: Path, output_root: Path) -> list[dict[str, Any]]:
    expected = json.loads((PACKAGE_ROOT / "expected_outputs.json").read_text(encoding="utf-8"))["supplementary_tables"]
    rows = []
    for index, rel in enumerate(TABLE_FILES, start=1):
        source = data_root / rel
        target = output_root / "supplementary_tables" / f"Supplementary_Table_{index:02d}.csv"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        import csv

        with target.open("r", encoding="utf-8-sig", newline="") as stream:
            table = list(csv.reader(stream))
        shape = [len(table) - 1, len(table[0]) if table else 0]
        declared = expected[str(index)]
        checks = {
            "shape": shape == declared["shape"],
            "header": (table[0] if table else []) == declared["header"],
            "sha256": sha256(target) == declared["sha256"],
            "nonempty_header": bool(table and all(table[0])),
        }
        if not all(checks.values()):
            raise ValueError(f"Supplementary Table {index} validation failed: {checks}")
        rows.append({"table": index, "source": rel, "output": target.relative_to(output_root).as_posix(), "shape": shape, "sha256": sha256(target), "checks": checks})
    return rows


def _figure_output_inventory(artifacts: list[dict[str, Any]], output_root: Path) -> list[dict[str, Any]]:
    inventory = []
    for artifact in artifacts:
        name = artifact["name"]
        if artifact.get("status") == "WITHHELD_PRE_ACCEPTANCE":
            inventory.append(
                {
                    "figure": name,
                    "status": "WITHHELD_PRE_ACCEPTANCE",
                    "outputs": {},
                    "reason": artifact["reason"],
                    "source_sha256": artifact["source_sha256"],
                }
            )
            continue
        outputs = artifact.get("outputs", {})
        required = {"pdf", "svg", "png_300dpi", "png_600dpi"}
        if set(outputs) != required:
            raise ValueError(f"{name} output contract changed: {sorted(outputs)}")
        checked = {}
        for kind, record in outputs.items():
            path = output_root / record["path"]
            if not path.is_file():
                raise FileNotFoundError(f"Generated figure output missing: {path}")
            actual = sha256(path)
            if actual != record["sha256"]:
                raise ValueError(f"Generated figure checksum mismatch: {path}")
            checked[kind] = {
                "path": record["path"],
                "bytes": path.stat().st_size,
                "sha256": actual,
            }
        inventory.append(
            {
                "figure": name,
                "status": "GENERATED",
                "outputs": checked,
                "source_sha256": artifact["source_sha256"],
                "render_mode": artifact["render_mode"],
            }
        )
    return inventory


def _write_markdown_qa(output_root: Path, payload: dict[str, Any]) -> None:
    qa_dir = output_root / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    figures = payload["figures"]
    tables = payload["supplementary_tables"]
    rendered_figures = sum(
        row.get("status") != "WITHHELD_PRE_ACCEPTANCE" for row in figures
    )
    lines = [
        "# Lightweight reproducibility report",
        "",
        f"- Status: `{payload['status']}`",
        f"- Source-data directory SHA-256: `{payload['data_package']['directory_canonical_sha256']}`",
        f"- Figure records validated: {len(figures)}/9",
        f"- Figures rendered: {rendered_figures}/9",
        f"- Supplementary tables validated and copied: {len(tables)}/10",
        "- Scientific model runs: 0",
        f"- Port–SAR bootstrap replicates: {payload['statistics']['port_sar']['bootstrap_replicates']}",
        f"- NO2 bootstrap replicates: {payload['statistics']['no2']['bootstrap_replicates_per_domain']} across {payload['statistics']['no2']['analytical_domains']} analytical domains",
        "- Data downloads: 0",
        "",
        "## Figure paths",
        "",
    ]
    for row in figures:
        lines.append(f"- {row['name']}: panels {','.join(row['panel_ids'])}; {row['render_mode']}; source rows={row['source_rows']}; source SHA-256 `{row['source_sha256']}`")
    lines.extend(
        [
            "",
            "## Reproduction boundary",
            "",
            "This command recomputes the reported five-year port–SAR point estimates and 5,000-replicate bootstrap from shared daily/eligible-date aggregate inputs, then redraws the aggregate/source-data figures. It does not rerun upstream Sentinel-1 preprocessing, xView3 inference, PortWatch acquisition, TROPOMI/ERA5 processing, population weighting or atmospheric models. Supplementary Figure 2 is recorded as excluded from public rendering because its source table does not redistribute the underlying optical/SAR pixel chips.",
            "",
            "Vessel-like labels remain an activity proxy rather than verified vessel totals. NO2 values remain population-weighted tropospheric column anomalies rather than surface concentration, personal exposure or health effects. No causal effect is claimed.",
        ]
    )
    (qa_dir / "REPRODUCIBILITY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    inventory = payload["figure_output_inventory"]
    ilines = [
        "# Generated figure output inventory",
        "",
        "Rendered manuscript figures are generated from the shared source tables and plotting code.",
        "",
    ]
    for row in inventory:
        ilines.append(
            f"- {row['figure']}: {row['status']}; generated outputs={len(row['outputs'])}."
        )
    (qa_dir / "FIGURE_OUTPUT_INVENTORY.md").write_text(
        "\n".join(ilines) + "\n", encoding="utf-8"
    )


def reproduce(data_root: Path, output_root: Path) -> dict[str, Any]:
    _ensure_empty_output(output_root)
    started = _now()
    data_validation = validate_data_package(data_root)
    statistics = reproduce_statistics(data_root, output_root)
    figure_1 = reproduce_figure_1(data_root, output_root)
    figure_2 = reproduce_figure_2(data_root, output_root)
    supplementary = reproduce_supplementary(data_root, output_root)
    figures = [figure_1, figure_2, *supplementary]
    if len(figures) != 9:
        raise RuntimeError(f"Expected nine figures, got {len(figures)}")
    tables = _validate_and_copy_tables(data_root, output_root)
    inventory = _figure_output_inventory(figures, output_root)
    package_security_findings = security_scan(PACKAGE_ROOT)
    if package_security_findings:
        raise RuntimeError(f"Security/anonymity scan findings: {package_security_findings}")
    payload: dict[str, Any] = {
        "status": "LIGHTWEIGHT_REPRODUCTION_COMPLETE",
        "started_at_utc": started,
        "completed_at_utc": _now(),
        "command_boundary": "port–SAR statistical recomputation plus aggregate/source-data figure redraw and table validation",
        "data_package": data_validation,
        "statistics": {
            "port_sar": {
                "status": statistics["status"],
                "analysis": statistics["analysis"],
                "bootstrap_replicates": 5000,
                "verification_against_shared_results": statistics[
                    "verification_against_shared_results"
                ],
                "outputs": statistics["outputs"],
            },
            "no2": {
                "status": statistics["no2"]["status"],
                "analysis": statistics["no2"]["analysis"],
                "analytical_domains": 4,
                "bootstrap_replicates_per_domain": 5000,
                "verification_against_shared_summary": statistics["no2"][
                    "verification_against_shared_summary"
                ],
                "outputs": statistics["no2"]["outputs"],
            },
        },
        "figures": figures,
        "supplementary_tables": tables,
        "figure_output_inventory": inventory,
        "security_findings": package_security_findings,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "execution_counts": {"downloads": 0, "earth_engine_calls": 0, "xview3_runs": 0, "scientific_models": 0, "bootstrap_runs": 5, "bootstrap_replicates": 25000},
    }
    _write_markdown_qa(output_root, payload)
    write_json(output_root / "qa/REPRODUCIBILITY_REPORT.json", payload)
    write_json(output_root / "qa/FIGURE_OUTPUT_INVENTORY.json", inventory)
    write_json(output_root / "logs/reproduction_run.json", payload)
    output_manifest = file_manifest(output_root, exclude={"OUTPUT_MANIFEST.json"})
    write_json(output_root / "OUTPUT_MANIFEST.json", {"files": output_manifest})
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Reproduce figures and validate supplementary tables from the shared source data.")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = reproduce(args.data_root.resolve(), args.output_root.resolve())
    print(json.dumps({"status": result["status"], "figures": len(result["figures"]), "tables": len(result["supplementary_tables"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
