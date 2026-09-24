"""Prepare channel 1 only for voice orders; never modify the source file."""
from contextlib import contextmanager
from pathlib import Path
import tempfile

from pydub import AudioSegment


@contextmanager
def first_channel_pcm(source):
    audio = AudioSegment.from_file(source)
    mono = audio.split_to_mono()[0].set_frame_rate(16000).set_sample_width(2)
    with tempfile.TemporaryDirectory(prefix='speech-mono-') as directory:
        path = Path(directory) / 'channel-1.pcm'
        path.write_bytes(mono.raw_data)
        yield str(path), {
            'encoding': 'LINEAR16_PCM', 'sample_rate': 16000, 'channels': 1,
            'source_channels': audio.channels, 'selected_channel': 1,
        }
