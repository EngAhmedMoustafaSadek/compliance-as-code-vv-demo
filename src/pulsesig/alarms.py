"""Monitor output and alarm logic. Software unit covered by REQ-007 and REQ-008."""

from dataclasses import dataclass
from enum import Enum

from .quality import assess_quality
from .rate import InsufficientDataError, estimate_pulse_rate


class Alarm(str, Enum):
    NONE = "NONE"
    LOW_RATE = "LOW_RATE"
    HIGH_RATE = "HIGH_RATE"
    SIGNAL_QUALITY = "SIGNAL_QUALITY"


@dataclass(frozen=True)
class AlarmLimits:
    low_bpm: float = 40.0
    high_bpm: float = 150.0


@dataclass(frozen=True)
class MonitorOutput:
    pulse_rate_bpm: float | None
    alarm: Alarm
    reasons: tuple[str, ...] = ()


def evaluate(signal, fs: float, limits: AlarmLimits = AlarmLimits()) -> MonitorOutput:
    """Turn a raw signal into what the clinician would see.

    Risk control RC-02: a rate is never output from an inadequate signal.
    """
    quality = assess_quality(signal, fs)
    if not quality.adequate:
        return MonitorOutput(None, Alarm.SIGNAL_QUALITY, quality.reasons)

    try:
        rate = estimate_pulse_rate(signal, fs)
    except InsufficientDataError:
        return MonitorOutput(None, Alarm.SIGNAL_QUALITY, ("insufficient data",))

    if rate < limits.low_bpm:
        return MonitorOutput(rate, Alarm.LOW_RATE)
    if rate > limits.high_bpm:
        return MonitorOutput(rate, Alarm.HIGH_RATE)
    return MonitorOutput(rate, Alarm.NONE)
