from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageChops, ImageStat


DATA_DIRECTORY_SHA256 = "db14fd7d9797e1c433a2e34f7307d1b6c61a87b26031b024e2bcda0e534f5fd3"
MAIN_SOURCE_FILES = [
    "files/main_figures/Figure_1_source_data.csv",
    "files/main_figures/Figure_2_source_data.csv",
]
SUPPLEMENTARY_SOURCE_FILES = [
    f"files/supplementary_figures/Supplementary_Figure_{i}_source_data.csv"
    for i in range(1, 8)
]
TABLE_FILES = [
    f"files/supplementary_tables/Supplementary_Table_{i:02d}.csv"
    for i in range(1, 11)
]
STATISTICAL_INPUT_FILES = [
    "files/statistical_inputs/khor_fakkan_port_daily.csv",
    "files/statistical_inputs/khor_fakkan_sar_eligible_dates.csv",
    "files/statistical_inputs/no2_daily_aggregates.csv",
    "files/statistical_inputs/no2_may_june_summary.csv",
]
STATISTICAL_PARAMETER_FILES = [
    "files/statistical_inputs/analysis_parameters.json",
    "files/statistical_inputs/no2_analysis_parameters.json",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_shape(path: Path) -> tuple[int, int, list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    if not rows:
        return 0, 0, []
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError(f"Ragged CSV: {path}")
    return len(rows) - 1, width, rows[0]


def canonical_directory_sha256(data_root: Path) -> tuple[str, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(data_root.rglob("*")):
        if not path.is_file() or path.name == "CHECKSUMS.sha256":
            continue
        rows.append(
            {
                "path": path.relative_to(data_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    canonical = "".join(
        f"{row['path']}\t{row['bytes']}\t{row['sha256']}\n" for row in rows
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest(), rows


def validate_data_package(data_root: Path) -> dict[str, Any]:
    if not data_root.is_dir():
        raise FileNotFoundError(f"Data package directory does not exist: {data_root}")
    required = [
        "CHECKSUMS.sha256",
        "FILE_MANIFEST.json",
        "FIGURE_TABLE_CROSSWALK.csv",
        *MAIN_SOURCE_FILES,
        *SUPPLEMENTARY_SOURCE_FILES,
        *TABLE_FILES,
        *STATISTICAL_INPUT_FILES,
        *STATISTICAL_PARAMETER_FILES,
    ]
    missing = [rel for rel in required if not (data_root / rel).is_file()]
    if missing:
        raise FileNotFoundError(f"Required source-data input missing: {missing}")

    checksum_errors: list[str] = []
    for line in (data_root / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split("  ", 1)
        path = data_root / rel
        if not path.is_file():
            checksum_errors.append(f"missing:{rel}")
        elif sha256(path) != expected:
            checksum_errors.append(f"sha256:{rel}")
    if checksum_errors:
        raise ValueError(f"Source-data checksum failure: {checksum_errors}")

    directory_sha, members = canonical_directory_sha256(data_root)
    if directory_sha != DATA_DIRECTORY_SHA256:
        raise ValueError(
            "Source-data canonical directory SHA-256 mismatch: "
            f"expected {DATA_DIRECTORY_SHA256}, got {directory_sha}"
        )

    shapes = {}
    for rel in [
        *MAIN_SOURCE_FILES,
        *SUPPLEMENTARY_SOURCE_FILES,
        *TABLE_FILES,
        *STATISTICAL_INPUT_FILES,
    ]:
        rows, cols, header = csv_shape(data_root / rel)
        shapes[rel] = {"rows": rows, "columns": cols, "header": header}
    return {
        "directory_canonical_sha256": directory_sha,
        "canonical_member_count": len(members),
        "checksum_errors": checksum_errors,
        "shapes": shapes,
    }


def configure_style(hash_salt: str) -> None:
    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 6.7,
            "axes.titlesize": 7.0,
            "axes.labelsize": 6.7,
            "xtick.labelsize": 5.8,
            "ytick.labelsize": 5.8,
            "legend.fontsize": 5.6,
            "axes.linewidth": 0.55,
            "lines.linewidth": 0.9,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": hash_salt,
            "savefig.facecolor": "white",
        }
    )


def save_figure(fig: plt.Figure, name: str, output_root: Path) -> dict[str, Any]:
    figure_dir = output_root / "figures"
    high_dir = output_root / "figures_600dpi"
    figure_dir.mkdir(parents=True, exist_ok=True)
    high_dir.mkdir(parents=True, exist_ok=True)
    targets = {
        "pdf": figure_dir / f"{name}.pdf",
        "svg": figure_dir / f"{name}.svg",
        "png_300dpi": figure_dir / f"{name}.png",
        "png_600dpi": high_dir / f"{name}.png",
    }
    fixed_pdf_metadata = {
        "Title": name,
        "Author": "Zhenbei Zhang and collaborators",
        "Creator": "Hormuz reproducibility package",
        "CreationDate": None,
        "ModDate": None,
    }
    fixed_svg_metadata = {"Title": name, "Date": "2026-08-18"}
    fig.savefig(targets["pdf"], metadata=fixed_pdf_metadata, facecolor="white")
    fig.savefig(targets["svg"], metadata=fixed_svg_metadata, facecolor="white")
    fig.savefig(targets["png_300dpi"], dpi=300, facecolor="white")
    fig.savefig(targets["png_600dpi"], dpi=600, facecolor="white")
    inches = tuple(float(v) for v in fig.get_size_inches())
    plt.close(fig)
    return {
        "name": name,
        "size_inches": list(inches),
        "outputs": {
            key: {
                "path": path.relative_to(output_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for key, path in targets.items()
        },
    }


def copy_source(source: Path, output_root: Path) -> Path:
    target = output_root / "source_data" / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    if sha256(target) != sha256(source):
        raise RuntimeError(f"Source-data copy hash mismatch: {source.name}")
    return target


def compare_png(reference: Path, reproduced: Path) -> dict[str, Any]:
    with Image.open(reference).convert("RGB") as ref, Image.open(reproduced).convert("RGB") as got:
        same_size = ref.size == got.size
        if not same_size:
            return {
                "same_size": False,
                "reference_pixels": list(ref.size),
                "reproduced_pixels": list(got.size),
                "mean_absolute_channel_difference": None,
                "maximum_channel_difference": None,
                "exact_pixel_fraction": 0.0,
            }
        diff = ImageChops.difference(ref, got)
        stat = ImageStat.Stat(diff)
        histogram = diff.histogram()
        total_channel_values = ref.width * ref.height * 3
        nonzero = sum(histogram[channel * 256 + value] for channel in range(3) for value in range(1, 256))
        return {
            "same_size": True,
            "reference_pixels": list(ref.size),
            "reproduced_pixels": list(got.size),
            "mean_absolute_channel_difference": sum(stat.mean) / 3.0,
            "maximum_channel_difference": max(diff.getextrema()[i][1] for i in range(3)),
            "exact_channel_value_fraction": 1.0 - (nonzero / total_channel_values),
        }


TEXT_SUFFIXES = {".py", ".md", ".txt", ".csv", ".json", ".yml", ".yaml"}
SECURITY_PATTERNS = {
    # Match an actual drive-prefixed path without embedding a project-local
    # example that would make this scanner flag its own source code.
    "windows_absolute_path": re.compile(r"(?i)\b[A-Z]:[\\/]"),
    "email": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "credential_assignment": re.compile(r"(?i)\b(?:token|password|passwd|api[_-]?key|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    "fake_repository_or_doi": re.compile(r"(?i)(?:doi:\s*10\.XXXX|zenodo\.org/record/PLACEHOLDER|github\.com/PLACEHOLDER)"),
}


def security_scan(package_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    excluded_parts = {"reproduced_outputs", "qa_reproduction_runs"}
    for path in sorted(package_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in excluded_parts for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for label, pattern in SECURITY_PATTERNS.items():
            if pattern.search(text):
                findings.append({"path": path.relative_to(package_root).as_posix(), "category": label})
    return findings


def file_manifest(root: Path, *, exclude: set[str] | None = None) -> list[dict[str, Any]]:
    excluded = exclude or set()
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in excluded:
            continue
        rows.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256(path)})
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
