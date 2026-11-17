import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf


# Every output gets the same sample count so mixes and stems stay on one timeline even when a source is shorter.
def apply(segments, sources, out_dir, fade_s):
    if not segments or not sources:
        raise ValueError("segments and sources must not be empty")
    sr = sf.info(next(iter(sources.values()))["path"]).samplerate
    fade = int(round(fade_s * sr))
    lengths = [int(round((e - s) * sr)) for s, e in segments]
    if fade_s < 0 or any(n <= fade for n in lengths):
        raise ValueError("each segment must be longer than the nonnegative fade")
    total = sum(lengths) - fade * (len(segments) - 1)
    for name, src in sources.items():
        x, file_sr = sf.read(src["path"], always_2d=True)
        assert file_sr == sr, f"{name}: {file_sr} != {sr}"
        parts = []
        for (s, _), n in zip(segments, lengths):
            a = int(round((s + src.get("offset", 0.0)) * sr))
            seg = np.zeros((n, x.shape[1]))
            lo, hi = max(0, a), min(len(x), a + n)
            if hi > lo:
                seg[lo - a:hi - a] = x[lo:hi]
            parts.append(seg)
        y = parts[0]
        ramp = np.linspace(0, 1, fade)[:, None]
        for p in parts[1:]:
            y = np.concatenate([y[:-fade], y[-fade:] * (1 - ramp) + p[:fade] * ramp, p[fade:]]) if fade else np.concatenate([y, p])
        assert len(y) == total
        out = Path(out_dir) / f"{name}.wav"
        out.parent.mkdir(parents=True, exist_ok=True)
        sf.write(out, y, sr, subtype="PCM_16")
    return sr, total


if __name__ == "__main__":
    spec = json.loads(Path(sys.argv[1]).read_text())
    sr, total = apply(spec["segments"], spec["sources"], spec["out_dir"], spec.get("fade_s", 0.04))
    print(f"{len(spec['sources'])} files, {total} samples @ {sr} Hz ({total / sr:.3f}s)")
