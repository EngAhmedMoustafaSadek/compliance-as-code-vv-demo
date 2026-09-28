"""pulsesig: a small, synthetic pulse-rate module used to demonstrate compliance-as-code V&V.

Not a medical device. Not for clinical use.
"""

from .alarms import Alarm, AlarmLimits, MonitorOutput, evaluate
from .filters import moving_average
from .quality import QualityResult, assess_quality
from .rate import InsufficientDataError, detect_peaks, estimate_pulse_rate

__version__ = "0.1.0"

__all__ = [
    "Alarm",
    "AlarmLimits",
    "InsufficientDataError",
    "MonitorOutput",
    "QualityResult",
    "assess_quality",
    "detect_peaks",
    "estimate_pulse_rate",
    "evaluate",
    "moving_average",
]
