import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Numerical settings for Zhu-Luo CAM16 simultaneous-contrast searches."""

    viewing_condition: str = "Average"
    background_luminous_factor: float = 20.0
    adapting_luminance: float = 23.0
    rgb_grid_points: int = 12
    min_delta: float = 1.0
    max_candidates: int = 3

    def __post_init__(self):
        if not self.viewing_condition:
            raise ValueError("viewing_condition must not be empty")
        if (
            not math.isfinite(self.background_luminous_factor)
            or self.background_luminous_factor < 0
        ):
            raise ValueError("background_luminous_factor must be finite and non-negative")
        if not math.isfinite(self.adapting_luminance) or self.adapting_luminance < 0:
            raise ValueError("adapting_luminance must be finite and non-negative")
        if self.rgb_grid_points < 2:
            raise ValueError("rgb_grid_points must be at least 2")
        if not math.isfinite(self.min_delta) or self.min_delta < 0:
            raise ValueError("min_delta must be finite and non-negative")
        if self.max_candidates < 1:
            raise ValueError("max_candidates must be at least 1")


DEFAULT_CONFIG = Config()
