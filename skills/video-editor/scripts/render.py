#!/usr/bin/env python3
"""Deterministic local FFmpeg renderer for the video-editor Agent Skill.

Only Python's standard library, ffmpeg, and ffprobe are required.
No network access, paid APIs, or automatic overwrites.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FORMATS = {"shorts": (720, 1280), "landscape": (1280, 720), "square": (720, 720)}
TRANSITIONS = {"cut", "fade", "wipeleft", "wiperight"}


class EditError(Exception):
    pass


def run_capture(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise EditError(f"Command failed: {args[0]}\n{result.stderr[-2500:]}")
    return result.stdout


def safe_path(root: Path, value: str, *, must_exist: bool = True) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise EditError(f"Path must stay inside the project folder: {value}")
    if must_exist and not path.is_file():
        raise EditError(f"File not found: {value}")
    return path


def probe(path: Path) -> dict:
    raw = run_capture(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)])
    data = json.loads(raw)
    streams = data.get("streams", [])
    if not any(s.get("codec_type") == "video" for s in streams):
        raise EditError(f"No video stream: {path.name}")
    duration = float(data.get("format", {}).get("duration") or 0)
    if duration <= 0:
        raise EditError(f"Could not determine video duration: {path.name}")
    return {"duration": duration, "audio": any(s.get("codec_type") == "audio" for s in streams)}


def number(value, name: str, low: float = 0, high: float = 100000) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise EditError(f"{name} must be a number")
    value = float(value)
    if not low <= value <= high:
        raise EditError(f"{name} must be between {low} and {high}")
    return value


def timestamp(seconds: float) -> str:
    hundredths = max(0, round(seconds * 100))
    hours, remainder = divmod(hundredths, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, fraction = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{fraction:02d}"


def srt_seconds(value: str) -> float:
    value = value.replace(",", ".")
    parts = value.split(":")
    if len(parts) != 3:
        raise EditError(f"Bad SRT timestamp: {value}")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def read_srt(path: Path) -> list[tuple[float, float, str]]:
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip())
    cues = []
    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue
        index = 1 if lines[0].strip().isdigit() else 0
        if index >= len(lines):
            continue
        match = re.match(r"^(\d+:\d{2}:\d{2}[,.]\d+)\s*-->\s*(\d+:\d{2}:\d{2}[,.]\d+)", lines[index].strip())
        if not match:
            raise EditError(f"Invalid SRT timing in {path.name}")
        start, end = (srt_seconds(x) for x in match.groups())
        if end <= start:
            raise EditError("Subtitle end must be after start")
        cues.append((start, end, "\n".join(lines[index + 1:])))
    if not cues:
        raise EditError("No subtitle cues found in SRT file")
    return cues


def ass_color(value: str) -> str:
    if not re.fullmatch(r"#?[0-9A-Fa-f]{6}", value):
        raise EditError("Subtitle color must be #RRGGBB")
    rgb = value.lstrip("#")
    return "&H00" + rgb[4:6] + rgb[2:4] + rgb[0:2]


def ass_text(value: str) -> str:
    return value.replace("\\", "＼").replace("{", "（").replace("}", "）").replace("\n", r"\N")


def create_ass(plan: dict, root: Path, workdir: Path, width: int, height: int, total: float) -> Path | None:
    captions = plan.get("subtitles")
    title = plan.get("title")
    if not captions and not title:
        return None
    style = captions or {}
    font = str(style.get("font", "Arial")).strip()
    if not font or "," in font or "\n" in font:
        raise EditError("Invalid font family name")
    size = int(number(style.get("size", 48), "subtitle size", 14, 150))
    outline = number(style.get("outline", 3), "subtitle outline", 0, 10)
    color = ass_color(str(style.get("color", "#FFFFFF")))
    title_font = str((title or {}).get("font", font)).strip()
    if not title_font or "," in title_font or "\n" in title_font:
        raise EditError("Invalid title font name")
    if style.get("font_file"):
        fontfile = safe_path(root, str(style["font_file"]))
        if fontfile.suffix.lower() not in {".ttf", ".otf"}:
            raise EditError("Font file must be .ttf or .otf")
        shutil.copy2(fontfile, workdir / fontfile.name)

    header = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Subtitle,{font},{size},{color},&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{outline:g},0,2,35,35,65,1",
        f"Style: Title,{title_font},{int(number((title or {}).get('size', 66), 'title size', 16, 160))},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,0,8,35,35,100,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    if captions:
        path = safe_path(root, str(captions["file"]))
        for start, end, text in read_srt(path):
            if start >= total:
                continue
            header.append(f"Dialogue: 0,{timestamp(start)},{timestamp(min(end,total))},Subtitle,,0,0,0,,{ass_text(text)}")
    if title:
        start = number(title.get("start", 0), "title start", 0, total)
        end = number(title.get("end", min(total, 2.5)), "title end", 0, total)
        if end <= start:
            raise EditError("Title end must be after title start")
        header.append(f"Dialogue: 1,{timestamp(start)},{timestamp(end)},Title,,0,0,0,,{ass_text(str(title['text']))}")
    ass = workdir / "overlays.ass"
    ass.write_text("\n".join(header) + "\n", encoding="utf-8")
    return ass


def choose_output(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}_v{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise EditError("Too many existing output versions")


def plan_command(plan: dict, root: Path, workdir: Path) -> tuple[list[str], Path, float]:
    if not isinstance(plan.get("clips"), list) or not 1 <= len(plan["clips"]) <= 12:
        raise EditError("Plan must contain 1-12 clips")
    fmt = plan.get("format", "shorts")
    if fmt not in FORMATS:
        raise EditError("format must be shorts, landscape, or square")
    width, height = FORMATS[fmt]
    if "resolution" in plan:
        res = plan["resolution"]
        if not isinstance(res, list) or len(res) != 2:
            raise EditError("resolution must be [width, height]")
        width, height = (int(number(x, "resolution", 256, 3840)) for x in res)
        if width % 2 or height % 2:
            raise EditError("resolution dimensions must be even")
    fps = int(number(plan.get("fps", 30), "fps", 24, 60))
    if fps not in {24, 25, 30, 50, 60}:
        raise EditError("fps must be 24, 25, 30, 50, or 60")
    transition = plan.get("transition", {}) or {}
    effect = str(transition.get("type", "cut"))
    if effect not in TRANSITIONS:
        raise EditError("transition type must be cut, fade, wipeleft, or wiperight")
    d = number(transition.get("duration", 0.4 if effect != "cut" else 0), "transition duration", 0, 3)
    if effect == "cut":
        d = 0

    clips = []
    cmd = ["ffmpeg", "-hide_banner", "-y"]
    for index, item in enumerate(plan["clips"]):
        if not isinstance(item, dict) or "file" not in item:
            raise EditError(f"Clip {index + 1} needs a file")
        path = safe_path(root, str(item["file"]))
        info = probe(path)
        start = number(item.get("start", 0), "start", 0, info["duration"])
        end = number(item.get("end", info["duration"]), "end", 0, info["duration"])
        if end - start <= 0.05:
            raise EditError(f"Invalid clip range: {path.name}")
        speed = number(item.get("speed", 1.0), "speed", 0.5, 2.0)
        duration = (end - start) / speed
        if d and duration <= d + 0.05:
            raise EditError("A clip is too short for the requested transition")
        clips.append({"start": start, "end": end, "speed": speed, "duration": duration, "audio": info["audio"]})
        cmd += ["-i", str(path)]

    music = plan.get("music")
    if music:
        if not isinstance(music, dict) or "file" not in music:
            raise EditError("music must contain a file")
        musicfile = safe_path(root, str(music["file"]))
        cmd += ["-stream_loop", "-1", "-i", str(musicfile)]

    total = sum(x["duration"] for x in clips) - d * (len(clips) - 1)
    fade = plan.get("fade", {}) or {}
    fade_in = number(fade.get("in", 0), "fade in", 0, 5)
    fade_out = number(fade.get("out", 0), "fade out", 0, 5)
    if fade_in + fade_out > total:
        raise EditError("Fade durations exceed video length")
    source_volume = number(plan.get("original_audio_volume", 1), "original audio volume", 0, 2)
    filters = []
    fit = plan.get("fit", "crop")
    if fit not in {"crop", "pad"}:
        raise EditError("fit must be crop or pad")
    resize = (f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
              if fit == "crop" else
              f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2")
    for i, clip in enumerate(clips):
        start, end, speed, duration = (clip[k] for k in ("start", "end", "speed", "duration"))
        filters.append(f"[{i}:v]trim=start={start:g}:end={end:g},setpts=(PTS-STARTPTS)/{speed:g},fps={fps},{resize},setsar=1,format=yuv420p,settb=AVTB[v{i}]")
        if clip["audio"]:
            filters.append(f"[{i}:a]atrim=start={start:g}:end={end:g},asetpts=PTS-STARTPTS,atempo={speed:g},aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={duration:g},atrim=duration={duration:g},asetpts=PTS-STARTPTS[a{i}]")
        else:
            filters.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={duration:g},asetpts=PTS-STARTPTS[a{i}]")

    v, a = "v0", "a0"
    running = clips[0]["duration"]
    for i in range(1, len(clips)):
        nv, na = f"joinedv{i}", f"joineda{i}"
        if effect == "cut":
            filters.append(f"[{v}][v{i}]concat=n=2:v=1:a=0[{nv}]")
            filters.append(f"[{a}][a{i}]concat=n=2:v=0:a=1[{na}]")
        else:
            offset = running - d
            filters.append(f"[{v}][v{i}]xfade=transition={effect}:duration={d:g}:offset={offset:g}[{nv}]")
            filters.append(f"[{a}][a{i}]acrossfade=d={d:g}[{na}]")
        running += clips[i]["duration"] - d
        v, a = nv, na

    if fade_in or fade_out:
        chain = []
        if fade_in:
            chain.append(f"fade=t=in:st=0:d={fade_in:g}")
        if fade_out:
            chain.append(f"fade=t=out:st={total-fade_out:g}:d={fade_out:g}")
        filters.append(f"[{v}]{','.join(chain)}[fadedv]")
        v = "fadedv"

    ass = create_ass(plan, root, workdir, width, height, total)
    if ass:
        filters.append(f"[{v}]ass=overlays.ass:fontsdir=.[captionedv]")
        v = "captionedv"

    filters.append(f"[{a}]volume={source_volume:g}[sourcea]")
    a = "sourcea"
    if music:
        volume = number(music.get("volume", 0.2), "music volume", 0, 2)
        filters.append(f"[{len(clips)}:a]atrim=duration={total:g},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,volume={volume:g}[bgm]")
        filters.append(f"[{a}][bgm]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[mixeda]")
        a = "mixeda"
    if fade_in or fade_out:
        chain = []
        if fade_in:
            chain.append(f"afade=t=in:st=0:d={fade_in:g}")
        if fade_out:
            chain.append(f"afade=t=out:st={total-fade_out:g}:d={fade_out:g}")
        filters.append(f"[{a}]{','.join(chain)}[fadeda]")
        a = "fadeda"

    output_value = plan.get("output", "output/edited.mp4")
    output = safe_path(root, str(output_value), must_exist=False)
    if output.suffix.lower() != ".mp4":
        raise EditError("Output must end with .mp4")
    if not output.parent.is_relative_to(root / "output"):
        raise EditError("Output must be inside the project's output/ folder")
    output = choose_output(output)
    cmd += ["-filter_complex", ";".join(filters), "-map", f"[{v}]", "-map", f"[{a}]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
            "-t", f"{total:.3f}", str(output)]
    return cmd, output, total


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a local video edit plan using FFmpeg")
    parser.add_argument("plan", type=Path, help="Path to edit-plan.json")
    parser.add_argument("--dry-run", action="store_true", help="Validate and show the FFmpeg command")
    args = parser.parse_args()
    try:
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise EditError("Install FFmpeg and ffprobe, and add both to PATH")
        plan_path = args.plan.resolve()
        root = plan_path.parent
        if not plan_path.is_file():
            raise EditError(f"Plan not found: {plan_path}")
        plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        with tempfile.TemporaryDirectory(prefix="ai-video-editor-") as tmp:
            workdir = Path(tmp)
            command, output, expected = plan_command(plan, root, workdir)
            if args.dry_run:
                print("Validated plan. Expected seconds:", round(expected, 3))
                print("FFmpeg command:", subprocess.list2cmdline(command))
                return 0
            output.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(command, cwd=workdir)
            if result.returncode:
                raise EditError(f"FFmpeg failed with exit code {result.returncode}")
            measured = probe(output)
            print(f"Created: {output}")
            print(f"Duration: {measured['duration']:.2f}s (expected about {expected:.2f}s)")
            return 0
    except (EditError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
