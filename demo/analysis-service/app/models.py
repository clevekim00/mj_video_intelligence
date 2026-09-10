from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(alias_generator=lambda value: "".join(
        word if index == 0 else word.capitalize()
        for index, word in enumerate(value.split("_"))
    ), populate_by_name=True)

    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    text: str


class FrameCandidate(BaseModel):
    model_config = ConfigDict(alias_generator=lambda value: "".join(
        word if index == 0 else word.capitalize()
        for index, word in enumerate(value.split("_"))
    ), populate_by_name=True)

    timestamp_seconds: float = Field(ge=0)
    artifact_ref: str
    text: str | None = None


class Evidence(BaseModel):
    model_config = ConfigDict(alias_generator=lambda value: "".join(
        word if index == 0 else word.capitalize()
        for index, word in enumerate(value.split("_"))
    ), populate_by_name=True)

    url: str
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    duration_seconds: float = Field(gt=0)
    transcript_segments: list[TranscriptSegment] = Field(default_factory=list)
    frame_candidates: list[FrameCandidate] = Field(default_factory=list)


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(alias_generator=lambda value: "".join(
        word if index == 0 else word.capitalize()
        for index, word in enumerate(value.split("_"))
    ), populate_by_name=True)

    objective: str = Field(min_length=1)
    result_schema: dict[str, Any] | None = None
    evidence: Evidence


class AnalysisResponse(BaseModel):
    result: dict[str, Any]
    mode: str
