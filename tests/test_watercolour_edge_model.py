import numpy as np
import pytest
from scipy.ndimage import distance_transform_edt

from colourshift.watercolour._edge_model import (
    EdgeModelConfig,
    opponent_to_rgb,
    rgb_to_opponent,
    run_edge_model,
)
from colourshift.watercolour.stimuli import (
    WatercolourStimulus,
    annular_masks,
    render_annular_stimulus,
)


def test_opponent_transform_round_trip():
    rng = np.random.default_rng(123)
    image = rng.random((12, 14, 3))
    assert opponent_to_rgb(rgb_to_opponent(image)) == pytest.approx(image)


def test_uniform_image_is_unchanged():
    image = np.full((48, 48, 3), [0.7, 0.6, 0.5])
    result = run_edge_model(image)
    assert result.predicted_rgb == pytest.approx(image, abs=1e-10)
    assert np.allclose(result.combined_weight, 0.0)


def test_default_parameters_match_published_reproduction():
    config = EdgeModelConfig()
    assert config.alpha == 1.0
    assert config.beta == 0.5
    assert config.opponent_transform == "van_de_sande"


def test_canonical_stimulus_generates_interior_shift():
    stimulus = WatercolourStimulus(
        size_px=128,
        radius_px=36,
        inner_width_px=3,
        outer_width_px=3,
    )
    image = render_annular_stimulus(stimulus)
    result = run_edge_model(image)
    masks = annular_masks(stimulus)
    interior = masks.field & (distance_transform_edt(masks.field) >= 10)
    physical = np.mean(result.opponent_input[interior], axis=0)
    predicted = np.mean(result.opponent_prediction[interior], axis=0)

    assert np.max(result.combined_weight) == pytest.approx(1.0)
    assert np.linalg.norm(predicted - physical) > 0.0
