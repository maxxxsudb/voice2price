"""Reusable GigaAM transcription with pause-aware overlapping chunks."""
import os
import re
import subprocess
import tempfile
import threading
import wave
from pathlib import Path

import numpy as np

RATE = 16000
MAX_CHUNK_SEC = float(os.environ.get('GIGAAM_CHUNK_SEC', '22'))
OVERLAP_SEC = float(os.environ.get('GIGAAM_OVERLAP_SEC', '0.8'))
if MAX_CHUNK_SEC <= 0 or OVERLAP_SEC < 0 or MAX_CHUNK_SEC + OVERLAP_SEC >= 25:
    raise ValueError('GIGAAM_CHUNK_SEC + GIGAAM_OVERLAP_SEC must be positive and less than 25 seconds')
FRAME = RATE // 50

_model = None
_model_name = None
_lock = threading.Lock()


def model_name():
    return os.environ.get('GIGAAM_MODEL', 'v3_rnnt')


def load_model():
    global _model, _model_name
    name = model_name()
    if _model is None or _model_name != name:
        import torch
        import gigaam
        torch.set_num_threads(max(1, int(os.environ.get('GIGAAM_THREADS', os.cpu_count() or 1))))
        _model = gigaam.load_model(name, device='cpu', fp16_encoder=False,
                                   download_root=os.environ.get('GIGAAM_CACHE', '/models/gigaam'))
        _model_name = name
    return _model


def model_loaded():
    return _model is not None


def prepare(source):
    raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(source), '-af', 'pan=mono|c0=c0',
                          '-f', 's16le', '-acodec', 'pcm_s16le', '-ar', str(RATE), '-'],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    peak = float(np.abs(audio).max()) if audio.size else 0.0
    return audio * (0.9 / peak) if peak > 1e-4 else audio


def split_points(audio, max_sec=MAX_CHUNK_SEC):
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
            idx = int(np.flatnonzero(window <= quiet * 1.5 + 1e-6)[-1])
            cut = (lo + idx) * FRAME + FRAME // 2
        else:
            cut = start + limit
        cuts.append(cut)
        start = cut
    return cuts


def _write_wav(path, samples):
    data = (np.clip(samples, -1, 1) * 32767).astype('<i2').tobytes()
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(data)


def append_without_overlap(current, addition, max_words=12):
    if not current:
        return addition.strip(), addition.strip()
    old_words, new_words = current.split(), addition.split()
    old_norm = [re.sub(r'\W+', '', word.lower(), flags=re.UNICODE) for word in old_words]
    new_norm = [re.sub(r'\W+', '', word.lower(), flags=re.UNICODE) for word in new_words]
    repeated = 0
    for size in range(min(max_words, len(old_words), len(new_words)), 0, -1):
        if old_norm[-size:] == new_norm[:size]:
            repeated = size
            break
    unique = ' '.join(new_words[repeated:]).strip()
    return ' '.join(filter(None, [current.strip(), unique])), unique


def transcribe(source):
    audio = prepare(source)
    bounds = [0] + split_points(audio) + [len(audio)]
    segments, full_text = [], ''
    overlap = int(OVERLAP_SEC * RATE)
    with tempfile.TemporaryDirectory(prefix='gigaam-') as folder, _lock:
        model = load_model()
        for index, (start, end) in enumerate(zip(bounds, bounds[1:])):
            if end - start < RATE * 0.3:
                continue
            audio_start = start if index == 0 else max(0, start - overlap)
            path = Path(folder) / f'{index:03}.wav'
            _write_wav(path, audio[audio_start:end])
            result = model.transcribe(str(path))
            text = (getattr(result, 'text', result) or '').strip()
            if text:
                full_text, unique = append_without_overlap(full_text, text)
                if unique:
                    segments.append({'startTime': f'{start / RATE:.2f}s',
                                     'endTime': f'{end / RATE:.2f}s',
                                     'text': unique, 'words': []})
    return full_text, segments
