from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from src.common import configure_style, copy_source, save_figure, sha256


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
from src.plotting import supplementary_base as base
from src.plotting import supplementary_refined as refined


EXPECTED_SHAPES = {
    1: (68, 33),
    2: (7, 11),
    3: (3439, 12),
    4: (42, 22),
    5: (110, 56),
    6: (213, 9),
    7: (33, 41),
}
EXPECTED_PANELS = {1: 3, 2: 3, 3: 2, 4: 5, 5: 3, 6: 3, 7: 3}
PANEL_IDS = {
    1: ["a", "b", "c"],
    2: ["a", "b", "c"],
    3: ["a", "b"],
    4: ["a", "b", "c", "d", "e"],
    5: ["a", "b", "c"],
    6: ["a", "b", "c"],
    7: ["a", "b", "c"],
}


def _withheld_figure_2() -> dict[str, Any]:
    return {
        "name": "Supplementary_Figure_2",
        "outputs": {},
        "status": "WITHHELD_PRE_ACCEPTANCE",
        "render_mode": "not_rendered_third_party_pixel_chips_not_redistributed",
        "reason": (
            "The seven-row source CSV documents geometry and imagery lineage but intentionally "
            "omits the third-party optical and SAR pixel chips. No display-ready manuscript "
            "figure or placeholder is stored in the public repository."
        ),
    }


def reproduce(number: int, data_root: Path, output_root: Path) -> dict[str, Any]:
    if number not in range(1, 8):
        raise ValueError(f"Supplementary figure number out of range: {number}")
    source_path = data_root / f"files/supplementary_figures/Supplementary_Figure_{number}_source_data.csv"
    source = pd.read_csv(source_path)
    if source.shape != EXPECTED_SHAPES[number]:
        raise ValueError(f"Supplementary Figure {number} packaged source shape changed: {source.shape}")
    configure_style(f"public-lightweight-supplementary-{number}")
    base.configure_style()
    plt.rcParams["svg.hashsalt"] = f"public-lightweight-supplementary-{number}"
    if number == 2:
        artifact = _withheld_figure_2()
    else:
        builders = {
            1: refined.figure1,
            3: base.figure3,
            4: base.figure4,
            5: refined.figure5,
            6: base.figure6,
            7: refined.figure7,
        }
        figure = builders[number](source)
        artifact = save_figure(figure, f"Supplementary_Figure_{number}", output_root)
        artifact["render_mode"] = "source_data_redraw_no_estimation"
    copied = copy_source(source_path, output_root)
    artifact.update(
        {
            "panels": EXPECTED_PANELS[number],
            "panel_ids": PANEL_IDS[number],
            "source_rows": len(source),
            "source_columns": len(source.columns),
            "source_sha256": sha256(source_path),
            "copied_source_sha256": sha256(copied),
            "scientific_estimation_runs": 0,
        }
    )
    return artifact


def reproduce_all(data_root: Path, output_root: Path) -> list[dict[str, Any]]:
    return [reproduce(number, data_root, output_root) for number in range(1, 8)]


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--figure", type=int)
    args = parser.parse_args()
    result = reproduce(args.figure, args.data_root, args.output_root) if args.figure else reproduce_all(args.data_root, args.output_root)
    print(json.dumps(result, indent=2, sort_keys=True))
