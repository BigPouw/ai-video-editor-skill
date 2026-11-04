#!/usr/bin/env python3
"""Optional, explicitly paid ElevenLabs Scribe v2 transcription to SRT.

Requires only the Python standard library. Never called by render.py.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def srt_time(seconds: float) -> str:
    ms = max(0, round(float(seconds) * 1000))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def join_text(current: str, token: str) -> str:
    if not current:
        return token.strip()
    if token.startswith((" ", "\n")) or re.match(r"^[,.!?;:，。！？；：、]", token):
        return current + token
    if re.search(r"[A-Za-z0-9]$", current) and re.match(r"^[A-Za-z0-9]", token):
        return current + " " + token
    return current + token


def transcript_to_srt(transcription: dict) -> str:
    words = transcription.get("words")
    if not isinstance(words, list) or not words:
        raise ValueError("ElevenLabs did not return word timestamps")
    captions = []
    text, start, end = "", None, None
    for item in words:
        if not isinstance(item, dict) or item.get("type") not in (None, "word", "spacing", "punctuation"):
            continue
        token = str(item.get("text", ""))
        if not token:
            continue
        try:
            word_start = float(item.get("start")) if item.get("start") is not None else end
            word_end = float(item.get("end")) if item.get("end") is not None else end
        except (TypeError, ValueError):
            continue
        if word_start is None or word_end is None or word_end < word_start:
            continue
        if start is not None and text and (word_end - start > 4.0 or len(text) + len(token) > 34):
            captions.append((start, end, text.strip()))
            text, start, end = "", None, None
        if start is None:
            start = word_start
        end = word_end
        text = join_text(text, token)
        if re.search(r"[.!?。！？]$", text) and end - start >= 0.7:
            captions.append((start, end, text.strip()))
            text, start, end = "", None, None
    if text and start is not None and end is not None:
        captions.append((start, end, text.strip()))
    if not captions:
        raise ValueError("Transcript contains no timed speech")
    return "\n\n".join(
        f"{i}\n{srt_time(start)} --> {srt_time(max(end, start + 0.1))}\n{text}"
        for i, (start, end, text) in enumerate(captions, 1)
    ) + "\n"


def multipart(media_path: Path) -> tuple[bytes, str]:
    boundary = "----videoeditor" + uuid.uuid4().hex
    raw = media_path.read_bytes()
    fields = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"model_id\"\r\n\r\nscribe_v2\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"timestamps_granularity\"\r\n\r\nword\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"media{media_path.suffix.lower()}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode() + raw + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return b"".join(fields), boundary


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert spoken media to SRT with ElevenLabs")
    parser.add_argument("media", type=Path, help="Audio or video to upload")
    parser.add_argument("--output", type=Path, default=Path("output/transcript.srt"))
    parser.add_argument("--confirm-api-cost", action="store_true",
                        help="Explicitly authorize uploading the media and using a billed ElevenLabs API")
    args = parser.parse_args()
    if not args.confirm_api_cost:
        parser.error("Explicit --confirm-api-cost is required. This sends media to ElevenLabs and may incur charges.")
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        parser.error("Set ELEVENLABS_API_KEY in your environment (never in GitHub)")
    if not args.media.is_file():
        parser.error("Media file does not exist")
    if args.media.stat().st_size > 25 * 1024 * 1024:
        parser.error("For this simple prototype, use a media file under 25 MiB or extract/compress audio first")
    if args.output.resolve() == args.media.resolve():
        parser.error("Output must not replace the input")
    if args.output.exists():
        parser.error("Output SRT exists; choose another filename to avoid overwriting")
    try:
        body, boundary = multipart(args.media)
        request = urllib.request.Request(
            "https://api.elevenlabs.io/v1/speech-to-text",
            data=body,
            headers={"xi-api-key": api_key, "Content-Type": f"multipart/form-data; boundary={boundary}",
                     "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
        srt = transcript_to_srt(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(srt, encoding="utf-8")
        print(f"Created: {args.output} (review and correct captions before publishing)")
        return 0
    except urllib.error.HTTPError as exc:
        print(f"ElevenLabs API failed with HTTP {exc.code}: {exc.read(600).decode('utf-8','replace')}", file=sys.stderr)
    except (urllib.error.URLError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Transcription failed: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
