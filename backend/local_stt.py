"""Local speech recognition with GigaAM-v3 (Sber, MIT): audio never leaves the machine.

Model weights are downloaded once to GIGAAM_CACHE (a docker volume) and kept in
memory. GigaAM's plain `transcribe` accepts up to 25 s, so longer voice messages
are cut at pauses into pieces of at most MAX_CHUNK_SEC; each piece becomes one
segment, like SpeechKit chunks.

Settings (environment):
  GIGAAM_MODEL  v3_rnnt (default: words, no punctuation — what the order parser expects),
                v3_ctc, v3_e2e_rnnt, v3_e2e_ctc
  GIGAAM_CACHE  weights folder, default /models/gigaam
"""
import os
import subprocess
import tempfile
import threading
import wave
from pathlib import Path

import numpy as np

RATE = 16000
MAX_CHUNK_SEC = 22.0
FRAME = RATE // 50  # 20 ms

_model = None
_model_name = None
_lock = threading.Lock()


def model_name():
    return os.environ.get('GIGAAM_MODEL', 'v3_rnnt')


def _load():
    global _model, _model_name
    name = model_name()
    if _model is None or _model_name != name:
        try:
            import torch
            import gigaam
        except ImportError as exc:
            raise RuntimeError('Локальное распознавание не установлено в образ backend '
                               '(нужна сборка с LOCAL_STT=1)') from exc
        torch.set_num_threads(max(1, os.cpu_count() or 1))
        _model = gigaam.load_model(name, device='cpu', fp16_encoder=False,
                                   download_root=os.environ.get('GIGAAM_CACHE', '/models/gigaam'))
        _model_name = name
    return _model


def prepare(source):
    """First channel (channels in these files are identical), 16 kHz mono float,
    peak-normalized (some recordings are very quiet)."""
    raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(source), '-af', 'pan=mono|c0=c0',
                          '-f', 's16le', '-acodec', 'pcm_s16le', '-ar', str(RATE), '-'],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    peak = float(np.abs(audio).max()) if audio.size else 0.0
    return audio * (0.9 / peak) if peak > 1e-4 else audio


def split_points(audio, max_sec=MAX_CHUNK_SEC):
    """Sample positions to cut at so every piece is <= max_sec, preferring the
    quietest 20 ms frame in the last part of each window (a pause)."""
    limit = int(max_sec * RATE)
    if len(audio) <= limit:
        return []
    frames = len(audio) // FRAME
    energy = np.sqrt((audio[:frames * FRAME].reshape(frames, FRAME) ** 2).mean(axis=1))
    cuts, start = [], 0
    while len(audio) - start > limit:
        lo, hi = (start + 2 * RATE) // FRAME, (start + limit) // FRAME
        window = energy[lo:hi]
        quiet = window.min() if window.size else 1.0
        if window.size and quiet < 0.2 * float(np.median(window) or 1):
            idx = int(np.flatnonzero(window <= quiet * 1.5 + 1e-6)[-1])  # latest quiet frame
            cut = (lo + idx) * FRAME + FRAME // 2
        else:
            cut = start + limit
        cuts.append(cut)
        start = cut
    return cuts


def _write_wav(path, samples):
    data = (np.clip(samples, -1, 1) * 32767).astype('<i2').tobytes()
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)


def transcribe(source):
    """Return (text, segments) in the same shape as the SpeechKit path."""
    audio = prepare(source)
    bounds = [0] + split_points(audio) + [len(audio)]
    segments = []
    with tempfile.TemporaryDirectory(prefix='gigaam-') as folder, _lock:
        model = _load()
        for n, (start, end) in enumerate(zip(bounds, bounds[1:])):
            if end - start < RATE * 0.3:
                continue
            path = Path(folder) / f'{n:03}.wav'
            _write_wav(path, audio[start:end])
            result = model.transcribe(str(path))
            text = (getattr(result, 'text', result) or '').strip()
            if text:
                segments.append({'startTime': f'{start / RATE:.2f}s', 'endTime': f'{end / RATE:.2f}s',
                                 'text': text, 'words': []})
    return ' '.join(s['text'] for s in segments).strip(), segments
