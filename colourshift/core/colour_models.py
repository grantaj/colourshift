import re

import numpy as np

from ._colour_warnings import suppress_colour_optional_dependency_warnings

suppress_colour_optional_dependency_warnings()

import colour  # noqa: E402

HEX_COLOR_PATTERN = re.compile(r"^#?[0-9a-fA-F]{6}$")


def hex_to_rgb(hex_color):
    if not isinstance(hex_color, str) or not HEX_COLOR_PATTERN.fullmatch(hex_color):
        raise ValueError(f"Expected a 6-digit hex colour, got {hex_color!r}")
    hex_color = hex_color.lstrip("#")
    return [int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]


def rgb_to_hex(rgb):
    if len(rgb) != 3:
        raise ValueError(f"Expected 3 RGB channels, got {len(rgb)}")
    if not all(np.isfinite(channel) and 0.0 <= channel <= 1.0 for channel in rgb):
        raise ValueError(f"RGB channels must be finite values between 0 and 1, got {rgb!r}")
    return "#{:02x}{:02x}{:02x}".format(*(int(255 * channel) for channel in rgb))


def rgb_to_XYZ(rgb):
    return colour.sRGB_to_XYZ(rgb)


def is_valid_JMh(J, M, h):
    return (
        np.isfinite(J)
        and np.isfinite(M)
        and np.isfinite(h)
        and 0 <= J <= 100
        and 0 <= M <= 100
        and 0 <= h <= 360
    )
