from __future__ import annotations

import os
import re
from typing import Any

from mj_video_intelligence import (
    AgenticVideoAnalyzer,
    IndexedVideoTools,
    OpenAIVideoAgentModel,
    VideoBudget,
)

from .models import AnalysisRequest
from .youtube import collect_youtube_evidence, is_youtube_url


class DemoVideoAgentModel:
    """Deterministic model used to make the sample runnable without credentials."""

    def __init__(self) -> None:
        self.observed = False

    def next_action(self, state: dict[str, Any]) -> dict[str, Any]:
        required = (state.get("result_schema") or {}).get("required", [])
        if "findings" in required:
            observations = state["observations"]
            duration = float(state["source"].get("duration_seconds") or 0)
            window = min(duration, 120.0)
            window_count = 1 if duration <= window else 5
            if len(observations) < window_count:
                start = 0.0 if window_count == 1 else (duration - window) * len(observations) / (window_count - 1)
                return {
                    "action": "get_transcript_range",
                    "arguments": {"start_seconds": start, "end_seconds": start + window},
                }
            findings = []
            seen = set()
            for observation in observations:
                for segment in observation["output"].get("segments", []):
                    key = (segment.get("start_seconds"), segment.get("text"))
                    if key in seen:
                        continue
                    seen.add(key)
                    findings.append({
                        "type": "transcript",
                        "text": str(segment.get("text", "")),
                        "startSeconds": segment.get("start_seconds"),
                        "endSeconds": segment.get("end_seconds"),
                    })
            return {"action": "finish", "result": {"findings": findings[:50]}}

        if not self.observed:
            self.observed = True
            return {"action": "search_transcript", "arguments": {"query": "카페 아이스크림 가격", "limit": 8}}

        segments = next(
            (item["output"].get("segments", []) for item in state["observations"] if item["tool"] == "search_transcript"),
            [],
        )
        restaurants = []
        for segment in segments:
            text = str(segment.get("text", ""))
            price_match = re.search(r"(\d[\d,]*)\s*원", text)
            name_match = re.search(r"([가-힣A-Za-z0-9 ]+카페)", text)
            menu_match = re.search(r"([가-힣A-Za-z0-9 ]*아이스크림)", text)
            restaurants.append({
                "name": name_match.group(1).strip() if name_match else "확인 필요",
                "recommendedMenu": menu_match.group(1).strip() if menu_match else None,
                "price": int(price_match.group(1).replace(",", "")) if price_match else None,
                "evidence": {
                    "type": "transcript",
                    "startSeconds": segment.get("start_seconds"),
                    "endSeconds": segment.get("end_seconds"),
                    "text": text,
                },
            })
        return {"action": "finish", "result": {"restaurants": restaurants}}


def _validate_result(result: dict[str, Any], evidence: dict[str, Any]) -> None:
    duration = float(evidence["duration_seconds"])
    evidence_items = [item.get("evidence") or {} for item in result.get("restaurants", [])]
    evidence_items.extend(result.get("findings", []))
    for proof in evidence_items:
        start = proof.get("startSeconds")
        end = proof.get("endSeconds")
        if start is None or end is None or not 0 <= float(start) < float(end) <= duration:
            raise ValueError("result contains an invalid evidence range")


def analyze(request: AnalysisRequest) -> tuple[dict[str, Any], str]:
    evidence = request.evidence.model_dump()
    if is_youtube_url(evidence["url"]) and not evidence["transcript_segments"]:
        evidence = collect_youtube_evidence(evidence["url"])
    budget = VideoBudget(max_iterations=6, max_tool_calls=10, max_frames=24)
    base_url = os.getenv("VIDEO_MODEL_BASE_URL")
    model_name = os.getenv("VIDEO_MODEL_NAME")
    if base_url and model_name:
        model = OpenAIVideoAgentModel(
            base_url=base_url,
            model=model_name,
            api_key=os.getenv("VIDEO_MODEL_API_KEY", "local"),
        )
        mode = "openai-compatible"
    else:
        model = DemoVideoAgentModel()
        mode = "demo"

    required = (request.result_schema or {}).get("required", [])
    analyzer = AgenticVideoAnalyzer(
        model=model,
        tools=IndexedVideoTools(evidence, budget),
        budget=budget,
        objective=request.objective,
        result_schema=request.result_schema,
        result_validator=lambda result, source: (
            (_validate_result(result, source))
            if all(key in result for key in required)
            else (_ for _ in ()).throw(ValueError("result is missing a required field"))
        ),
    )
    if not evidence["transcript_segments"]:
        result = {key: [] for key in required}
        result["notice"] = "사용 가능한 음성 자막이 없어 메타데이터만 표시합니다. 영상 파일 업로드로 음성 전사를 시도할 수 있습니다. 화면 OCR·사물 인식은 아직 지원하지 않습니다."
        mode = "metadata-only"
    else:
        result = analyzer.analyze(evidence)
        if mode == "demo":
            result["notice"] = "데모 규칙 기반 결과입니다. 범용 결과는 일부 자막 구간을 최대 50개 표시하며 전체 의미 분석은 모델 연결이 필요합니다."
    result["video"] = {
        "url": evidence["url"],
        "title": evidence["title"],
        "description": evidence.get("description"),
        "thumbnailUrl": evidence.get("thumbnail_url"),
        "durationSeconds": evidence["duration_seconds"],
    }
    return result, mode


def analyze_prepared_evidence(request: AnalysisRequest, evidence: dict[str, Any], source_mode: str) -> tuple[dict[str, Any], str]:
    request = request.model_copy(update={"evidence": request.evidence.model_validate(evidence)})
    result, model_mode = analyze(request)
    return result, f"{source_mode}+{model_mode}"
