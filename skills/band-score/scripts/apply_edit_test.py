import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from apply_edit import apply


class EditTest(unittest.TestCase):
    def test_aligned_sources_with_fade_and_padding(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            signal = np.arange(12, dtype=float)[:, None] / 16
            sf.write(root / 'mix.wav', signal, 100, subtype='FLOAT')
            sf.write(root / 'stem.wav', signal[:10], 100, subtype='FLOAT')
            sources = {'mix': {'path': root / 'mix.wav'}, 'stem': {'path': root / 'stem.wav', 'offset': -0.02}}
            for fade, length in [(0, 12), (0.02, 10)]:
                with self.subTest(fade=fade):
                    out = root / str(fade)
                    self.assertEqual(apply([(0, 0.06), (0.08, 0.14)], sources, out, fade), (100, length))
                    mix, _ = sf.read(out / 'mix.wav')
                    stem, _ = sf.read(out / 'stem.wav')
                    expected_mix = [0, 1, 2, 3, 4, 9, 10, 11, 0, 0] if fade else [0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 0, 0]
                    expected_stem = [0, 0, 0, 1, 2, 7, 8, 9, 0, 0] if fade else [0, 0, 0, 1, 2, 3, 6, 7, 8, 9, 0, 0]
                    np.testing.assert_allclose(mix, np.array(expected_mix) / 16, atol=1 / 32768)
                    np.testing.assert_allclose(stem, np.array(expected_stem) / 16, atol=1 / 32768)


if __name__ == '__main__':
    unittest.main()
