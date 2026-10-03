"""Internal edge/diffusion engine for Watercolour Effect colour drive.

This reproduces the Cohen-Duwek & Spitzer (2019) edge-triggered filling-in
pipeline. It is intentionally internal: physical geometry is handled by
`colourshift.watercolour.model`, the single public WCE forward model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter, zoom

from .diffusion import divergence, forward_gradient, solve_poisson_dirichlet

VAN_DE_SANDE_OPPONENT_MATRIX = np.array(
    [
        [0.2989, 0.5870, 0.1140],
        [1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0), 0.0],
        [1.0 / np.sqrt(6.0), 1.0 / np.sqrt(6.0), -2.0 / np.sqrt(6.0)],
    ],
    dtype=float,
)
WANDELL_OPPONENT_MATRIX = np.array(
    [
        [0.2814, 0.6938, 0.0638],
        [-0.0971, 0.1458, -0.0250],
        [-0.0930, -0.2529, 0.4665],
    ],
    dtype=float,
)
OPPONENT_MATRICES = {
    "van_de_sande": VAN_DE_SANDE_OPPONENT_MATRIX,
    "wandell": WANDELL_OPPONENT_MATRIX,
}


@dataclass(frozen=True)
class EdgeModelConfig:
    alpha: float = 1.0
    beta: float = 0.5
    pyramid_levels: int = 5
    pyramid_blur_sigma_px: float = 1.0
    diffusion_coefficient: float = 1.0
    opponent_transform: str = "van_de_sande"

    def __post_init__(self) -> None:
        if self.alpha <= self.beta or self.beta < 0:
            raise ValueError("model requires alpha > beta >= 0")
        if self.pyramid_levels < 1:
            raise ValueError("pyramid_levels must be positive")
        if self.pyramid_blur_sigma_px <= 0:
            raise ValueError("pyramid_blur_sigma_px must be positive")
        if self.diffusion_coefficient <= 0:
            raise ValueError("diffusion_coefficient must be positive")
        if self.opponent_transform not in OPPONENT_MATRICES:
            raise ValueError("opponent_transform must be 'van_de_sande' or 'wandell'")


@dataclass(frozen=True)
class EdgeModelResult:
    input_rgb: np.ndarray
    predicted_rgb: np.ndarray
    opponent_input: np.ndarray
    opponent_prediction: np.ndarray
    combined_weight: np.ndarray
    channel_weights: np.ndarray
    triggers_x: np.ndarray
    triggers_y: np.ndarray
    source_terms: np.ndarray


def _opponent_matrix(transform: str) -> np.ndarray:
    try:
        return OPPONENT_MATRICES[transform]
    except KeyError as exc:
        raise ValueError("transform must be 'van_de_sande' or 'wandell'") from exc


def rgb_to_opponent(rgb: np.ndarray, transform: str = "van_de_sande") -> np.ndarray:
    rgb = np.asarray(rgb, dtype=float)
    if rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError("rgb must have shape (height, width, 3)")
    if not np.all(np.isfinite(rgb)):
        raise ValueError("rgb must contain finite values")
    return np.einsum("...c,kc->...k", rgb, _opponent_matrix(transform))


def opponent_to_rgb(opponent: np.ndarray, transform: str = "van_de_sande") -> np.ndarray:
    opponent = np.asarray(opponent, dtype=float)
    if opponent.ndim != 3 or opponent.shape[-1] != 3:
        raise ValueError("opponent must have shape (height, width, 3)")
    inverse = np.linalg.inv(_opponent_matrix(transform))
    return np.einsum("...c,kc->...k", opponent, inverse)


def _second_difference(image: np.ndarray, axis: int) -> np.ndarray:
    out = np.zeros_like(image)
    if axis == 1:
        out[:, 1:-1] = -image[:, :-2] + 2.0 * image[:, 1:-1] - image[:, 2:]
    elif axis == 0:
        out[1:-1, :] = -image[:-2, :] + 2.0 * image[1:-1, :] - image[2:, :]
    else:
        raise ValueError("axis must be 0 or 1")
    return out


def _even_gabor_response(channel: np.ndarray) -> np.ndarray:
    return np.hypot(
        _second_difference(channel, axis=1),
        _second_difference(channel, axis=0),
    )


def _resize_to_base(response: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    if response.shape == shape:
        return response
    factors = (shape[0] / response.shape[0], shape[1] / response.shape[1])
    resized = zoom(response, factors, order=1, mode="nearest", prefilter=False)
    if resized.shape == shape:
        return resized
    out = np.empty(shape, dtype=float)
    height = min(shape[0], resized.shape[0])
    width = min(shape[1], resized.shape[1])
    out[:height, :width] = resized[:height, :width]
    if height < shape[0]:
        out[height:, :width] = resized[height - 1, :width]
    if width < shape[1]:
        out[:, width:] = out[:, width - 1 : width]
    return out


def _channel_weight(channel: np.ndarray, levels: int, blur_sigma_px: float) -> np.ndarray:
    base_shape = channel.shape
    current = channel
    responses: list[np.ndarray] = []
    for level in range(levels):
        responses.append(_resize_to_base(_even_gabor_response(current), base_shape))
        if level == levels - 1 or min(current.shape) < 8:
            break
        current = gaussian_filter(current, sigma=blur_sigma_px, mode="nearest")[::2, ::2]
    return np.max(np.stack(responses, axis=0), axis=0)


def _normalise_weight(weight: np.ndarray) -> np.ndarray:
    maximum = float(np.max(weight))
    if maximum <= np.finfo(float).eps:
        return np.zeros_like(weight)
    return weight / maximum


def run_edge_model(rgb: np.ndarray, config: EdgeModelConfig | None = None) -> EdgeModelResult:
    config = config or EdgeModelConfig()
    rgb = np.asarray(rgb, dtype=float)
    opponent = rgb_to_opponent(rgb, config.opponent_transform)
    raw_weights = np.stack(
        [
            _channel_weight(
                opponent[..., channel],
                config.pyramid_levels,
                config.pyramid_blur_sigma_px,
            )
            for channel in range(3)
        ],
        axis=-1,
    )
    channel_weights = raw_weights
    combined_weight = _normalise_weight(np.sum(channel_weights, axis=-1))
    modulation = config.alpha + config.beta * combined_weight

    triggers_x = np.empty_like(opponent)
    triggers_y = np.empty_like(opponent)
    source_terms = np.empty_like(opponent)
    prediction = np.empty_like(opponent)
    for channel in range(3):
        gx, gy = forward_gradient(opponent[..., channel])
        triggers_x[..., channel] = gx * modulation
        triggers_y[..., channel] = gy * modulation
        source = divergence(triggers_x[..., channel], triggers_y[..., channel])
        source_terms[..., channel] = source
        prediction[..., channel] = solve_poisson_dirichlet(
            source / config.diffusion_coefficient,
            boundary=opponent[..., channel],
        )

    predicted_rgb = np.clip(opponent_to_rgb(prediction, config.opponent_transform), 0.0, 1.0)
    return EdgeModelResult(
        input_rgb=rgb.copy(),
        predicted_rgb=predicted_rgb,
        opponent_input=opponent,
        opponent_prediction=prediction,
        combined_weight=combined_weight,
        channel_weights=channel_weights,
        triggers_x=triggers_x,
        triggers_y=triggers_y,
        source_terms=source_terms,
    )
