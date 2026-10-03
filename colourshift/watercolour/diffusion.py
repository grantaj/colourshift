"""Poisson reconstruction used by the edge-triggered filling-in model."""

from __future__ import annotations

import numpy as np
from scipy.fft import dstn, idstn


def solve_poisson_dirichlet(rhs: np.ndarray, boundary: np.ndarray | None = None) -> np.ndarray:
    """Solve ``laplacian(u) = rhs`` with fixed image-boundary values.

    The discrete five-point Laplacian is inverted with a type-I discrete sine
    transform. This matches the reconstruction viewpoint of the WCE model:
    modified edge derivatives are integrated back into a surface image.
    """
    rhs = np.asarray(rhs, dtype=float)
    if rhs.ndim != 2 or min(rhs.shape) < 3:
        raise ValueError("rhs must be a 2-D array at least 3x3")
    if not np.all(np.isfinite(rhs)):
        raise ValueError("rhs must contain only finite values")

    if boundary is None:
        boundary_arr = np.zeros_like(rhs)
    else:
        boundary_arr = np.asarray(boundary, dtype=float)
        if boundary_arr.shape != rhs.shape:
            raise ValueError("boundary must have the same shape as rhs")
        if not np.all(np.isfinite(boundary_arr)):
            raise ValueError("boundary must contain only finite values")

    f = rhs[1:-1, 1:-1].copy()
    f[0, :] -= boundary_arr[0, 1:-1]
    f[-1, :] -= boundary_arr[-1, 1:-1]
    f[:, 0] -= boundary_arr[1:-1, 0]
    f[:, -1] -= boundary_arr[1:-1, -1]

    ny, nx = f.shape
    ky = np.arange(1, ny + 1, dtype=float)[:, None]
    kx = np.arange(1, nx + 1, dtype=float)[None, :]
    eigenvalues = 2.0 * np.cos(np.pi * ky / (ny + 1)) + 2.0 * np.cos(np.pi * kx / (nx + 1)) - 4.0

    f_hat = dstn(f, type=1, norm="ortho")
    interior = idstn(f_hat / eigenvalues, type=1, norm="ortho")

    result = boundary_arr.copy()
    result[1:-1, 1:-1] = interior
    return result


def forward_gradient(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Discrete gradient equivalent to the paper's [-1, 1] filters."""
    image = np.asarray(image, dtype=float)
    gx = np.zeros_like(image)
    gy = np.zeros_like(image)
    gx[:, :-1] = image[:, 1:] - image[:, :-1]
    gy[:-1, :] = image[1:, :] - image[:-1, :]
    return gx, gy


def divergence(gx: np.ndarray, gy: np.ndarray) -> np.ndarray:
    """Discrete divergence paired with :func:`forward_gradient`."""
    gx = np.asarray(gx, dtype=float)
    gy = np.asarray(gy, dtype=float)
    if gx.shape != gy.shape or gx.ndim != 2:
        raise ValueError("gx and gy must be same-shaped 2-D arrays")

    div = np.zeros_like(gx)
    div[:, 0] += gx[:, 0]
    div[:, 1:-1] += gx[:, 1:-1] - gx[:, :-2]
    div[:, -1] -= gx[:, -2]
    div[0, :] += gy[0, :]
    div[1:-1, :] += gy[1:-1, :] - gy[:-2, :]
    div[-1, :] -= gy[-2, :]
    return div
