"""Pulse rate estimation. Software unit covered by REQ-002 and REQ-003."""

import numpy as np

from .filters import moving_average

MIN_DURATION_S = 4.0
MAX_RATE_BPM = 200.0
SMOOTHING_WINDOW = 5
PEAK_THRESHOLD_RATIO = 0.6  # of the 99th percentile; rejects dicrotic (secondary) peaks


class InsufficientDataError(ValueError):
    """Raised when there is not enough signal to estimate a rate safely."""


def detect_peaks(x: np.ndarray, min_distance: int, threshold: float, exit_ratio: float = 0.5) -> np.ndarray:
    """Return one peak index per beat, at least min_distance apart.

    A beat starts when the signal rises above threshold and ends only when it falls
    below exit_ratio * threshold (hysteresis). This stops noise near the crossing
    from splitting one beat in two, and secondary (dicrotic) peaks that never reach
    the threshold are ignored. Beats cut off by the start or end of the recording
    are dropped because their true peak position is unknown. If two peaks are still
    closer than min_distance, the taller one wins.
    """
    x = np.asarray(x, dtype=float)
    if x.size < 3:
        return np.array([], dtype=int)
    exit_level = exit_ratio * threshold

    regions: list[tuple[int, int]] = []
    start = None
    for i, value in enumerate(x):
        if start is None and value > threshold:
            start = i
        elif start is not None and value < exit_level:
            regions.append((start, i))
            start = None
    if start is not None:
        regions.append((start, x.size))

    candidates = [int(s + np.argmax(x[s:e])) for s, e in regions if s > 0 and e < x.size]
    kept: list[int] = []
    for idx in sorted(candidates, key=lambda i: x[i], reverse=True):
        if all(abs(idx - k) >= min_distance for k in kept):
            kept.append(idx)
    return np.array(sorted(kept), dtype=int)


def estimate_pulse_rate(signal, fs: float) -> float:
    """Estimate pulse rate in beats per minute from a pulsatile signal."""
    if fs <= 0:
        raise ValueError("sampling rate must be positive")
    x = np.asarray(signal, dtype=float)
    if x.size < MIN_DURATION_S * fs:
        raise InsufficientDataError(
            f"need at least {MIN_DURATION_S:.0f} s of signal, got {x.size / fs:.2f} s"
        )
    if np.isnan(x).any():
        raise ValueError("signal contains missing samples")

    smoothed = moving_average(x - x.mean(), SMOOTHING_WINDOW)
    threshold = PEAK_THRESHOLD_RATIO * np.percentile(smoothed, 99)
    min_distance = int(fs * 60.0 / MAX_RATE_BPM)
    peaks = detect_peaks(smoothed, min_distance, threshold)
    if peaks.size < 2:
        raise InsufficientDataError("fewer than two beats detected")

    mean_interval_s = (peaks[-1] - peaks[0]) / (peaks.size - 1) / fs
    return 60.0 / mean_interval_s
