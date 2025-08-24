# Centralized configuration (defaults chosen to preserve existing behavior)
from dataclasses import dataclass

@dataclass
class Config:
    vc_name: str = "Average"   # Viewing conditions name for CIECAM02
    Y_b: float = 20.0          # Luminance of background
    L_A: float = 64.0          # Adapting field luminance
    rgb_grid_points: int = 12  # number of grid points per RGB channel
    min_delta: float = 10.0    # minimal separation in CAM02-UCS
    max_candidates: int = 8    # top-N candidates to keep
