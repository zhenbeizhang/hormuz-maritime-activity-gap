from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from shapely import wkt

from src.common import configure_style, copy_source, save_figure, sha256, write_json


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
from src.plotting import main_figure as plotting


def _section(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    return frame.loc[frame["source_section"].eq(name)].drop(columns="source_section").dropna(axis=1, how="all").reset_index(drop=True)


def reproduce(data_root: Path, output_root: Path) -> dict[str, Any]:
    source_path = data_root / "files/main_figures/Figure_1_source_data.csv"
    source = pd.read_csv(source_path)
    if source.shape != (1539, 36):
        raise ValueError(f"Figure 1 packaged source shape changed: {source.shape}")
    waters_raw = _section(source, "map_water")
    waters = gpd.GeoDataFrame(
        waters_raw.drop(columns="geometry_wkt"),
        geometry=waters_raw["geometry_wkt"].map(wkt.loads),
        crs="EPSG:4326",
    )
    ports_raw = _section(source, "map_port")
    ports = gpd.GeoDataFrame(
        ports_raw,
        geometry=gpd.points_from_xy(ports_raw["longitude"], ports_raw["latitude"]),
        crs="EPSG:4326",
    )
    portwatch = _section(source, "portwatch_screen")
    sar = _section(source, "sar_scene")
    land = gpd.read_file(PACKAGE_ROOT / "assets/regional_land_context.geojson")
    checks = {
        "six_waters": len(waters) == 6,
        "five_port_reference_points": len(ports) == 5,
        "portwatch_rows_168": len(portwatch) == 168,
        "portwatch_candidates_24": portwatch["candidate_id"].nunique() == 24,
        "sar_rows_1360": len(sar) == 1360,
        "sar_waters_6": sar["aoi_id"].nunique() == 6,
        "fold1_only": set(sar["fold"]) == {"B4_fold1"},
        "scene_coordinates_absent": not any(c in source.columns for c in ["target_lon", "target_lat", "vessel_id"]),
    }
    if not all(checks.values()):
        raise ValueError(f"Figure 1 input contract failed: {[k for k, v in checks.items() if not v]}")

    configure_style("public-lightweight-figure-1")
    plotting.configure()
    plt.rcParams["svg.hashsalt"] = "public-lightweight-figure-1"
    data = {"waters": waters, "ports": ports, "pw": portwatch, "sar": sar, "land": land}
    fig = plt.figure(figsize=(plotting.FIG_W, plotting.FIG1_H))
    gs = fig.add_gridspec(
        2,
        2,
        width_ratios=[0.39, 0.61],
        height_ratios=[0.54, 0.46],
        left=0.045,
        right=0.98,
        bottom=0.045,
        top=0.91,
        wspace=0.27,
        hspace=0.25,
    )
    plotting.draw_map(fig.add_subplot(gs[0, 0]), data)
    plotting.draw_portwatch(fig.add_subplot(gs[0, 1]), portwatch)
    plotting.draw_sar_strips(fig.add_subplot(gs[1, :]), sar)
    artifact = save_figure(fig, "Figure_1", output_root)
    copied = copy_source(source_path, output_root)
    artifact.update(
        {
            "panels": 3,
            "panel_ids": ["a", "b", "c"],
            "source_rows": len(source),
            "source_columns": len(source.columns),
            "source_sha256": sha256(source_path),
            "copied_source_sha256": sha256(copied),
            "checks": checks,
            "render_mode": "source_data_redraw_with_declared_context_coastline_asset",
        }
    )
    write_json(output_root / "qa/Figure_1_reproduction.json", artifact)
    write_json(
        output_root / "logs/Figure_1_render.json",
        {
            "figure": "Figure_1",
            "status": "render_complete",
            "source_sha256": artifact["source_sha256"],
            "checks": checks,
            "outputs": artifact["outputs"],
        },
    )
    return artifact


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(reproduce(args.data_root, args.output_root), indent=2, sort_keys=True))

