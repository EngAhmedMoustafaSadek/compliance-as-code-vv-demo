"""Synthetic test signals. Deterministic (seeded) so every run produces the same evidence."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Recording:
    signal: np.ndarray
    fs: float


def pulse_wave(bpm: float, fs: float = 100.0, seconds: float = 10.0, noise_std: float = 0.02, seed: int = 0) -> np.ndarray:
    """A pulsatile waveform: fundamental plus a second harmonic that mimics a dicrotic notch."""
    t = np.arange(int(round(seconds * fs))) / fs
    phase = 2 * np.pi * (bpm / 60.0) * t
    wave = np.sin(phase) + 0.35 * np.sin(2 * phase + 0.8)
    rng = np.random.default_rng(seed)
    return wave + rng.normal(0.0, noise_std, t.size)


def flat(fs: float = 100.0, seconds: float = 10.0, level: float = 0.5) -> np.ndarray:
    return np.full(int(round(seconds * fs)), level)


def clipped(bpm: float, fs: float = 100.0, seconds: float = 10.0) -> np.ndarray:
    """An over-amplified pulse wave saturating at the acquisition rails."""
    return np.clip(3.0 * pulse_wave(bpm, fs, seconds, noise_std=0.0), -1.0, 1.0)


def with_dropout(bpm: float, fs: float = 100.0, seconds: float = 10.0, start_s: float = 2.0, length_s: float = 0.2) -> np.ndarray:
    x = pulse_wave(bpm, fs, seconds)
    start = int(start_s * fs)
    x[start : start + int(length_s * fs)] = np.nan
    return x


def poor_quality(condition: str, fs: float = 100.0, seconds: float = 10.0) -> np.ndarray:
    makers = {
        "flat": lambda: flat(fs, seconds),
        "clipped": lambda: clipped(70, fs, seconds),
        "dropout": lambda: with_dropout(70, fs, seconds),
    }
    return makers[condition]()
