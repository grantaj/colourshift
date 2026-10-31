import json

from colourshift.core.algorithms import (
    MODE_MAXIMAL_SURROUND_SHIFT,
    MODEL_ID,
    OBJECTIVE_CHROMATIC,
    ColourShiftCandidate,
    SearchResult,
)
from colourshift.core.config import Config
from colourshift.io import (
    build_search_result_payload,
    create_comparison_image,
    save_search_result_json,
)


def example_result():
    return SearchResult(
        MODEL_ID,
        MODE_MAXIMAL_SURROUND_SHIFT,
        OBJECTIVE_CHROMATIC,
        Config(rgb_grid_points=2, min_delta=5, max_candidates=1),
        (149 / 255, 0.0, 0.0),
        (150 / 255, 67 / 255, 1 / 255),
        (ColourShiftCandidate((1.0, 0.0, 0.5), 12.34, 10.5),),
    )


def test_search_payload_is_complete_and_versioned():
    payload = build_search_result_payload(example_result())
    assert payload["schema"] == "colourshift-search-result-v1"
    assert payload["model"] == MODEL_ID
    assert payload["mode"] == MODE_MAXIMAL_SURROUND_SHIFT
    assert payload["objective"] == OBJECTIVE_CHROMATIC
    assert payload["config"]["background_luminous_factor"] == 20.0
    assert payload["inputs"]["base"]["hex"] == "#950000"
    assert payload["inputs"]["surround"]["hex"] == "#964301"
    assert payload["candidates"] == [
        {
            "hex": "#ff007f",
            "rgb": [1.0, 0.0, 0.5],
            "total_shift": 12.34,
            "chromatic_shift": 10.5,
        }
    ]


def test_save_search_result_json_creates_parent_and_trailing_newline(tmp_path):
    path = tmp_path / "nested" / "result.json"
    save_search_result_json(path, example_result())
    assert json.loads(path.read_text())["model"] == MODEL_ID
    assert path.read_text().endswith("\n")


def test_create_comparison_image_draws_expected_regions():
    image = create_comparison_image(
        "#ff0000", "#00ff00", "#ff00ff", "#0000ff", size=(100, 50), box_size=5
    )
    assert image.size == (100, 50)
    assert image.getpixel((10, 10)) == (0, 255, 0)
    assert image.getpixel((75, 10)) == (0, 0, 255)
    assert image.getpixel((25, 25)) == (255, 0, 0)
    assert image.getpixel((75, 25)) == (255, 0, 255)
