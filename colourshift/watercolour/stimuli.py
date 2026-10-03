"""Generation of canonical Watercolour Effect stimuli."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

RGB: TypeAlias = tuple[float, float, float]


def _validate_rgb(name: str, rgb: RGB) -> None:
    if len(rgb) != 3 or any(not np.isfinite(v) or not 0.0 <= v <= 1.0 for v in rgb):
        raise ValueError(f"{name} must contain three finite values in [0, 1]")


@dataclass(frozen=True)
class WatercolourStimulus:
    """Parameters for an annular double-contour WCE stimulus.

    ``radius_px`` is the radius of the physically uniform enclosed field. The
    inner contour lies immediately outside it, followed by an optional gap and
    then the outer contour.
    """

    size_px: int = 256
    radius_px: float = 72.0
    inner_width_px: float = 4.0
    outer_width_px: float = 4.0
    gap_px: float = 0.0
    background_rgb: RGB = (1.0, 1.0, 1.0)
    field_rgb: RGB = (1.0, 1.0, 1.0)
    inner_rgb: RGB = (1.0, 0.55, 0.10)
    outer_rgb: RGB = (0.30, 0.08, 0.45)
    centre_x_px: float | None = None
    centre_y_px: float | None = None
    waviness_amplitude_px: float = 0.0
    waviness_cycles: int = 0

    def __post_init__(self) -> None:
        if self.size_px < 16:
            raise ValueError("size_px must be at least 16")
        if self.radius_px <= 0:
            raise ValueError("radius_px must be positive")
        if self.inner_width_px <= 0 or self.outer_width_px <= 0:
            raise ValueError("contour widths must be positive")
        if self.gap_px < 0:
            raise ValueError("gap_px must be non-negative")
        if self.waviness_amplitude_px < 0:
            raise ValueError("waviness_amplitude_px must be non-negative")
        if self.waviness_cycles < 0:
            raise ValueError("waviness_cycles must be non-negative")
        for name in ("background_rgb", "field_rgb", "inner_rgb", "outer_rgb"):
            _validate_rgb(name, getattr(self, name))

        outer_radius = (
            self.radius_px
            + self.inner_width_px
            + self.gap_px
            + self.outer_width_px
            + self.waviness_amplitude_px
        )
        cx = self.centre_x_px if self.centre_x_px is not None else (self.size_px - 1) / 2
        cy = self.centre_y_px if self.centre_y_px is not None else (self.size_px - 1) / 2
        margin = min(cx, cy, self.size_px - 1 - cx, self.size_px - 1 - cy)
        if outer_radius >= margin:
            raise ValueError("stimulus contours do not fit inside the image")


@dataclass(frozen=True)
class StimulusMasks:
    field: np.ndarray
    inner: np.ndarray
    gap: np.ndarray
    outer: np.ndarray
    background: np.ndarray


def annular_masks(config: WatercolourStimulus) -> StimulusMasks:
    """Return masks for a circular or sinusoidally wavy double contour."""
    yy, xx = np.mgrid[: config.size_px, : config.size_px]
    cx = config.centre_x_px if config.centre_x_px is not None else (config.size_px - 1) / 2
    cy = config.centre_y_px if config.centre_y_px is not None else (config.size_px - 1) / 2
    dx = xx - cx
    dy = yy - cy
    r = np.hypot(dx, dy)

    boundary = np.full_like(r, config.radius_px, dtype=float)
    if config.waviness_amplitude_px and config.waviness_cycles:
        theta = np.arctan2(dy, dx)
        boundary = boundary + config.waviness_amplitude_px * np.sin(config.waviness_cycles * theta)

    inner_outer = boundary + config.inner_width_px
    gap_outer = inner_outer + config.gap_px
    outer_outer = gap_outer + config.outer_width_px

    field = r <= boundary
    inner = (r > boundary) & (r <= inner_outer)
    gap = (r > inner_outer) & (r <= gap_outer)
    outer = (r > gap_outer) & (r <= outer_outer)
    background = r > outer_outer
    return StimulusMasks(field=field, inner=inner, gap=gap, outer=outer, background=background)


def render_annular_stimulus(config: WatercolourStimulus) -> np.ndarray:
    """Render a WCE stimulus as a floating-point sRGB image in [0, 1]."""
    masks = annular_masks(config)
    image = np.empty((config.size_px, config.size_px, 3), dtype=float)
    image[:] = config.background_rgb
    image[masks.field] = config.field_rgb
    image[masks.inner] = config.inner_rgb
    image[masks.gap] = config.field_rgb
    image[masks.outer] = config.outer_rgb
    return image


@dataclass(frozen=True)
class StarWatercolourStimulus:
    """Polygonal star stimulus used for qualitative Figure 3 reproduction.

    The 2019 paper does not publish exact RGB values or pixel dimensions for
    Figure 3, so these parameters describe a reproducible representative
    stimulus rather than claiming pixel-for-pixel reconstruction.
    """

    size_px: int = 256
    outer_radius_px: float = 76.0
    inner_radius_ratio: float = 0.62
    points: int = 7
    inner_width_px: float = 4.0
    outer_width_px: float = 4.0
    gap_px: float = 0.0
    background_rgb: RGB = (1.0, 1.0, 1.0)
    field_rgb: RGB = (1.0, 1.0, 1.0)
    inner_rgb: RGB = (1.0, 0.72, 0.0)
    outer_rgb: RGB = (0.32, 0.36, 0.85)

    def __post_init__(self) -> None:
        if self.size_px < 32:
            raise ValueError("size_px must be at least 32")
        if self.outer_radius_px <= 0:
            raise ValueError("outer_radius_px must be positive")
        if not 0.1 <= self.inner_radius_ratio < 1.0:
            raise ValueError("inner_radius_ratio must be in [0.1, 1)")
        if self.points < 3:
            raise ValueError("points must be at least 3")
        if self.inner_width_px <= 0 or self.outer_width_px <= 0:
            raise ValueError("contour widths must be positive")
        if self.gap_px < 0:
            raise ValueError("gap_px must be non-negative")
        for name in ("background_rgb", "field_rgb", "inner_rgb", "outer_rgb"):
            _validate_rgb(name, getattr(self, name))

        margin = (self.size_px - 1) / 2
        required = self.outer_radius_px + self.inner_width_px + self.gap_px + self.outer_width_px
        if required >= margin:
            raise ValueError("star stimulus contours do not fit inside the image")


def _star_field_mask(config: StarWatercolourStimulus) -> np.ndarray:
    centre = (config.size_px - 1) / 2
    vertices: list[tuple[float, float]] = []
    for index in range(config.points * 2):
        angle = -np.pi / 2 + index * np.pi / config.points
        radius = (
            config.outer_radius_px
            if index % 2 == 0
            else config.outer_radius_px * config.inner_radius_ratio
        )
        vertices.append(
            (
                centre + radius * np.cos(angle),
                centre + radius * np.sin(angle),
            )
        )

    image = Image.new("1", (config.size_px, config.size_px), 0)
    ImageDraw.Draw(image).polygon(vertices, fill=1)
    return np.asarray(image, dtype=bool)


def star_masks(config: StarWatercolourStimulus) -> StimulusMasks:
    """Return approximately constant-width contours around a polygonal star."""
    field = _star_field_mask(config)
    distance = distance_transform_edt(~field)

    inner_outer = config.inner_width_px
    gap_outer = inner_outer + config.gap_px
    outer_outer = gap_outer + config.outer_width_px

    inner = (~field) & (distance <= inner_outer)
    gap = (distance > inner_outer) & (distance <= gap_outer)
    outer = (distance > gap_outer) & (distance <= outer_outer)
    background = distance > outer_outer
    return StimulusMasks(
        field=field,
        inner=inner,
        gap=gap,
        outer=outer,
        background=background,
    )


def render_star_stimulus(config: StarWatercolourStimulus) -> np.ndarray:
    """Render a polygonal double-contour WCE star as floating-point sRGB."""
    masks = star_masks(config)
    image = np.empty((config.size_px, config.size_px, 3), dtype=float)
    image[:] = config.background_rgb
    image[masks.field] = config.field_rgb
    image[masks.inner] = config.inner_rgb
    image[masks.gap] = config.field_rgb
    image[masks.outer] = config.outer_rgb
    return image
