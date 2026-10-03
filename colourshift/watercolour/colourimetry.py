"""CIE 1976 u'v'Y and sRGB conversion helpers for WCE reproduction.

Cohen-Duwek & Spitzer (2019) state that the Devinck et al. CIE Lu'v'
stimulus colours were converted to sRGB, fed through the model, then converted
back to CIE Lu'v'.  They do not state whether out-of-gamut sRGB values were
clipped, nor whether the experimental display white was chromatically adapted
to D65.  This module therefore makes both choices explicit.

The default Figure 4 reproduction uses *extended* sRGB (no clipping) and no
chromatic adaptation: this is the least destructive literal conversion and
does not silently alter the published chromaticity/luminance coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# IEC 61966-2-1 / standard sRGB D65 matrices.
XYZ_TO_LINEAR_SRGB = np.array(
    [
        [3.2404542, -1.5371385, -0.4985314],
        [-0.9692660, 1.8760108, 0.0415560],
        [0.0556434, -0.2040259, 1.0572252],
    ],
    dtype=float,
)
LINEAR_SRGB_TO_XYZ = np.linalg.inv(XYZ_TO_LINEAR_SRGB)

D65_XYZ = np.array([0.95047, 1.0, 1.08883], dtype=float)
BRADFORD = np.array(
    [
        [0.8951, 0.2664, -0.1614],
        [-0.7502, 1.7135, 0.0367],
        [0.0389, -0.0685, 1.0296],
    ],
    dtype=float,
)
BRADFORD_INV = np.linalg.inv(BRADFORD)


@dataclass(frozen=True)
class SRGBConversionPolicy:
    """Explicit choices left unspecified by the 2019 reproduction method."""

    adapt_source_white_to_d65: bool = False
    clip_to_unit_gamut: bool = False

    @property
    def name(self) -> str:
        adaptation = "bradford-d65" if self.adapt_source_white_to_d65 else "direct"
        gamut = "clipped" if self.clip_to_unit_gamut else "extended"
        return f"{adaptation}-{gamut}"


def xyY_to_XYZ(x: float, y: float, Y: float) -> np.ndarray:
    """Convert CIE 1931 xy plus luminance Y to XYZ."""
    if not np.isfinite(x) or not np.isfinite(y) or not np.isfinite(Y):
        raise ValueError("x, y, and Y must be finite")
    if y <= 0:
        raise ValueError("y must be positive")
    if Y < 0:
        raise ValueError("Y must be non-negative")
    X = x * Y / y
    Z = (1.0 - x - y) * Y / y
    return np.array([X, Y, Z], dtype=float)


def xyY_to_sRGB(
    x: float,
    y: float,
    Y: float,
    *,
    source_white_xy: tuple[float, float] | None = None,
    policy: SRGBConversionPolicy | None = None,
) -> np.ndarray:
    """Convert CIE 1931 xyY to gamma-encoded sRGB under an explicit policy."""
    policy = policy or SRGBConversionPolicy()
    XYZ = xyY_to_XYZ(x, y, Y)
    if policy.adapt_source_white_to_d65:
        if source_white_xy is None:
            raise ValueError("source_white_xy is required for chromatic adaptation")
        source_white = xyY_to_XYZ(source_white_xy[0], source_white_xy[1], 1.0)
        XYZ = _bradford_matrix(source_white, D65_XYZ) @ XYZ
    rgb = _srgb_encode(XYZ_TO_LINEAR_SRGB @ XYZ)
    if policy.clip_to_unit_gamut:
        rgb = np.clip(rgb, 0.0, 1.0)
    return rgb


def uvY_to_XYZ(u_prime: float, v_prime: float, Y: float) -> np.ndarray:
    """Convert CIE 1976 u'v' plus luminance Y to XYZ."""
    if not np.isfinite(u_prime) or not np.isfinite(v_prime) or not np.isfinite(Y):
        raise ValueError("u', v', and Y must be finite")
    if v_prime <= 0:
        raise ValueError("v' must be positive")
    if Y < 0:
        raise ValueError("Y must be non-negative")

    X = 9.0 * Y * u_prime / (4.0 * v_prime)
    Z = Y * (12.0 - 3.0 * u_prime - 20.0 * v_prime) / (4.0 * v_prime)
    return np.array([X, Y, Z], dtype=float)


def XYZ_to_uv(XYZ: np.ndarray) -> np.ndarray:
    """Convert XYZ to CIE 1976 u'v' chromaticity."""
    X, Y, Z = np.asarray(XYZ, dtype=float)
    denominator = X + 15.0 * Y + 3.0 * Z
    if denominator <= 0 or not np.isfinite(denominator):
        raise ValueError("XYZ does not define a finite positive u'v' chromaticity")
    return np.array([4.0 * X / denominator, 9.0 * Y / denominator], dtype=float)


def _bradford_matrix(source_white_XYZ: np.ndarray, destination_white_XYZ: np.ndarray) -> np.ndarray:
    source = np.asarray(source_white_XYZ, dtype=float)
    destination = np.asarray(destination_white_XYZ, dtype=float)
    source_lms = BRADFORD @ source
    destination_lms = BRADFORD @ destination
    if np.any(source_lms == 0):
        raise ValueError("source white is invalid for Bradford adaptation")
    return BRADFORD_INV @ np.diag(destination_lms / source_lms) @ BRADFORD


def _srgb_encode(linear_rgb: np.ndarray) -> np.ndarray:
    """Sign-preserving sRGB transfer function, allowing extended values."""
    linear_rgb = np.asarray(linear_rgb, dtype=float)
    magnitude = np.abs(linear_rgb)
    encoded_magnitude = np.where(
        magnitude <= 0.0031308,
        12.92 * magnitude,
        1.055 * magnitude ** (1.0 / 2.4) - 0.055,
    )
    return np.sign(linear_rgb) * encoded_magnitude


def _srgb_decode(rgb: np.ndarray) -> np.ndarray:
    """Inverse sign-preserving sRGB transfer function."""
    rgb = np.asarray(rgb, dtype=float)
    magnitude = np.abs(rgb)
    linear_magnitude = np.where(
        magnitude <= 0.04045,
        magnitude / 12.92,
        ((magnitude + 0.055) / 1.055) ** 2.4,
    )
    return np.sign(rgb) * linear_magnitude


def uvY_to_sRGB(
    u_prime: float,
    v_prime: float,
    Y: float,
    *,
    source_white_uv: tuple[float, float] | None = None,
    policy: SRGBConversionPolicy | None = None,
) -> np.ndarray:
    """Convert u'v'Y to gamma-encoded sRGB under an explicit policy."""
    policy = policy or SRGBConversionPolicy()
    XYZ = uvY_to_XYZ(u_prime, v_prime, Y)

    if policy.adapt_source_white_to_d65:
        if source_white_uv is None:
            raise ValueError("source_white_uv is required for chromatic adaptation")
        source_white = uvY_to_XYZ(source_white_uv[0], source_white_uv[1], 1.0)
        XYZ = _bradford_matrix(source_white, D65_XYZ) @ XYZ

    rgb = _srgb_encode(XYZ_TO_LINEAR_SRGB @ XYZ)
    if policy.clip_to_unit_gamut:
        rgb = np.clip(rgb, 0.0, 1.0)
    return rgb


def sRGB_to_uvY(
    rgb: np.ndarray,
    *,
    source_white_uv: tuple[float, float] | None = None,
    policy: SRGBConversionPolicy | None = None,
) -> tuple[np.ndarray, float]:
    """Convert gamma-encoded sRGB back to source-space u'v'Y."""
    policy = policy or SRGBConversionPolicy()
    XYZ = LINEAR_SRGB_TO_XYZ @ _srgb_decode(np.asarray(rgb, dtype=float))

    if policy.adapt_source_white_to_d65:
        if source_white_uv is None:
            raise ValueError("source_white_uv is required for chromatic adaptation")
        source_white = uvY_to_XYZ(source_white_uv[0], source_white_uv[1], 1.0)
        XYZ = np.linalg.inv(_bradford_matrix(source_white, D65_XYZ)) @ XYZ

    return XYZ_to_uv(XYZ), float(XYZ[1])


def is_unit_gamut(rgb: np.ndarray) -> bool:
    """Return whether every sRGB component lies in the display interval [0, 1]."""
    rgb = np.asarray(rgb, dtype=float)
    return bool(np.all(np.isfinite(rgb)) and np.all((rgb >= 0.0) & (rgb <= 1.0)))
