"""Local STT wrapper: chunking and result shape; the GigaAM model itself is mocked."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import local_stt

RATE = local_stt.RATE


def speech_with_pauses(seconds, tone_sec=4.5, pause_sec=0.5):
    t = np.arange(int(tone_sec * RATE)) / RATE
    tone = 0.5 * np.sin(2 * np.pi * 300 * t)
    block = np.concatenate([tone, np.zeros(int(pause_sec * RATE))])
    reps = int(np.ceil(seconds / (tone_sec + pause_sec)))
    return np.tile(block, reps)[:int(seconds * RATE)].astype(np.float32)


class LocalSttTest(unittest.TestCase):
    def test_short_audio_is_one_piece(self):
        self.assertEqual(local_stt.split_points(speech_with_pauses(12)), [])

    def test_long_audio_is_cut_in_pauses_under_limit(self):
        audio = speech_with_pauses(70)
        cuts = local_stt.split_points(audio)
        bounds = [0] + cuts + [len(audio)]
        self.assertTrue(all(b - a <= local_stt.MAX_CHUNK_SEC * RATE for a, b in zip(bounds, bounds[1:])))
        self.assertTrue(all((c / RATE) % 5 >= 4.5 for c in cuts), [c / RATE for c in cuts])

    def test_no_pauses_still_cut(self):
        t = np.arange(50 * RATE) / RATE
        audio = (0.5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
        self.assertEqual(local_stt.split_points(audio), [22 * RATE, 44 * RATE])

    def test_transcribe_returns_text_and_segments(self):
        fake = SimpleNamespace(transcribe=lambda path: SimpleNamespace(text='бочок индейки два'))
        with patch('local_stt.prepare', return_value=speech_with_pauses(30)), \
             patch('local_stt._load', return_value=fake):
            text, segments = local_stt.transcribe('order.mp3')
        self.assertEqual(len(segments), 2)
        self.assertEqual(text, 'бочок индейки два бочок индейки два')
        self.assertEqual(segments[0]['startTime'], '0.00s')

    def test_prepare_reads_first_channel_and_normalizes(self):
        import subprocess, tempfile, os
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'quiet.mp3')
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=300:duration=2',
                            '-af', 'volume=0.02', '-ac', '2', '-ar', '48000', path], check=True)
            audio = local_stt.prepare(path)
        self.assertAlmostEqual(len(audio) / RATE, 2.0, delta=0.1)
        self.assertGreater(float(np.abs(audio).max()), 0.8)


if __name__ == '__main__':
    unittest.main()
