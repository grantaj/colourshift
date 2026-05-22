import json
from pathlib import Path

from PIL import Image, ImageDraw

from colourshift.core.colour_models import hex_to_rgb, rgb_to_hex


def build_solution_payload(base_hex, surround_hex, candidates):
    return {
        "base_color": {
            "hex": base_hex,
            "rgb": hex_to_rgb(base_hex),
        },
        "surround_color": {
            "hex": surround_hex,
            "rgb": hex_to_rgb(surround_hex),
        },
        "candidates": [
            {
                "hex": rgb_to_hex(rgb),
                "rgb": list(rgb),
                "deltaE": float(delta),
            }
            for rgb, delta in candidates
        ],
    }


def save_solution_json(path, base_hex, surround_hex, candidates):
    payload = build_solution_payload(base_hex, surround_hex, candidates)
    Path(path).write_text(json.dumps(payload, indent=4), encoding="utf-8")


def create_comparison_image(
    base_hex, original_surround_hex, candidate_surround_hex, size=(300, 150), box_size=20
):
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)

    left_center = (size[0] // 4, size[1] // 2)
    right_center = (3 * size[0] // 4, size[1] // 2)

    draw.rectangle([0, 0, size[0] // 2, size[1]], fill=original_surround_hex)
    draw.rectangle(
        [
            left_center[0] - box_size,
            left_center[1] - box_size,
            left_center[0] + box_size,
            left_center[1] + box_size,
        ],
        fill=base_hex,
    )

    draw.rectangle([size[0] // 2, 0, size[0], size[1]], fill=candidate_surround_hex)
    draw.rectangle(
        [
            right_center[0] - box_size,
            right_center[1] - box_size,
            right_center[0] + box_size,
            right_center[1] + box_size,
        ],
        fill=base_hex,
    )

    return image


def save_comparison_image(path, base_hex, original_surround_hex, candidate_surround_hex):
    image = create_comparison_image(base_hex, original_surround_hex, candidate_surround_hex)
    image.save(path)
