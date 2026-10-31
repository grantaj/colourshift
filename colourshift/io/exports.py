import json
from dataclasses import asdict
from pathlib import Path

from PIL import Image, ImageDraw

from colourshift.core.algorithms import SearchResult
from colourshift.core.colour_models import rgb_to_hex

NEUTRAL_GREY_HEX = "#808080"


def _colour_payload(rgb):
    if rgb is None:
        return None
    return {"hex": rgb_to_hex(rgb), "rgb": list(rgb)}


def build_search_result_payload(result: SearchResult):
    """Serialise the stable, versioned search-result contract."""
    return {
        "schema": "colourshift-search-result-v1",
        "model": result.model,
        "mode": result.mode,
        "objective": result.objective,
        "config": asdict(result.config),
        "inputs": {
            "base": _colour_payload(result.base_rgb),
            "surround": _colour_payload(result.surround_rgb),
        },
        "candidates": [
            {
                "hex": rgb_to_hex(candidate.rgb),
                "rgb": list(candidate.rgb),
                "total_shift": float(candidate.total_shift),
                "chromatic_shift": float(candidate.chromatic_shift),
            }
            for candidate in result.candidates
        ],
    }


def save_search_result_json(path, result: SearchResult):
    payload = build_search_result_payload(result)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def create_comparison_image(
    left_base_hex,
    left_surround_hex,
    right_base_hex,
    right_surround_hex,
    size=(300, 150),
    box_size=20,
):
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)

    left_center = (size[0] // 4, size[1] // 2)
    right_center = (3 * size[0] // 4, size[1] // 2)

    draw.rectangle([0, 0, size[0] // 2, size[1]], fill=left_surround_hex)
    draw.rectangle(
        [
            left_center[0] - box_size,
            left_center[1] - box_size,
            left_center[0] + box_size,
            left_center[1] + box_size,
        ],
        fill=left_base_hex,
    )

    draw.rectangle([size[0] // 2, 0, size[0], size[1]], fill=right_surround_hex)
    draw.rectangle(
        [
            right_center[0] - box_size,
            right_center[1] - box_size,
            right_center[0] + box_size,
            right_center[1] + box_size,
        ],
        fill=right_base_hex,
    )

    return image


def save_comparison_image(
    path,
    left_base_hex,
    left_surround_hex,
    right_base_hex,
    right_surround_hex,
):
    image = create_comparison_image(
        left_base_hex,
        left_surround_hex,
        right_base_hex,
        right_surround_hex,
    )
    image.save(path)
