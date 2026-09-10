from __future__ import annotations

import base64
import json
import os
import subprocess
from pathlib import Path
from typing import Any


class MediaAnalysisError(ValueError):
    """Raised when an authorized uploaded media file cannot be prepared."""


def _run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(command, check=True, capture_output=True, timeout=600)
    except FileNotFoundError as error:
        raise MediaAnalysisError(f"필수 미디어 도구를 찾지 못했습니다: {command[0]}") from error
    except subprocess.TimeoutExpired as error:
        raise MediaAnalysisError("미디어 처리 시간이 초과되었습니다.") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", errors="replace")[-500:].strip()
        raise MediaAnalysisError(f"업로드한 영상을 처리하지 못했습니다. {detail}") from error


def _duration(path: Path) -> float:
    result = _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(path),
    ])
    try:
        duration = float(json.loads(result.stdout).get("format", {}).get("duration"))
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise MediaAnalysisError("영상 재생시간을 확인하지 못했습니다.") from error
    if duration <= 0:
        raise MediaAnalysisError("재생시간이 없는 영상입니다.")
    return duration


def _thumbnail(path: Path, output: Path, duration: float) -> str | None:
    timestamp = min(max(duration * 0.15, 0.1), max(duration - 0.1, 0.1))
    try:
        _run([
            "ffmpeg", "-y", "-ss", str(timestamp), "-i", str(path),
            "-frames:v", "1", "-vf", "scale='min(960,iw)':-2", "-q:v", "4", str(output),
        ])
    except MediaAnalysisError:
        return None
    if not output.exists():
        return None
    return "data:image/jpeg;base64," + base64.b64encode(output.read_bytes()).decode("ascii")


def collect_uploaded_evidence(path: Path, filename: str, workdir: Path) -> tuple[dict[str, Any], str]:
    duration = _duration(path)
    thumbnail_url = _thumbnail(path, workdir / "thumbnail.jpg", duration)
    audio_path = workdir / "audio.wav"
    streams = json.loads(_run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "json", str(path)]).stdout)
    if not streams.get("streams"):
        return {
            "url": f"upload://{filename}", "title": filename,
            "description": "음성 트랙이 없는 업로드 영상. 대표 프레임만 표시합니다.",
            "thumbnail_url": thumbnail_url, "duration_seconds": duration,
            "transcript_segments": [], "frame_candidates": [],
        }, "metadata-only"
    _run([
        "ffmpeg", "-y", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", str(audio_path),
    ])

    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise MediaAnalysisError("로컬 Whisper ASR가 설치되어 있지 않습니다.") from error

    model_name = os.getenv("WHISPER_MODEL", "tiny")
    try:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        transcript, _ = model.transcribe(str(audio_path), vad_filter=True)
        segments = [
            {
                "start_seconds": float(segment.start),
                "end_seconds": min(float(segment.end), duration),
                "text": segment.text.strip(),
            }
            for segment in transcript
            if segment.text.strip() and float(segment.end) > float(segment.start)
        ]
    except Exception as error:
        raise MediaAnalysisError(f"Whisper 음성 전사에 실패했습니다: {error}") from error

    mode = "local-asr" if segments else "metadata-only"
    return {
        "url": f"upload://{filename}",
        "title": filename,
        "description": "사용자가 직접 업로드한 영상",
        "thumbnail_url": thumbnail_url,
        "duration_seconds": duration,
        "transcript_segments": segments,
        "frame_candidates": [],
    }, mode
