import unittest
import wave
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import transcriber

RATE = transcriber.RATE


def speech_with_pauses(seconds, tone_sec=4.5, pause_sec=0.5):
    timeline = np.arange(int(tone_sec * RATE)) / RATE
    tone = 0.5 * np.sin(2 * np.pi * 300 * timeline)
    block = np.concatenate([tone, np.zeros(int(pause_sec * RATE))])
    repeats = int(np.ceil(seconds / (tone_sec + pause_sec)))
    return np.tile(block, repeats)[:int(seconds * RATE)].astype(np.float32)


class TranscriberTest(unittest.TestCase):
    def test_long_audio_is_cut_in_pauses_under_limit(self):
        audio = speech_with_pauses(70)
        cuts = transcriber.split_points(audio)
        bounds = [0] + cuts + [len(audio)]
        self.assertTrue(all(b - a <= transcriber.MAX_CHUNK_SEC * RATE
                            for a, b in zip(bounds, bounds[1:])))

    def test_overlap_is_deduplicated(self):
        answers = iter(['бочок индейки два', 'два сервелат венский полтора'])
        fake = SimpleNamespace(transcribe=lambda path: SimpleNamespace(text=next(answers)))
        with patch('transcriber.prepare', return_value=speech_with_pauses(30)), \
             patch('transcriber.load_model', return_value=fake):
            text, segments = transcriber.transcribe('order.mp3')
        self.assertEqual(text, 'бочок индейки два сервелат венский полтора')
        self.assertEqual(segments[1]['text'], 'сервелат венский полтора')

    def test_later_chunks_include_audio_overlap(self):
        durations = []
        fake = SimpleNamespace(transcribe=lambda path: (
            durations.append(wave.open(path).getnframes() / RATE) or SimpleNamespace(text='слово')))
        with patch('transcriber.prepare', return_value=speech_with_pauses(30)), \
             patch('transcriber.load_model', return_value=fake):
            transcriber.transcribe('order.mp3')
        self.assertGreater(durations[1], 30 - 20)


if __name__ == '__main__':
    unittest.main()
