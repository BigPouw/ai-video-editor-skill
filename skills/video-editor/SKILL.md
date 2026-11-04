---
name: video-editor
description: Edit local video/audio into MP4 with FFmpeg. Use for cuts, combining clips, Shorts, music, fades, titles, SRT captions, or opt-in ElevenLabs transcription.
---

# Local Video Editor

Use the bundled deterministic scripts for video-editing requests. This is a portable Agent Skill for Codex, Claude Code and Google Antigravity (other agents with local command execution may also follow it). It does not require any AI API for ordinary editing.

## First actions

1. Locate the user's working folder and media. Prefer `input/`, but accept explicitly named local files. Treat filenames as hints, not evidence of the video's content. Inspect video/audio streams and durations using `ffprobe`.
2. Check `python`/`python3`, `ffmpeg` and `ffprobe`. If FFmpeg tools are not on PATH, first look for existing binaries (including a project-local `.tools/` directory). If still missing and permitted, obtain a portable FFmpeg distribution for the current OS from a trusted source linked by https://ffmpeg.org/download.html and extract it under the user's working project `.tools/` directory. Prepend its binary folder to PATH **for each command running `render.py`/`ffprobe`** (or pass a process-local environment to the renderer), verify `ffmpeg` and `ffprobe`, then continue the task. Do not change system-wide PATH, install globally, or request administrator access automatically. If Python is missing, a trusted source cannot be confirmed, elevated/system changes are needed, or the agent platform asks for approval, pause for the specific user action; never bypass platform permissions.
3. Summarize the intended clip order and clip-to-music assignments before rendering. When a user pairs A with X and B with Y, use each clip's `music` field. Infer the minimum useful edit and ask a focused question only when a file is missing or an important choice is unclear. Translate the user's natural-language request into the plan yourself.
4. Keep all input files unchanged. Put the plan at the project root as `edit-plan.json`; put MP4 and optional caption output inside `output/`.

## Execute edits

Use `scripts/render.py` relative to **this SKILL.md's directory**. The script's first argument is the absolute path to the user's `edit-plan.json`:

```shell
python <SKILL_DIR>/scripts/render.py <PROJECT_DIR>/edit-plan.json --dry-run
python <SKILL_DIR>/scripts/render.py <PROJECT_DIR>/edit-plan.json
```

Use the local `python3` or `py -3` launcher where appropriate. Never use shell-evaluated interpolations of user filenames; pass arguments as safely quoted paths. Fix validation failures and retry. Do not bypass the renderer for supported edits unless necessary to repair a documented limitation.

### Edit plan (JSON)

All file paths are relative to the directory containing `edit-plan.json`, and must stay inside it. `output` must remain inside `output/`. The renderer chooses a new filename (e.g. `edited_v2.mp4`) when an output already exists.

```json
{
  "clips": [
    {"file": "input/01.mp4", "start": 0, "end": 5, "speed": 1.0, "music": {"file": "input/X.mp3", "volume": 0.2}},
    {"file": "input/02.mp4", "start": 1, "end": 7, "music": {"file": "input/Y.mp3", "volume": 0.2, "start": 1}}
  ],
  "format": "shorts",
  "fit": "crop",
  "fps": 30,
  "transition": {"type": "fade", "duration": 0.4},
  "fade": {"in": 0.3, "out": 0.6},
  "original_audio_volume": 1.0,
  "title": {"text": "我的大學生活", "start": 0, "end": 2, "size": 66},
  "subtitles": {"file": "input/captions.srt", "font": "Arial", "size": 48, "color": "#FFFFFF", "outline": 3},
  "output": "output/edited.mp4"
}
```

- `clips`: 1–12. `start`/`end` are original media seconds; `end` may be omitted to use full duration. `speed`: 0.5–2.0.
- `format`: `shorts` (720×1280), `landscape` (1280×720), `square` (720×720); optional even `resolution: [1080,1920]`.
- `fit`: `crop` (fills frame, may cut the sides) or `pad` (preserves whole frame). Prefer `pad` if a person's face or important content would be cropped.
- `transition.type`: `cut`, `fade`, `wipeleft`, `wiperight`. All inter-clip transitions use the same type and duration. Default is `cut` with no decorative effect.
- `fade.in`/`fade.out`: seconds applied to image and final audio.
- `clips[].music` is optional. It takes a local audio `file`, an optional `volume` multiplier (0–2, default 0.2), and an optional `start` offset in seconds (default 0, before the end of the audio). Music plays at normal speed for the clip's edited duration and loops from the beginning of the audio file as needed.
- Clip music mixes with the clip's original sound, which is scaled by `original_audio_volume` (default 1, set to 0 to mute). Clip audio crossfades for the same duration as any non-cut video transition.
- Use top-level `music: {"file": "input/music.mp3", "volume": 0.2}` for one continuous track across the whole edit. It loops as needed. If any clip has its own music, the renderer ignores top-level `music` and unscored clips play their original sound only.
- `title` and `subtitles` are optional.
- SRT timestamps must refer to the **edited output timeline**. Font names must exist on the user's system. `subtitles.font_file` may point to a local TTF/OTF; the configured font family must match the file's real family name.

If a user asks only to combine clips, use hard cuts with default format; apply transitions/fades only when requested.

## Optional auto-caption workflow — explicit approval required

**Do not call any paid or network API by default.** ElevenLabs Speech-to-Text uploads user media, consumes usage, and requires a personal `ELEVENLABS_API_KEY` environment variable.

1. If an existing SRT is supplied, render that and skip all API calls.
2. If the user wants *automatic* captions, explain the upload and possible cost and obtain **explicit consent for this particular call**.
3. First render the video without captions. After approval, call `scripts/transcribe_elevenlabs.py` on the edited MP4 with `--confirm-api-cost`, outputting a unique `output/*.srt`. Input must be below 25 MiB; ask before compressing and uploading a larger file.
4. Ask the user to check transcript wording. Update the plan to point `subtitles.file` to the generated SRT and render a new MP4 version. The transcriber never runs from `render.py`.

Never print, commit, paste or store the API key in project files.

## Final verification and report

- Check exit code and use `ffprobe` to verify playable MP4, video/audio streams, format and approximate duration.
- Let the user preview the output, especially cropping, captions, font fallback and audio balance. Do not claim visual quality was checked unless it was actually inspected.
- Report original files used, applied edits, output file and any limitations.
- Do not upload user media, render outputs, private audio, API responses, keys, or accounts to GitHub. Never auto-publish to social platforms.
