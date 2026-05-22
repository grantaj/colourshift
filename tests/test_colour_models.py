import pytest

from colourshift.core.colour_models import hex_to_rgb, is_valid_JMh, rgb_to_hex


def test_hex_to_rgb_normalises_channel_values():
    assert hex_to_rgb("#804020") == pytest.approx([128 / 255, 64 / 255, 32 / 255])


def test_rgb_to_hex_formats_lowercase_hex_triplet():
    assert rgb_to_hex([1.0, 0.5, 0.0]) == "#ff7f00"


def test_is_valid_jmh_rejects_non_finite_and_out_of_range_values():
    assert is_valid_JMh(50, 25, 180)
    assert not is_valid_JMh(float("nan"), 25, 180)
    assert not is_valid_JMh(101, 25, 180)
    assert not is_valid_JMh(50, 101, 180)
    assert not is_valid_JMh(50, 25, 361)
