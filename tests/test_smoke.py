"""Local tests: synthetic media only; no downloads or paid API calls."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RENDER = REPO / "skills" / "video-editor" / "scripts" / "render.py"
TRANSCRIBE = REPO / "skills" / "video-editor" / "scripts" / "transcribe_elevenlabs.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PureUnitTests(unittest.TestCase):
    def test_srt_generation(self):
        module = load("transcribe_elevenlabs", TRANSCRIBE)
        data = {"words": [
            {"text": "Hello", "start": 0, "end": 0.2, "type": "word"},
            {"text": " world", "start": 0.2, "end": 0.5, "type": "word"},
            {"text": "!", "start": 0.5, "end": 0.6, "type": "punctuation"},
        ]}
        srt = module.transcript_to_srt(data)
        self.assertIn("Hello world!", srt)
        self.assertIn("00:00:00,000 --> 00:00:00,600", srt)

    def test_path_traversal_rejected(self):
        module = load("local_renderer", RENDER)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with self.assertRaises(module.EditError):
                module.safe_path(root, "../outside.mp4")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg and ffprobe are needed for integration tests")
class RenderingTests(unittest.TestCase):
    def test_synthetic_two_clip_edit_with_music_and_captions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "input").mkdir()
            (root / "output").mkdir()
            for color, name, include_audio in [
                ("red", "a.mp4", True), ("blue", "b.mp4", False)
            ]:
                command = [
                    "ffmpeg", "-v", "error", "-y",
                    "-f", "lavfi", "-i", f"color=c={color}:s=320x180:r=30:d=2",
                ]
                if include_audio:
                    command += ["-f", "lavfi", "-i", "sine=frequency=440:duration=2"]
                command += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
                if include_audio:
                    command += ["-c:a", "aac"]
                command += [str(root / "input" / name)]
                subprocess.run(command, check=True)
            subprocess.run([
                "ffmpeg", "-v", "error", "-y",
                "-f", "lavfi", "-i", "sine=frequency=220:duration=1",
                "-c:a", "libmp3lame", str(root / "input" / "music.mp3")
            ], check=True)
            (root / "input" / "captions.srt").write_text(
                "1\n00:00:00,300 --> 00:00:01,900\nHello from a test\n", encoding="utf-8"
            )
            plan = {
                "clips": [{"file": "input/a.mp4", "start": 0, "end": 2},
                          {"file": "input/b.mp4", "start": 0, "end": 2}],
                "format": "shorts", "resolution": [360, 640],
                "transition": {"type": "fade", "duration": 0.4},
                "fade": {"in": 0.2, "out": 0.3},
                "music": {"file": "input/music.mp3", "volume": 0.15},
                "title": {"text": "Demo", "start": 0, "end": 1},
                "subtitles": {"file": "input/captions.srt"},
                "output": "output/edited.mp4"
            }
            planfile = root / "edit-plan.json"
            planfile.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            subprocess.run([sys.executable, str(RENDER), str(planfile), "--dry-run"], check=True)
            subprocess.run([sys.executable, str(RENDER), str(planfile)], check=True)
            output = root / "output" / "edited.mp4"
            self.assertTrue(output.is_file())
            result = subprocess.run([
                "ffprobe", "-v", "error", "-show_format", "-of", "json", str(output)
            ], capture_output=True, text=True, check=True)
            duration = float(json.loads(result.stdout)["format"]["duration"])
            self.assertAlmostEqual(duration, 3.6, delta=0.2)
            subprocess.run([sys.executable, str(RENDER), str(planfile)], check=True)
            self.assertTrue((root / "output" / "edited_v2.mp4").is_file())


if __name__ == "__main__":
    unittest.main()
