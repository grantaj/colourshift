import numpy as np

from colourshift.watercolour.stimuli import (
    WatercolourStimulus,
    annular_masks,
    render_annular_stimulus,
)


def test_masks_partition_image():
    config = WatercolourStimulus(size_px=128, radius_px=30, gap_px=2)
    masks = annular_masks(config)
    total = sum(
        mask.astype(int)
        for mask in (
            masks.field,
            masks.inner,
            masks.gap,
            masks.outer,
            masks.background,
        )
    )
    assert np.all(total == 1)


def test_render_places_requested_colours():
    config = WatercolourStimulus(
        size_px=128,
        radius_px=30,
        field_rgb=(0.9, 0.9, 0.9),
        inner_rgb=(1.0, 0.5, 0.0),
        outer_rgb=(0.2, 0.0, 0.4),
    )
    image = render_annular_stimulus(config)
    masks = annular_masks(config)
    assert np.allclose(image[masks.field][0], config.field_rgb)
    assert np.allclose(image[masks.inner][0], config.inner_rgb)
    assert np.allclose(image[masks.outer][0], config.outer_rgb)


def test_waviness_changes_boundary_without_changing_shape():
    smooth = annular_masks(WatercolourStimulus(size_px=128, radius_px=30))
    wavy = annular_masks(
        WatercolourStimulus(
            size_px=128,
            radius_px=30,
            waviness_amplitude_px=3,
            waviness_cycles=12,
        )
    )
    assert smooth.field.shape == wavy.field.shape
    assert not np.array_equal(smooth.field, wavy.field)
