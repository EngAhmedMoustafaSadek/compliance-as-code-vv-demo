"""Shared BDD step definitions for all feature files."""

from dataclasses import dataclass

import pytest
from pytest_bdd import given, parsers, then, when

from pulsesig import (
    Alarm,
    AlarmLimits,
    InsufficientDataError,
    assess_quality,
    estimate_pulse_rate,
    evaluate,
)
from support.signals import Recording, clipped, flat, poor_quality, pulse_wave, with_dropout

FS = 100.0


@dataclass
class Estimate:
    value: float | None = None
    error: Exception | None = None


@pytest.fixture
def limits():
    return AlarmLimits()


# ---- Given ---------------------------------------------------------------

@given(
    parsers.parse("a clean pulsatile signal at {bpm:d} bpm sampled at {fs:d} Hz for {seconds:d} seconds"),
    target_fixture="recording",
)
def clean_signal(bpm, fs, seconds):
    return Recording(pulse_wave(bpm, fs, seconds), fs)


@given(parsers.parse("a flat signal sampled at {fs:d} Hz for {seconds:d} seconds"), target_fixture="recording")
def flat_signal(fs, seconds):
    return Recording(flat(fs, seconds), fs)


@given(
    parsers.parse("a clipped pulsatile signal at {bpm:d} bpm sampled at {fs:d} Hz for {seconds:d} seconds"),
    target_fixture="recording",
)
def clipped_signal(bpm, fs, seconds):
    return Recording(clipped(bpm, fs, seconds), fs)


@given(parsers.parse("a pulsatile signal at {bpm:d} bpm with missing samples"), target_fixture="recording")
def dropout_signal(bpm):
    return Recording(with_dropout(bpm, FS), FS)


@given(parsers.parse("a {condition} poor-quality signal"), target_fixture="recording")
def poor_signal(condition):
    return Recording(poor_quality(condition, FS), FS)


@given(parsers.parse("alarm limits of {low:d} to {high:d} bpm"), target_fixture="limits")
def custom_limits(low, high):
    return AlarmLimits(low_bpm=low, high_bpm=high)


# ---- When ----------------------------------------------------------------

@when("the pulse rate is estimated", target_fixture="estimate")
def estimate_rate(recording):
    try:
        return Estimate(value=estimate_pulse_rate(recording.signal, recording.fs))
    except InsufficientDataError as error:
        return Estimate(error=error)


@when("signal quality is assessed", target_fixture="quality")
def assess(recording):
    return assess_quality(recording.signal, recording.fs)


@when("the monitor evaluates the signal", target_fixture="output")
def monitor(recording, limits):
    return evaluate(recording.signal, recording.fs, limits)


# ---- Then ----------------------------------------------------------------

@then(parsers.parse("the estimate is within {tolerance:d} bpm of {bpm:d}"))
def rate_within(estimate, tolerance, bpm):
    assert estimate.error is None, f"unexpected error: {estimate.error}"
    assert abs(estimate.value - bpm) <= tolerance, f"estimated {estimate.value:.2f} bpm for {bpm} bpm"


@then("the estimate is rejected as insufficient data")
def rejected(estimate):
    assert estimate.value is None
    assert isinstance(estimate.error, InsufficientDataError)


@then(parsers.parse('signal quality is inadequate because of "{reason}"'))
def inadequate(quality, reason):
    assert not quality.adequate
    assert reason in quality.reasons, f"reasons were {quality.reasons}"


@then("signal quality is adequate")
def adequate(quality):
    assert quality.adequate, f"flagged as {quality.reasons}"


@then("no pulse rate is output")
def no_rate(output):
    assert output.pulse_rate_bpm is None


@then("a pulse rate is output")
def has_rate(output):
    assert output.pulse_rate_bpm is not None


@then(parsers.parse('the "{alarm}" alarm is raised'))
def alarm_raised(output, alarm):
    assert output.alarm == Alarm(alarm), f"got {output.alarm.value}"
