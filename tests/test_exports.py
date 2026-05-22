import json

from colourshift.core.algorithms import ColourShiftResult
from colourshift.core.config import Config
from colourshift.io import build_solution_payload, create_comparison_image, save_solution_json


def test_build_solution_payload_serialises_candidates():
    payload = build_solution_payload(
        "#950000",
        "#964301",
        [ColourShiftResult(rgb=[1.0, 0.0, 0.5], delta_e=12.34)],
    )

    assert payload == {
        "base_color": {
            "hex": "#950000",
            "rgb": [149 / 255, 0.0, 0.0],
        },
        "surround_color": {
            "hex": "#964301",
            "rgb": [150 / 255, 67 / 255, 1 / 255],
        },
        "candidates": [
            {
                "hex": "#ff007f",
                "rgb": [1.0, 0.0, 0.5],
                "deltaE": 12.34,
            },
        ],
        "search": {},
    }


def test_build_solution_payload_includes_search_metadata():
    payload = build_solution_payload(
        "#950000",
        "#964301",
        [ColourShiftResult(rgb=[1.0, 0.0, 0.5], delta_e=12.34)],
        mode="maximal-surround-shift",
        config=Config(rgb_grid_points=2, min_delta=5.0, max_candidates=1),
    )

    assert payload["search"] == {
        "mode": "maximal-surround-shift",
        "config": {
            "viewing_condition": "Average",
            "background_luminance": 20.0,
            "adapting_luminance": 64.0,
            "rgb_grid_points": 2,
            "min_delta": 5.0,
            "max_candidates": 1,
        },
    }


def test_save_solution_json_writes_payload(tmp_path):
    path = tmp_path / "solution.json"

    save_solution_json(
        path,
        "#000000",
        "#ffffff",
        [ColourShiftResult(rgb=[0.0, 1.0, 0.0], delta_e=3)],
    )

    assert json.loads(path.read_text(encoding="utf-8"))["candidates"] == [
        {
            "hex": "#00ff00",
            "rgb": [0.0, 1.0, 0.0],
            "deltaE": 3.0,
        }
    ]


def test_create_comparison_image_draws_expected_regions():
    image = create_comparison_image(
        "#ff0000",
        "#00ff00",
        "#0000ff",
        size=(100, 50),
        box_size=5,
    )

    assert image.size == (100, 50)
    assert image.getpixel((10, 10)) == (0, 255, 0)
    assert image.getpixel((75, 10)) == (0, 0, 255)
    assert image.getpixel((25, 25)) == (255, 0, 0)
    assert image.getpixel((75, 25)) == (255, 0, 0)
