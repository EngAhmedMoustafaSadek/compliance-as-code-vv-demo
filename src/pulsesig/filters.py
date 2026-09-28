"""Signal conditioning. Software unit covered by REQ-001."""

import numpy as np


def moving_average(signal, window: int) -> np.ndarray:
    """Smooth a signal with a centred moving average.

    The output has the same length as the input so sample indices stay aligned
    with the original recording.
    """
    x = np.asarray(signal, dtype=float)
    if window < 1:
        raise ValueError("window must be at least 1 sample")
    if window > x.size:
        raise ValueError("window must not be longer than the signal")
    kernel = np.ones(window) / window
    return np.convolve(x, kernel, mode="same")
