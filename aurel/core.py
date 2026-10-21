from dataclasses import dataclass
from typing import Protocol
import numpy as np


@dataclass(frozen=True)
class Case:
    id: str
    group: str
    task: str
    prompt: str
    audio: np.ndarray
    sample_rate: int
    label: str


class Model(Protocol):
    def predict(self, audio: np.ndarray, sample_rate: int, prompt: str) -> str: ...


def validate_audio(audio):
    x = np.asarray(audio, dtype=np.float32)
    if x.ndim != 1 or x.size == 0 or not np.isfinite(x).all():
        raise ValueError('Expected nonempty finite mono audio')
    if np.max(np.abs(x)) > 1:
        raise ValueError('Audio must be in [-1, 1]')
    return x


def transform(audio, kind, rng):
    x = validate_audio(audio)
    if kind == 'identity':
        return x.copy()
    if kind == 'gain':
        return x * 0.35
    if kind == 'noise':
        # 25 dB target SNR before clipping; seed recorded by the runner.
        noise = rng.normal(size=x.shape)
        noise *= np.sqrt(np.mean(x*x)) / (10**(25/20) * np.sqrt(np.mean(noise*noise)))
        return np.clip(x + noise, -1, 1).astype(np.float32)
    if kind == 'reverse':
        # Valid only for the explicitly synthetic order task, never generic speech.
        return x[::-1].copy()
    raise ValueError(f'Unknown transformation: {kind}')


def expected_label(case, kind):
    if kind == 'reverse' and case.task == 'order':
        return {'rising': 'falling', 'falling': 'rising'}[case.label]
    if kind not in ('identity', 'gain', 'noise', 'reverse'):
        raise ValueError(kind)
    return case.label


def synthetic_cases(n=40, seed=0):
    if n < 2:
        raise ValueError('Need at least two source groups')
    rng = np.random.default_rng(seed)
    sr = 16000
    t = np.arange(sr // 4) / sr
    for i in range(n):
        low = rng.uniform(350, 500)
        high = rng.uniform(850, 1000)
        tones = [np.sin(2*np.pi*f*t) for f in (low, high)]
        rising = bool(rng.integers(2))
        audio = (0.5*np.concatenate(tones if rising else tones[::-1])).astype(np.float32)
        for task, label, prompt in [
            ('order', 'rising' if rising else 'falling', 'Is pitch order rising or falling?'),
            ('count', 'two', 'How many tone segments: one or two?'),
        ]:
            yield Case(f'{i}-{task}', str(i), task, prompt, audio, sr, label)


class ToyModel:
    """Handcrafted signal classifier, deliberately amplitude sensitive."""
    def __init__(self, normalize=False):
        self.normalize = normalize

    def predict(self, audio, sample_rate, prompt):
        x = validate_audio(audio)
        if self.normalize:
            peak = np.max(np.abs(x))
            x = x / max(float(peak), 1e-9) * 0.5
        if np.sqrt(np.mean(x*x)) < 0.2:
            return 'unknown'
        if 'How many' in prompt:
            return 'two'
        a, b = np.array_split(x, 2)
        fa = np.argmax(np.abs(np.fft.rfft(a))) * sample_rate / len(a)
        fb = np.argmax(np.abs(np.fft.rfft(b))) * sample_rate / len(b)
        return 'rising' if fa < fb else 'falling'
