import tempfile
import unittest
from pathlib import Path
from pydub import AudioSegment
from pydub.generators import Sine
from audio_preparation import first_channel_pcm


class AudioPreparationTests(unittest.TestCase):
    def test_selects_first_channel_instead_of_mixing_and_cleans_up(self):
        left = Sine(440).to_audio_segment(duration=200).set_frame_rate(16000)
        right = Sine(880).to_audio_segment(duration=200).set_frame_rate(16000)
        stereo = AudioSegment.from_mono_audiosegments(left, right)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.wav'
            stereo.export(source, format='wav')
            original = source.read_bytes()
            with first_channel_pcm(source) as (pcm, info):
                self.assertEqual(Path(pcm).read_bytes(), left.set_sample_width(2).raw_data)
                self.assertEqual(info['channels'], 1)
                self.assertEqual(info['source_channels'], 2)
            self.assertFalse(Path(pcm).exists())
            self.assertEqual(source.read_bytes(), original)

    def test_mono_input_and_error_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.wav'
            AudioSegment.silent(duration=100).export(source, format='wav')
            with self.assertRaisesRegex(RuntimeError, 'upload failed'):
                with first_channel_pcm(source) as (pcm, info):
                    self.assertEqual(info['source_channels'], 1)
                    raise RuntimeError('upload failed')
            self.assertFalse(Path(pcm).exists())
