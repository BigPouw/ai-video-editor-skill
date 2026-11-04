"""Local tests: synthetic media only; no downloads or paid API calls."""
from __future__ import annotations

import importlib.util
import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from array import array
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


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg and ffprobe are needed for integration tests")
class ClipMusicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.root = Path(directory.name)
        inputs = cls.root / "input"
        inputs.mkdir()
        for name, color in (("a", "red"), ("b", "blue")):
            audio = ["-f", "lavfi", "-i", "sine=frequency=1200:duration=2", "-c:a", "aac"] if name == "a" else []
            subprocess.run([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color={color}:s=320x180:r=30:d=2",
                *audio, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(inputs / f"{name}.mp4"),
            ], check=True)
        for name, freq, duration in (("x.mp3", 400, 0.6), ("y.wav", 800, 2), ("global.wav", 1600, 2)):
            subprocess.run([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}",
                str(inputs / name),
            ], check=True)
        subprocess.run([
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "sine=frequency=600:duration=0.25",
            "-f", "lavfi", "-i", "sine=frequency=800:duration=0.75",
            "-filter_complex", "concat=n=2:v=0:a=1", str(inputs / "offset.wav"),
        ], check=True)

    def render(self, clips, duration, **settings):
        output = f"output/{self._testMethodName}.mp4"
        plan = {"clips": clips, "resolution": [320, 320], "output": output, **settings}
        planfile = self.root / "edit-plan.json"
        planfile.write_text(json.dumps(plan), encoding="utf-8")
        rendered = subprocess.run([sys.executable, str(RENDER), str(planfile)], capture_output=True, text=True)
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        file = str(self.root / output)
        probe = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "stream=codec_name,duration:format=duration",
            "-of", "json", file,
        ])
        media = json.loads(probe)
        self.assertAlmostEqual(float(media["format"]["duration"]), duration, delta=0.04)
        self.assertEqual([s["codec_name"] for s in media["streams"]], ["h264", "aac"])
        for stream in media["streams"]:
            self.assertAlmostEqual(float(stream["duration"]), duration, delta=0.04)
        pcm = subprocess.check_output([
            "ffmpeg", "-v", "error", "-xerror", "-i", file, "-map", "0:a:0",
            "-ac", "1", "-ar", "48000", "-f", "f32le", "-",
        ])
        samples = array("f", pcm)
        if sys.byteorder != "little":
            samples.byteswap()
        return samples

    @staticmethod
    def tone(samples, center, frequency):
        # Measure the sinusoidal component over 50 ms, independently of its phase.
        window = samples[round((center - 0.025) * 48000):round((center + 0.025) * 48000)]
        step = math.tau * frequency / 48000
        real = sum(sample * math.cos(i * step) for i, sample in enumerate(window))
        imag = sum(sample * math.sin(i * step) for i, sample in enumerate(window))
        return 2 * math.hypot(real, imag) / len(window)

    def test_independent_music_loops_and_crossfades(self):
        samples = self.render([
            {"file": "input/a.mp4", "end": 2, "music": {"file": "input/x.mp3", "volume": 0.5}},
            {"file": "input/b.mp4", "end": 2, "music": {"file": "input/y.wav", "volume": 0.5}},
        ], 3.5, transition={"type": "fade", "duration": 0.5}, original_audio_volume=0.25,
            music={"file": "input/global.wav", "volume": 1})
        x, y = self.tone(samples, 1.35, 400), self.tone(samples, 2.5, 800)
        self.assertGreater(x, 0.03)  # X is still audible after two loops.
        self.assertGreater(y, 0.03)
        self.assertLess(self.tone(samples, 1.35, 800), 0.003)
        self.assertLess(self.tone(samples, 2.5, 400), 0.003)
        self.assertLess(self.tone(samples, 1.35, 1600), 0.003)
        self.assertLess(self.tone(samples, 2.5, 1600), 0.003)
        self.assertAlmostEqual(self.tone(samples, 1.35, 1200), y / 2, delta=0.005)
        self.assertLess(self.tone(samples, 2.5, 1200), 0.003)
        # The complementary gains move together over the same 0.5 s as the video.
        for center, incoming in ((1.625, 0.25), (1.75, 0.5), (1.875, 0.75)):
            with self.subTest(center=center):
                self.assertAlmostEqual(self.tone(samples, center, 400) / x, 1 - incoming, delta=0.1)
                self.assertAlmostEqual(self.tone(samples, center, 800) / y, incoming, delta=0.1)

    def test_unscored_clip_keeps_original_audio(self):
        samples = self.render([
            {"file": "input/a.mp4", "end": 2},
            {"file": "input/b.mp4", "end": 2, "music": {"file": "input/y.wav", "volume": 0.5}},
        ], 4, original_audio_volume=0.5)
        self.assertGreater(self.tone(samples, 1.5, 1200), 0.03)
        self.assertLess(self.tone(samples, 1.5, 800), 0.003)
        self.assertGreater(self.tone(samples, 2.5, 800), 0.03)
        self.assertLess(self.tone(samples, 2.5, 1200), 0.003)

    def test_single_clip_music_offset_and_muted_source(self):
        samples = self.render([
            {"file": "input/a.mp4", "end": 2, "speed": 2,
             "music": {"file": "input/offset.wav", "volume": 0.5, "start": 0.25}},
        ], 1, original_audio_volume=0)
        self.assertGreater(self.tone(samples, 0.15, 800), 0.03)
        self.assertLess(self.tone(samples, 0.15, 600), 0.003)
        self.assertLess(self.tone(samples, 0.15, 1200), 0.003)
        self.assertGreater(self.tone(samples, 0.85, 600), 0.03)  # Loop returns to the file's beginning.

    def test_invalid_clip_music_is_rejected_during_dry_run(self):
        planfile = self.root / "edit-plan.json"
        for music, error in (
            ({}, "must contain a file"),
            ({"file": "../x.mp3"}, "must stay inside"),
            ({"file": "input/missing.mp3"}, "File not found"),
            ({"file": "input/b.mp4"}, "has no audio stream"),
            ({"file": "input/y.wav", "start": 2}, "start must be before the end"),
            ({"file": "input/y.wav", "volume": 3}, "volume must be between"),
        ):
            with self.subTest(music=music):
                planfile.write_text(json.dumps({"clips": [{"file": "input/a.mp4", "music": music}]}), encoding="utf-8")
                result = subprocess.run([sys.executable, str(RENDER), str(planfile), "--dry-run"],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(error, result.stderr)


if __name__ == "__main__":
    unittest.main()
