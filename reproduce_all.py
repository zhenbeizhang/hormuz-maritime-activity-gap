"""Run the public processed-input reproduction workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from src.analysis.no2_full_refit_bootstrap import BOOTSTRAP_REPLICATES, run as run_no2
from src.analysis.port_sar_uncertainty import run as run_port_sar
from src.figures.article_figures import run as run_figures


def reproduce(
    data_root: Path,
    article_data: Path,
    output_root: Path,
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> dict[str, object]:
    if replicates <= 0:
        raise ValueError("replicates must be positive")
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"output directory must be absent or empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    port = run_port_sar(data_root, output_root / "port_sar", replicates)
    no2 = run_no2(
        data_root / "files/statistical_inputs/no2_full_refit_daily_design.csv",
        output_root / "no2",
        replicates,
    )
    figures = run_figures(article_data, output_root / "figures")
    report = {
        "status": "PASS",
        "replicates_per_prespecified_setting": int(replicates),
        "publication_interval_run": bool(replicates == BOOTSTRAP_REPLICATES),
        "port_sar": port,
        "no2": no2,
        "figures": figures,
        "boundary": (
            "processed-input reproduction; raw provider downloads, satellite "
            "preprocessing, detector inference and coordinate-level spatial null excluded"
        ),
    }
    (output_root / "reproduction_manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    repository = Path(__file__).resolve().parent
    parser.add_argument("--data-root", type=Path, default=repository / "data")
    parser.add_argument("--article-data", type=Path, default=repository / "article_data")
    parser.add_argument("--output-root", type=Path, default=repository / "reproduced_outputs")
    parser.add_argument("--replicates", type=int, default=BOOTSTRAP_REPLICATES)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    result = reproduce(
        args.data_root.resolve(),
        args.article_data.resolve(),
        args.output_root.resolve(),
        replicates=args.replicates,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
