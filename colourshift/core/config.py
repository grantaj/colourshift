from dataclasses import dataclass


@dataclass
class Config:
    """Numerical settings for CAM02-UCS colour searches."""

    viewing_condition: str = "Average"
    background_luminance: float = 20.0
    adapting_luminance: float = 64.0
    rgb_grid_points: int = 12
    min_delta: float = 10.0
    max_candidates: int = 3


DEFAULT_CONFIG = Config()
