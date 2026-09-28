"""Unit tests for beat detection and minimum data length (TDD style)."""

import numpy as np
import pytest

from pulsesig import InsufficientDataError, detect_peaks, estimate_pulse_rate
from support.signals import pulse_wave


@pytest.mark.req("REQ-002")
def test_one_peak_per_beat_when_peaks_are_too_close():
    x = np.array([0, 1.0, 0, 0.9, 0, 0, 0, 0, 2.0, 0, 0])
    assert detect_peaks(x, min_distance=3, threshold=0.5).tolist() == [1, 8]


@pytest.mark.req("REQ-002")
def test_secondary_bump_below_threshold_is_not_a_beat():
    x = np.array([0, 1.0, 0.6, 0.8, 0.1, 0, 2.0, 0, 0])
    assert detect_peaks(x, min_distance=1, threshold=0.9).tolist() == [1, 6]


@pytest.mark.req("REQ-002")
def test_beats_cut_off_by_recording_edges_are_ignored():
    x = np.array([2.0, 1.0, 0, 0, 1.5, 0, 0, 1.0, 2.0])
    assert detect_peaks(x, min_distance=1, threshold=0.5).tolist() == [4]


@pytest.mark.req("REQ-002")
@pytest.mark.parametrize("bpm", [40, 180])
def test_rate_is_accurate_at_range_limits_with_heavier_noise(bpm):
    for seed in range(5):
        rate = estimate_pulse_rate(pulse_wave(bpm, noise_std=0.05, seed=seed), 100.0)
        assert abs(rate - bpm) <= 2


@pytest.mark.req("REQ-003")
def test_exactly_four_seconds_is_accepted():
    assert estimate_pulse_rate(pulse_wave(70, seconds=4.0), 100.0) == pytest.approx(70, abs=2)


@pytest.mark.req("REQ-003")
def test_just_under_four_seconds_is_rejected():
    with pytest.raises(InsufficientDataError):
        estimate_pulse_rate(pulse_wave(70, seconds=3.99), 100.0)
