from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class VideoBudget:
    max_iterations: int = 6
    max_tool_calls: int = 10
    max_transcript_results: int = 8
    max_transcript_characters: int = 24_000
    max_frames: int = 24
    max_range_seconds: int = 120
    max_fps: float = 2.0


class VideoTools(Protocol):
    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


class VideoAgentModel(Protocol):
    def next_action(self, state: dict[str, Any]) -> dict[str, Any]: ...


class IndexedVideoTools:
    """Policy-bounded tools over artifacts the host is allowed to use."""

    def __init__(self, evidence: dict[str, Any], budget: VideoBudget | None = None) -> None:
        self.evidence = evidence
        self.budget = budget or VideoBudget()
        self.transcript = list(evidence.get("transcript_segments", []))
        self.frames = list(evidence.get("frame_candidates", []))

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "get_video_metadata":
            return {key: self.evidence.get(key) for key in ("url", "title", "description", "duration_seconds")}
        if name == "search_transcript":
            return self._search_transcript(arguments)
        if name == "get_transcript_range":
            return self._transcript_range(arguments)
        if name == "get_frames":
            return self._get_frames(arguments)
        raise ValueError(f"unsupported video tool: {name}")

    def _search_transcript(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query", "")).strip().lower()
        if not query:
            raise ValueError("search_transcript.query is required")
        limit = min(max(int(arguments.get("limit", 5)), 1), self.budget.max_transcript_results)
        terms = [term for term in re.split(r"\s+", query) if term]
        ranked = sorted(self.transcript, key=lambda row: sum(term in str(row.get("text", "")).lower() for term in terms), reverse=True)
        matches = [row for row in ranked if any(term in str(row.get("text", "")).lower() for term in terms)][:limit]
        return {"segments": self._limit_text(matches)}

    def _transcript_range(self, arguments: dict[str, Any]) -> dict[str, Any]:
        start = float(arguments.get("start_seconds", 0))
        end = float(arguments.get("end_seconds", 0))
        self._validate_range(start, end)
        rows = [row for row in self.transcript if float(row.get("end_seconds", 0)) >= start and float(row.get("start_seconds", 0)) <= end]
        return {"segments": self._limit_text(rows)}

    def _get_frames(self, arguments: dict[str, Any]) -> dict[str, Any]:
        start = float(arguments.get("start_seconds", 0))
        end = float(arguments.get("end_seconds", 0))
        fps = float(arguments.get("fps", 1))
        self._validate_range(start, end)
        if not 0 < fps <= self.budget.max_fps:
            raise ValueError("frame fps exceeds policy")
        requested = min(int((end - start) * fps) + 1, self.budget.max_frames)
        rows = [row for row in self.frames if start <= float(row.get("timestamp_seconds", -1)) <= end][:requested]
        return {"frames": rows, "requested_fps": fps}

    def _validate_range(self, start: float, end: float) -> None:
        if start < 0 or end <= start or end - start > self.budget.max_range_seconds:
            raise ValueError("invalid or excessive video time range")

    def _limit_text(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        used = 0
        result = []
        for row in rows:
            text = str(row.get("text", ""))
            if used + len(text) > self.budget.max_transcript_characters:
                break
            used += len(text)
            result.append(row)
        return result


class AgenticVideoAnalyzer:
    def __init__(
        self,
        model: VideoAgentModel,
        tools: VideoTools,
        budget: VideoBudget | None = None,
        result_validator: Callable[[dict[str, Any], dict[str, Any]], None] | None = None,
        objective: str = "Extract information relevant to the host application.",
        result_schema: dict[str, Any] | None = None,
    ) -> None:
        self.model = model
        self.tools = tools
        self.budget = budget or VideoBudget()
        self.result_validator = result_validator
        self.objective = objective
        self.result_schema = result_schema

    def analyze(self, evidence: dict[str, Any]) -> dict[str, Any]:
        observations: list[dict[str, Any]] = []
        seen: set[str] = set()
        tool_calls = 0
        for iteration in range(self.budget.max_iterations):
            action = self.model.next_action(
                {
                    "objective": self.objective,
                    "result_schema": self.result_schema,
                    "source": {key: evidence.get(key) for key in ("url", "title", "description", "duration_seconds")},
                    "observations": observations,
                    "remaining_tool_calls": self.budget.max_tool_calls - tool_calls,
                    "iteration": iteration,
                }
            )
            name = str(action.get("action", ""))
            if name == "finish":
                result = action.get("result")
                if not isinstance(result, dict):
                    raise ValueError("finish action requires result")
                if self.result_validator:
                    self.result_validator(result, evidence)
                return result
            arguments = action.get("arguments") or {}
            fingerprint = json.dumps([name, arguments], sort_keys=True, ensure_ascii=False)
            if fingerprint in seen:
                raise ValueError("repeated video tool call")
            if tool_calls >= self.budget.max_tool_calls:
                raise ValueError("video tool call budget exceeded")
            seen.add(fingerprint)
            observations.append({"tool": name, "arguments": arguments, "output": self.tools.call(name, arguments)})
            tool_calls += 1
        raise ValueError("video agent iteration budget exceeded")
