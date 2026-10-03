import numpy as np
import pytest

from colourshift.watercolour.diffusion import (
    divergence,
    forward_gradient,
    solve_poisson_dirichlet,
)


def test_poisson_recovers_known_surface_from_its_discrete_laplacian():
    yy, xx = np.mgrid[:33, :35]
    surface = 0.2 + 0.01 * xx + 0.015 * yy + 0.1 * np.sin(np.pi * xx / 34) * np.sin(np.pi * yy / 32)
    gx, gy = forward_gradient(surface)
    rhs = divergence(gx, gy)
    recovered = solve_poisson_dirichlet(rhs, boundary=surface)
    assert recovered == pytest.approx(surface, abs=2e-12)


def test_zero_source_zero_boundary_gives_zero():
    result = solve_poisson_dirichlet(np.zeros((20, 24)))
    assert np.allclose(result, 0.0)
