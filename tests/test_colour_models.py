import pytest

from colourshift.core.colour_models import hex_to_rgb, is_valid_JMh, rgb_to_hex


def test_hex_to_rgb_normalises_channel_values():
    assert hex_to_rgb("#804020") == pytest.approx([128 / 255, 64 / 255, 32 / 255])


@pytest.mark.parametrize("hex_color", ["804020", "#804020"])
def test_hex_to_rgb_accepts_optional_hash(hex_color):
    assert hex_to_rgb(hex_color) == pytest.approx([128 / 255, 64 / 255, 32 / 255])


@pytest.mark.parametrize("hex_color", ["#123", "#1234567", "#zzzzzz", 123])
def test_hex_to_rgb_rejects_invalid_values(hex_color):
    with pytest.raises(ValueError):
        hex_to_rgb(hex_color)


def test_rgb_to_hex_formats_lowercase_hex_triplet():
    assert rgb_to_hex([1.0, 0.5, 0.0]) == "#ff7f00"


@pytest.mark.parametrize(
    "rgb", [[1.2, 0.0, 0.0], [-0.1, 0.0, 0.0], [float("nan"), 0.0, 0.0], [1.0, 0.0]]
)
def test_rgb_to_hex_rejects_invalid_values(rgb):
    with pytest.raises(ValueError):
        rgb_to_hex(rgb)


def test_is_valid_jmh_rejects_non_finite_and_out_of_range_values():
    assert is_valid_JMh(50, 25, 180)
    assert not is_valid_JMh(float("nan"), 25, 180)
    assert not is_valid_JMh(101, 25, 180)
    assert not is_valid_JMh(50, 101, 180)
    assert not is_valid_JMh(50, 25, 361)
