from __future__ import annotations

import json
import urllib.parse
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from yt_dlp.networking.exceptions import RequestError


class YouTubeCollectionError(ValueError):
    """Raised when a public YouTube video cannot provide usable captions."""


def is_youtube_url(url: str) -> bool:
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return host in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def _caption_track(info: dict[str, Any], languages: tuple[str, ...]) -> dict[str, Any] | None:
    for source in (info.get("subtitles") or {}, info.get("automatic_captions") or {}):
        language_keys = list(source)
        ordered = [
            key for preferred in languages for key in language_keys
            if key == preferred or key.startswith(f"{preferred}-")
        ]
        ordered.extend(key for key in language_keys if key not in ordered and key != "live_chat")
        for language in ordered:
            formats = source.get(language) or []
            for extension in ("json3", "vtt"):
                match = next((item for item in formats if item.get("ext") == extension and item.get("url")), None)
                if match:
                    return {**match, "language": language}
    return None


def _json3_segments(payload: bytes) -> list[dict[str, Any]]:
    data = json.loads(payload)
    segments = []
    for event in data.get("events", []):
        text = "".join(part.get("utf8", "") for part in event.get("segs", [])).replace("\n", " ").strip()
        if not text:
            continue
        start = float(event.get("tStartMs", 0)) / 1000
        duration = float(event.get("dDurationMs", 0)) / 1000
        segments.append({"start_seconds": start, "end_seconds": start + max(duration, 0.001), "text": text})
    return segments


def _vtt_timestamp(value: str) -> float:
    pieces = value.replace(",", ".").split(":")
    return sum(float(piece) * (60 ** index) for index, piece in enumerate(reversed(pieces)))


def _vtt_segments(payload: bytes) -> list[dict[str, Any]]:
    lines = payload.decode("utf-8", errors="replace").splitlines()
    segments: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if " --> " not in line:
            continue
        start_text, end_text = (part.split()[0] for part in line.split(" --> ", 1))
        text_lines = []
        for text_line in lines[index + 1:]:
            if not text_line.strip():
                break
            if " --> " not in text_line:
                text_lines.append(text_line.strip())
        text = " ".join(text_lines).strip()
        if text:
            segments.append({"start_seconds": _vtt_timestamp(start_text), "end_seconds": _vtt_timestamp(end_text), "text": text})
    return segments


def collect_youtube_evidence(url: str, languages: tuple[str, ...] = ("ko", "en")) -> dict[str, Any]:
    if not is_youtube_url(url):
        raise YouTubeCollectionError("지원되는 YouTube 주소가 아닙니다.")
    try:
        with YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            track = _caption_track(info, languages)
            if not track:
                return {
                    "url": info.get("webpage_url") or url,
                    "title": info.get("title") or "YouTube video",
                    "description": info.get("description"),
                    "thumbnail_url": info.get("thumbnail"),
                    "duration_seconds": float(info.get("duration") or 1),
                    "transcript_segments": [], "frame_candidates": [],
                }
            with ydl.urlopen(track["url"]) as response:
                payload = response.read(10_000_000)
    except DownloadError as error:
        raise YouTubeCollectionError("YouTube 메타데이터를 가져오지 못했습니다. 공개 영상인지 확인하세요.") from error
    except RequestError as error:
        raise YouTubeCollectionError("YouTube 자막 요청이 제한되었거나 실패했습니다. 잠시 후 재시도하거나 영상 파일을 업로드하세요.") from error
    except OSError as error:
        raise YouTubeCollectionError("YouTube 자막을 내려받지 못했습니다.") from error

    segments = _json3_segments(payload) if track["ext"] == "json3" else _vtt_segments(payload)
    if not segments:
        raise YouTubeCollectionError("YouTube 자막은 존재하지만 분석 가능한 문장을 찾지 못했습니다.")
    return {
        "url": info.get("webpage_url") or url,
        "title": info.get("title") or "YouTube video",
        "description": info.get("description"),
        "thumbnail_url": info.get("thumbnail"),
        "duration_seconds": float(info.get("duration") or segments[-1]["end_seconds"]),
        "transcript_segments": segments,
        "frame_candidates": [],
        "caption_language": track["language"],
    }
