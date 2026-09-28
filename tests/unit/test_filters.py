"""Unit tests for the filter unit (written before the implementation, TDD style)."""

import numpy as np
import pytest

from pulsesig import moving_average

pytestmark = pytest.mark.req("REQ-001")


def test_output_has_same_length_as_input():
    x = np.arange(100, dtype=float)
    assert moving_average(x, 5).size == x.size


def test_reduces_white_noise_by_at_least_half():
    noise = np.random.default_rng(1).normal(0.0, 1.0, 10_000)
    assert moving_average(noise, 5).std() <= 0.5 * noise.std()


def test_constant_signal_is_unchanged_away_from_edges():
    x = np.full(50, 3.0)
    np.testing.assert_allclose(moving_average(x, 5)[2:-2], 3.0)


@pytest.mark.parametrize("window", [0, -1, 11])
def test_rejects_invalid_window(window):
    with pytest.raises(ValueError):
        moving_average(np.zeros(10), window)
