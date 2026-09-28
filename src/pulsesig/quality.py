"""Signal quality assessment. Software unit covered by REQ-004 to REQ-006."""

from dataclasses import dataclass

import numpy as np

FLATLINE_STD = 1e-3
CLIP_FRACTION = 0.05


@dataclass(frozen=True)
class QualityResult:
    adequate: bool
    reasons: tuple[str, ...] = ()


def assess_quality(
    signal,
    fs: float,
    flatline_std: float = FLATLINE_STD,
    clip_fraction: float = CLIP_FRACTION,
) -> QualityResult:
    """Decide whether a signal is fit to derive a clinical value from."""
    x = np.asarray(signal, dtype=float)
    reasons: list[str] = []

    if np.isnan(x).any():
        reasons.append("dropout")
    valid = x[~np.isnan(x)]
    if valid.size == 0:
        return QualityResult(False, ("dropout",))

    if valid.std() < flatline_std:
        reasons.append("flatline")
    else:
        lo, hi = valid.min(), valid.max()
        tol = 1e-6 * (hi - lo)
        at_rails = (np.abs(valid - hi) <= tol) | (np.abs(valid - lo) <= tol)
        if at_rails.mean() > clip_fraction:
            reasons.append("clipping")

    return QualityResult(not reasons, tuple(reasons))
