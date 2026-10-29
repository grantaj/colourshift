#!/usr/bin/env python3
"""Baseline the Watercolour Effect colour-optimisation problem.

This script deliberately does not run the numerical optimiser. It probes the
authoritative forward model directly to separate four questions:

1. Does the model reproduce the published Devinck et al. colour conditions?
2. Does predicted shift grow monotonically with raw contour contrast?
3. At fixed luminance and fixed chroma, which inner/outer hue pairs are favoured?
4. Does the model respond specifically to a double-contour configuration?

The output directory contains CSV tables, a JSON summary, and lightweight SVG
plots that require no plotting dependency.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.stats import spearmanr

from colourshift.watercolour.colourimetry import (
    is_unit_gamut,
    sRGB_to_uvY,
    uvY_to_sRGB,
)
from colourshift.watercolour.figure4 import reproduce_figure4
from colourshift.watercolour.model import RGB, predict_watercolour
from colourshift.watercolour.published import (
    DEVINCK_2005_BACKGROUND_LUMINANCE,
    DEVINCK_2005_INNER_LUMINANCE,
    DEVINCK_2005_OUTER_LUMINANCE,
)

FIELD: RGB = (1.0, 1.0, 1.0)
REFERENCE_INNER: RGB = (1.0, 0.72, 0.0)
REFERENCE_OUTER: RGB = (0.32, 0.36, 0.85)
CORNER_INNER: RGB = (0.0, 0.0, 1.0)
CORNER_OUTER: RGB = (1.0, 1.0, 0.0)

INNER_RELATIVE_Y = DEVINCK_2005_INNER_LUMINANCE / DEVINCK_2005_BACKGROUND_LUMINANCE
OUTER_RELATIVE_Y = DEVINCK_2005_OUTER_LUMINANCE / DEVINCK_2005_BACKGROUND_LUMINANCE


def _rgb_tuple(values: np.ndarray | Iterable[float]) -> RGB:
    return tuple(float(value) for value in values)  # type: ignore[return-value]


def _uv(rgb: RGB) -> np.ndarray:
    return sRGB_to_uvY(np.asarray(rgb, dtype=float))[0]


def _uv_distance(a: RGB, b: RGB) -> float:
    return float(np.linalg.norm(_uv(a) - _uv(b)))


def _prediction_row(inner: RGB, outer: RGB) -> dict[str, object]:
    prediction = predict_watercolour(
        field_rgb=FIELD,
        inner_rgb=inner,
        outer_rgb=outer,
    )
    predicted_rgb = np.asarray(prediction.predicted_rgb_unclipped, dtype=float)
    inner_chroma = _uv_distance(inner, FIELD)
    efficiency = (
        prediction.chromatic_shift_uv / inner_chroma if inner_chroma > np.finfo(float).eps else None
    )
    return {
        "inner_rgb": list(inner),
        "outer_rgb": list(outer),
        "chromatic_shift_uv": prediction.chromatic_shift_uv,
        "transfer_efficiency": efficiency,
        "relative_luminance_shift": prediction.relative_luminance_shift,
        "predicted_rgb_unclipped": list(prediction.predicted_rgb_unclipped),
        "predicted_rgb_in_unit_gamut": is_unit_gamut(predicted_rgb),
        "inner_chroma_uv": inner_chroma,
        "contour_separation_uv": _uv_distance(inner, outer),
    }


def published_condition_baseline() -> dict[str, object]:
    measurements = reproduce_figure4()
    rows = [asdict(measurement) for measurement in measurements]
    predicted = np.asarray([item.predicted_shift_ratio for item in measurements])
    observed = np.asarray([item.published_shift_ratio for item in measurements])
    rank = spearmanr(predicted, observed)

    return {
        "rows": rows,
        "summary": {
            "spearman_rank_correlation": float(rank.statistic),
            "spearman_pvalue": float(rank.pvalue),
            "pearson_correlation": float(np.corrcoef(predicted, observed)[0, 1]),
            "mean_absolute_shift_ratio_error": float(np.mean(np.abs(predicted - observed))),
            "mean_absolute_angle_error_deg": float(
                np.mean([abs(item.angle_difference_error_deg) for item in measurements])
            ),
        },
    }


def _interpolate_rgb(a: RGB, b: RGB, amount: float) -> RGB:
    left = np.asarray(a, dtype=float)
    right = np.asarray(b, dtype=float)
    return _rgb_tuple((1.0 - amount) * left + amount * right)


def _hue_angle(rgb: RGB, centre_uv: np.ndarray) -> float:
    vector = _uv(rgb) - centre_uv
    return float(math.atan2(vector[1], vector[0]))


def _rgb_on_uv_circle(
    centre_uv: np.ndarray,
    radius: float,
    angle: float,
    relative_y: float,
) -> RGB:
    uv = centre_uv + radius * np.array([math.cos(angle), math.sin(angle)])
    return _rgb_tuple(uvY_to_sRGB(float(uv[0]), float(uv[1]), relative_y))


def _maximum_radius_for_directions(
    centre_uv: np.ndarray,
    directions: list[tuple[float, float]],
    *,
    upper: float = 0.25,
) -> float:
    low = 0.0
    high = upper

    def feasible(radius: float) -> bool:
        for angle, relative_y in directions:
            rgb = np.asarray(
                _rgb_on_uv_circle(centre_uv, radius, angle, relative_y),
                dtype=float,
            )
            if not is_unit_gamut(rgb):
                return False
        return True

    while feasible(high) and high < 1.0:
        low = high
        high *= 2.0

    for _ in range(40):
        middle = (low + high) / 2.0
        if feasible(middle):
            low = middle
        else:
            high = middle
    return 0.995 * low


def contrast_sweep(steps: int) -> list[dict[str, object]]:
    centre_uv = _uv(FIELD)
    rows: list[dict[str, object]] = []

    blue_angle = _hue_angle(CORNER_INNER, centre_uv)
    yellow_angle = _hue_angle(CORNER_OUTER, centre_uv)
    fixed_y_max_radius = _maximum_radius_for_directions(
        centre_uv,
        [
            (blue_angle, INNER_RELATIVE_Y),
            (yellow_angle, OUTER_RELATIVE_Y),
        ],
    )

    for index in range(steps):
        amount = index / (steps - 1)

        inner = _interpolate_rgb(FIELD, CORNER_INNER, amount)
        outer = _interpolate_rgb(FIELD, CORNER_OUTER, amount)
        row = {
            "mode": "rgb_to_corner",
            "amount": amount,
            **_prediction_row(inner, outer),
        }
        rows.append(row)

        radius = fixed_y_max_radius * amount
        fixed_inner = _rgb_on_uv_circle(
            centre_uv,
            radius,
            blue_angle,
            INNER_RELATIVE_Y,
        )
        fixed_outer = _rgb_on_uv_circle(
            centre_uv,
            radius,
            yellow_angle,
            OUTER_RELATIVE_Y,
        )
        fixed_row = {
            "mode": "fixed_luminance_chroma",
            "amount": amount,
            "chroma_radius_uv": radius,
            "maximum_chroma_radius_uv": fixed_y_max_radius,
            **_prediction_row(fixed_inner, fixed_outer),
        }
        rows.append(fixed_row)

    return rows


def _full_circle_radius(
    centre_uv: np.ndarray,
    *,
    angle_samples: int = 360,
) -> float:
    directions = []
    for index in range(angle_samples):
        angle = 2.0 * math.pi * index / angle_samples
        directions.append((angle, INNER_RELATIVE_Y))
        directions.append((angle, OUTER_RELATIVE_Y))
    return _maximum_radius_for_directions(centre_uv, directions)


def hue_map(hue_steps: int) -> dict[str, object]:
    centre_uv = _uv(FIELD)
    radius = _full_circle_radius(centre_uv)
    rows: list[dict[str, object]] = []
    scores = np.empty((hue_steps, hue_steps), dtype=float)

    colours: list[tuple[float, RGB, RGB]] = []
    for index in range(hue_steps):
        angle = 2.0 * math.pi * index / hue_steps
        inner = _rgb_on_uv_circle(centre_uv, radius, angle, INNER_RELATIVE_Y)
        outer = _rgb_on_uv_circle(centre_uv, radius, angle, OUTER_RELATIVE_Y)
        colours.append((angle, inner, outer))

    for inner_index, (inner_angle, inner, _) in enumerate(colours):
        for outer_index, (outer_angle, _, outer) in enumerate(colours):
            prediction = _prediction_row(inner, outer)
            score = float(prediction["chromatic_shift_uv"])
            scores[inner_index, outer_index] = score
            rows.append(
                {
                    "inner_hue_deg": math.degrees(inner_angle),
                    "outer_hue_deg": math.degrees(outer_angle),
                    "chroma_radius_uv": radius,
                    **prediction,
                }
            )

    maximum_index = np.unravel_index(int(np.argmax(scores)), scores.shape)
    best_inner = rows[maximum_index[0] * hue_steps + maximum_index[1]]

    return {
        "field_uv": centre_uv.tolist(),
        "inner_relative_y": INNER_RELATIVE_Y,
        "outer_relative_y": OUTER_RELATIVE_Y,
        "chroma_radius_uv": radius,
        "hue_steps": hue_steps,
        "rows": rows,
        "summary": {
            "minimum_shift_uv": float(np.min(scores)),
            "maximum_shift_uv": float(np.max(scores)),
            "mean_shift_uv": float(np.mean(scores)),
            "coefficient_of_variation": float(np.std(scores) / np.mean(scores)),
            "best_inner_hue_deg": best_inner["inner_hue_deg"],
            "best_outer_hue_deg": best_inner["outer_hue_deg"],
        },
    }


def control_conditions() -> list[dict[str, object]]:
    pairs = {
        "reference": (REFERENCE_INNER, REFERENCE_OUTER),
        "corner_blue_yellow": (CORNER_INNER, CORNER_OUTER),
    }
    rows: list[dict[str, object]] = []

    for pair_name, (inner, outer) in pairs.items():
        conditions = {
            "proper_double_contour": (inner, outer),
            "same_as_inner": (inner, inner),
            "same_as_outer": (outer, outer),
            "outer_is_field": (inner, FIELD),
            "inner_is_field": (FIELD, outer),
            "swapped": (outer, inner),
            "both_are_field": (FIELD, FIELD),
        }
        for condition_name, (candidate_inner, candidate_outer) in conditions.items():
            rows.append(
                {
                    "pair": pair_name,
                    "condition": condition_name,
                    **_prediction_row(candidate_inner, candidate_outer),
                }
            )
    return rows


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            serialised = {
                key: json.dumps(value) if isinstance(value, (list, dict)) else value
                for key, value in row.items()
            }
            writer.writerow(serialised)


def _write_line_plot(path: Path, rows: list[dict[str, object]]) -> None:
    width = 900
    height = 520
    left = 80
    right = 30
    top = 30
    bottom = 70
    plot_width = width - left - right
    plot_height = height - top - bottom

    modes = ["rgb_to_corner", "fixed_luminance_chroma"]
    grouped = {mode: [row for row in rows if row["mode"] == mode] for mode in modes}
    maximum = max(float(row["chromatic_shift_uv"]) for row in rows)
    maximum = maximum if maximum > 0 else 1.0

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        (f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="black"/>'),
        (
            f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" '
            f'y2="{height - bottom}" stroke="black"/>'
        ),
        (
            f'<text x="{width / 2}" y="{height - 20}" text-anchor="middle" '
            'font-family="sans-serif" font-size="16">contrast / chroma fraction</text>'
        ),
        (
            f'<text x="20" y="{height / 2}" transform="rotate(-90 20 '
            f'{height / 2})" text-anchor="middle" font-family="sans-serif" '
            'font-size="16">predicted Δu′v′</text>'
        ),
    ]

    colours = {
        "rgb_to_corner": "#7b3294",
        "fixed_luminance_chroma": "#008837",
    }
    labels = {
        "rgb_to_corner": "RGB interpolation to blue/yellow cube corners",
        "fixed_luminance_chroma": "fixed luminance, increasing chroma",
    }

    for mode_index, mode in enumerate(modes):
        points = []
        for row in grouped[mode]:
            x = left + float(row["amount"]) * plot_width
            y = top + (1.0 - float(row["chromatic_shift_uv"]) / maximum) * plot_height
            points.append(f"{x:.2f},{y:.2f}")
        lines.append(
            f'<polyline fill="none" stroke="{colours[mode]}" stroke-width="3" '
            f'points="{" ".join(points)}"/>'
        )
        legend_y = top + 22 + 24 * mode_index
        lines.append(
            f'<line x1="{left + 15}" y1="{legend_y}" x2="{left + 45}" '
            f'y2="{legend_y}" stroke="{colours[mode]}" stroke-width="3"/>'
        )
        lines.append(
            f'<text x="{left + 55}" y="{legend_y + 5}" font-family="sans-serif" '
            f'font-size="14">{labels[mode]}</text>'
        )

    for tick in range(6):
        fraction = tick / 5
        x = left + fraction * plot_width
        y = top + (1.0 - fraction) * plot_height
        lines.append(
            f'<text x="{x}" y="{height - bottom + 24}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="12">{fraction:.1f}</text>'
        )
        lines.append(
            f'<text x="{left - 10}" y="{y + 4}" text-anchor="end" '
            f'font-family="sans-serif" font-size="12">{maximum * fraction:.3f}</text>'
        )

    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_hue_map_svg(path: Path, result: dict[str, object]) -> None:
    hue_steps = int(result["hue_steps"])
    rows = result["rows"]
    assert isinstance(rows, list)
    scores = np.asarray([float(row["chromatic_shift_uv"]) for row in rows])
    minimum = float(np.min(scores))
    maximum = float(np.max(scores))
    span = maximum - minimum if maximum > minimum else 1.0

    size = 720
    margin = 75
    plot = size - 2 * margin
    cell = plot / hue_steps

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">',
        '<rect width="100%" height="100%" fill="white"/>',
        (
            f'<text x="{size / 2}" y="{size - 18}" text-anchor="middle" '
            'font-family="sans-serif" font-size="16">outer contour hue (degrees)</text>'
        ),
        (
            f'<text x="20" y="{size / 2}" transform="rotate(-90 20 '
            f'{size / 2})" text-anchor="middle" font-family="sans-serif" '
            'font-size="16">inner contour hue (degrees)</text>'
        ),
    ]

    for inner_index in range(hue_steps):
        for outer_index in range(hue_steps):
            row = rows[inner_index * hue_steps + outer_index]
            score = float(row["chromatic_shift_uv"])
            normalised = (score - minimum) / span
            lightness = 92.0 - 62.0 * normalised
            x = margin + outer_index * cell
            y = margin + inner_index * cell
            lines.append(
                f'<rect x="{x:.3f}" y="{y:.3f}" width="{cell + 0.3:.3f}" '
                f'height="{cell + 0.3:.3f}" fill="hsl(220 70% {lightness:.2f}%)"/>'
            )

    for degrees in (0, 90, 180, 270, 360):
        fraction = degrees / 360.0
        position = margin + fraction * plot
        lines.append(
            f'<text x="{position:.2f}" y="{size - margin + 24}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="12">{degrees}</text>'
        )
        lines.append(
            f'<text x="{margin - 10}" y="{position + 4:.2f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="12">{degrees}</text>'
        )

    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(output_dir: Path, *, hue_steps: int, contrast_steps: int) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    published = published_condition_baseline()
    contrast = contrast_sweep(contrast_steps)
    hues = hue_map(hue_steps)
    controls = control_conditions()

    _write_csv(output_dir / "published_conditions.csv", published["rows"])
    _write_csv(output_dir / "contrast_sweep.csv", contrast)
    _write_csv(output_dir / "hue_map.csv", hues["rows"])
    _write_csv(output_dir / "controls.csv", controls)
    _write_line_plot(output_dir / "contrast_sweep.svg", contrast)
    _write_hue_map_svg(output_dir / "hue_map.svg", hues)

    report = {
        "purpose": (
            "Diagnostic baseline for distinguishing optimiser bugs, objective/domain "
            "problems, forward-model limitations, and genuine contrast dominance."
        ),
        "field_rgb": list(FIELD),
        "published_conditions": published,
        "contrast_sweep": {
            "rows": contrast,
        },
        "fixed_luminance_fixed_chroma_hue_map": hues,
        "double_contour_controls": {
            "rows": controls,
        },
    }
    path = output_dir / "baseline_report.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return path


def _print_summary(report_path: Path) -> None:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    published = report["published_conditions"]["summary"]
    hues = report["fixed_luminance_fixed_chroma_hue_map"]["summary"]
    print(f"Wrote {report_path}")
    print(f"Published-condition rank correlation: {published['spearman_rank_correlation']:.3f}")
    print(
        "Fixed-luminance/fixed-chroma hue-map range: "
        f"{hues['minimum_shift_uv']:.6f} .. {hues['maximum_shift_uv']:.6f}"
    )
    print(
        "Best controlled hue pair: "
        f"inner {hues['best_inner_hue_deg']:.1f}°, "
        f"outer {hues['best_outer_hue_deg']:.1f}°"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Baseline the WCE colour-optimisation problem without running DE."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("watercolour-baseline"),
        help="output directory (default: watercolour-baseline)",
    )
    parser.add_argument(
        "--hue-steps",
        type=int,
        default=24,
        help="number of hue samples per contour (default: 24)",
    )
    parser.add_argument(
        "--contrast-steps",
        type=int,
        default=21,
        help="number of samples in each contrast sweep (default: 21)",
    )
    args = parser.parse_args()

    if args.hue_steps < 4:
        parser.error("--hue-steps must be at least 4")
    if args.contrast_steps < 2:
        parser.error("--contrast-steps must be at least 2")

    report_path = write_report(
        args.output,
        hue_steps=args.hue_steps,
        contrast_steps=args.contrast_steps,
    )
    _print_summary(report_path)


if __name__ == "__main__":
    main()
