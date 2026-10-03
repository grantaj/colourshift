"""Qualitative reproduction of Cohen-Duwek & Spitzer (2019), Figure 3.

Figure 3 is a qualitative demonstration rather than a numerically specified
experiment. The paper identifies the contour families (orange/purple,
red/cyan, and achromatic) and shows both contour orders, but it does not publish
the exact RGB values or raster dimensions used for that figure. Accordingly,
the fixtures below use representative sRGB values matched to the published
figure and validate the *direction* of filling-in, not pixel equality.

The acceptance criterion follows the paper's qualitative claim: the predicted
interior shift should point toward the inner-contour colour (or, for the
achromatic pair, change luminance in the same direction as the inner contour).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

from ._edge_model import (
    EdgeModelConfig,
    opponent_to_rgb,
    rgb_to_opponent,
    run_edge_model,
)
from .stimuli import (
    StarWatercolourStimulus,
    render_star_stimulus,
    star_masks,
)


@dataclass(frozen=True)
class Figure3Case:
    label: str
    description: str
    stimulus: StarWatercolourStimulus
    kind: str


@dataclass(frozen=True)
class Figure3Measurement:
    label: str
    description: str
    kind: str
    physical_field_rgb: tuple[float, float, float]
    predicted_field_rgb_unclipped: tuple[float, float, float]
    chromatic_shift_magnitude: float
    assimilation_cosine: float | None
    luminance_shift: float
    passes_direction_check: bool


def figure3_cases() -> tuple[Figure3Case, ...]:
    """Return the six reversed-contour conditions shown in Figure 3."""
    white = (1.0, 1.0, 1.0)
    grey = (0.50, 0.50, 0.50)

    # Figure 3 does not report exact digital colour values. These saturated
    # representatives capture the visible hue classes without pretending that
    # the original MATLAB inputs can be recovered from the publication image.
    orange_yellow = (1.00, 0.72, 0.00)
    blue_purple = (0.32, 0.36, 0.85)
    cyan = (0.15, 0.78, 0.92)
    red = (0.75, 0.02, 0.02)
    black = (0.0, 0.0, 0.0)

    common = dict(
        size_px=256,
        outer_radius_px=76.0,
        inner_radius_ratio=0.62,
        points=7,
        inner_width_px=4.0,
        outer_width_px=4.0,
    )

    return (
        Figure3Case(
            "A-I",
            "orange/yellow inner contour, blue/purple outer contour",
            StarWatercolourStimulus(
                **common,
                background_rgb=white,
                field_rgb=white,
                inner_rgb=orange_yellow,
                outer_rgb=blue_purple,
            ),
            "chromatic",
        ),
        Figure3Case(
            "A-II",
            "blue/purple inner contour, orange/yellow outer contour",
            StarWatercolourStimulus(
                **common,
                background_rgb=white,
                field_rgb=white,
                inner_rgb=blue_purple,
                outer_rgb=orange_yellow,
            ),
            "chromatic",
        ),
        Figure3Case(
            "B-I",
            "cyan inner contour, red outer contour",
            StarWatercolourStimulus(
                **common,
                background_rgb=white,
                field_rgb=white,
                inner_rgb=cyan,
                outer_rgb=red,
            ),
            "chromatic",
        ),
        Figure3Case(
            "B-II",
            "red inner contour, cyan outer contour",
            StarWatercolourStimulus(
                **common,
                background_rgb=white,
                field_rgb=white,
                inner_rgb=red,
                outer_rgb=cyan,
            ),
            "chromatic",
        ),
        Figure3Case(
            "C-I",
            "white inner contour, black outer contour on grey",
            StarWatercolourStimulus(
                **common,
                background_rgb=grey,
                field_rgb=grey,
                inner_rgb=white,
                outer_rgb=black,
            ),
            "achromatic",
        ),
        Figure3Case(
            "C-II",
            "black inner contour, white outer contour on grey",
            StarWatercolourStimulus(
                **common,
                background_rgb=grey,
                field_rgb=grey,
                inner_rgb=black,
                outer_rgb=white,
            ),
            "achromatic",
        ),
    )


def _opponent_triplet(rgb: tuple[float, float, float], transform: str) -> np.ndarray:
    sample = np.asarray(rgb, dtype=float).reshape(1, 1, 3)
    return rgb_to_opponent(sample, transform)[0, 0]


def _rgb_triplet(opponent: np.ndarray, transform: str) -> np.ndarray:
    sample = np.asarray(opponent, dtype=float).reshape(1, 1, 3)
    return opponent_to_rgb(sample, transform)[0, 0]


def evaluate_figure3_case(
    case: Figure3Case,
    model_config: EdgeModelConfig | None = None,
    *,
    inset_px: float = 12.0,
    cosine_threshold: float = 0.75,
) -> tuple[Figure3Measurement, np.ndarray, np.ndarray]:
    """Run one Figure 3 condition and evaluate its qualitative direction."""
    model_config = model_config or EdgeModelConfig(opponent_transform="van_de_sande")
    stimulus_rgb = render_star_stimulus(case.stimulus)
    result = run_edge_model(stimulus_rgb, model_config)

    masks = star_masks(case.stimulus)
    deep_interior = masks.field & (distance_transform_edt(masks.field) >= inset_px)
    if not np.any(deep_interior):
        raise ValueError("inset_px leaves no interior pixels to measure")

    predicted_opponent = np.mean(result.opponent_prediction[deep_interior], axis=0)
    physical_opponent = _opponent_triplet(case.stimulus.field_rgb, model_config.opponent_transform)
    inner_opponent = _opponent_triplet(case.stimulus.inner_rgb, model_config.opponent_transform)
    predicted_rgb_unclipped = _rgb_triplet(predicted_opponent, model_config.opponent_transform)

    luminance_shift = float(predicted_opponent[0] - physical_opponent[0])
    chromatic_shift = predicted_opponent[1:] - physical_opponent[1:]
    chromatic_shift_magnitude = float(np.linalg.norm(chromatic_shift))

    if case.kind == "chromatic":
        target = inner_opponent[1:] - physical_opponent[1:]
        target_norm = float(np.linalg.norm(target))
        if target_norm == 0 or chromatic_shift_magnitude == 0:
            assimilation_cosine = None
            passes = False
        else:
            assimilation_cosine = float(
                np.dot(chromatic_shift, target) / (chromatic_shift_magnitude * target_norm)
            )
            passes = assimilation_cosine >= cosine_threshold
    elif case.kind == "achromatic":
        assimilation_cosine = None
        target_luminance_shift = float(inner_opponent[0] - physical_opponent[0])
        passes = (
            abs(luminance_shift) > np.finfo(float).eps
            and luminance_shift * target_luminance_shift > 0
        )
    else:
        raise ValueError(f"unknown Figure 3 case kind: {case.kind!r}")

    measurement = Figure3Measurement(
        label=case.label,
        description=case.description,
        kind=case.kind,
        physical_field_rgb=tuple(float(v) for v in case.stimulus.field_rgb),
        predicted_field_rgb_unclipped=tuple(float(v) for v in predicted_rgb_unclipped),
        chromatic_shift_magnitude=chromatic_shift_magnitude,
        assimilation_cosine=assimilation_cosine,
        luminance_shift=luminance_shift,
        passes_direction_check=passes,
    )
    return measurement, stimulus_rgb, result.predicted_rgb


def reproduce_figure3(
    model_config: EdgeModelConfig | None = None,
) -> list[Figure3Measurement]:
    """Evaluate all six qualitative Figure 3 conditions."""
    return [evaluate_figure3_case(case, model_config)[0] for case in figure3_cases()]


def _save_rgb(path: Path, image: np.ndarray) -> None:
    data = np.rint(np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)
    Image.fromarray(data, mode="RGB").save(path)


def write_figure3_bundle(
    output_dir: str | Path,
    model_config: EdgeModelConfig | None = None,
) -> Path:
    """Write stimuli, predictions, and a machine-readable Gate 1A report."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    model_config = model_config or EdgeModelConfig(opponent_transform="van_de_sande")

    measurements: list[Figure3Measurement] = []
    for case in figure3_cases():
        measurement, stimulus, prediction = evaluate_figure3_case(case, model_config)
        measurements.append(measurement)
        stem = case.label.lower().replace("-", "_")
        _save_rgb(output / f"{stem}_stimulus.png", stimulus)
        _save_rgb(output / f"{stem}_prediction.png", prediction)

    report = {
        "source": "Cohen-Duwek & Spitzer (2019), Figure 3",
        "scope": "qualitative directional reproduction",
        "opponent_transform": model_config.opponent_transform,
        "exact_rgb_values_published": False,
        "acceptance": (
            "chromatic interior shift points toward inner-contour hue; "
            "achromatic luminance shift has the inner-contour sign"
        ),
        "all_pass": all(m.passes_direction_check for m in measurements),
        "measurements": [asdict(m) for m in measurements],
    }
    report_path = output / "figure3_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report_path
