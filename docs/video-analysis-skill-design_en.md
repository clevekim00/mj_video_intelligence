# Local video analysis skill implementation design

[한국어](video-analysis-skill-design.md) | **English**

Status: implementation proposal. This document does not indicate that the skill
has been created/installed or that new features are complete.
See the [usage guide](skill-usage_en.md) for the currently implemented scope.

## Goals and decisions

Give `$video-analysis` a YouTube URL or local video/audio file and an objective.
It collects evidence through public captions or local ASR and generates structured
results with a local LLM, including evidence timestamps, coverage and missing
analysis methods.

The primary execution path is a Python CLI. React, Spring Boot and Docker are not
required to run the skill. The existing demo wraps the same Python runtime with
HTTP. Calling the existing Spring API remains an optional integration for reusing
an already-running demo.

The analysis engine can be configured without a paid LLM API. Account and usage
terms for the host invoking the Codex skill are separate. The CLI also runs
directly without Codex.

## Reuse from the current code

| Current component | Reuse and change |
|---|---|
| `mj_video_intelligence/core.py` | Keep budgets, evidence search and agent loop |
| `mj_video_intelligence/openai.py` | Keep local OpenAI-compatible connection; add JSON response compatibility checks |
| `demo/analysis-service/app/youtube.py` | Move public caption/metadata collection to a shared adapter |
| `demo/analysis-service/app/media.py` | Move ffmpeg/faster-whisper processing to a shared adapter |
| `demo/analysis-service/app/service.py` | Separate execution functions from HTTP DTOs |
| `DemoVideoAgentModel` | Use only in explicit test/demo mode |

The generic demo currently returns up to 50 sampled transcript excerpts.
Do not call this full semantic analysis. OCR/vision inference is unimplemented
and remains a separate later phase.

## Structure

```text
Codex skill ── CLI invocation ── Python runtime
Terminal ───── CLI invocation ──┤
React → Spring → FastAPI ───────┤
                               ├─ YouTube public captions / metadata
                               ├─ Local file → ffmpeg → Whisper
                               ├─ Evidence index → local LLM → validation
                               └─ result.json / report.md
```

The skill contains execution guidance and a thin invocation script, not copies
of model weights or analysis logic. Version the source in `skills/video-analysis/`
and deploy it to the user's skill directory when installation is requested.

```text
skills/video-analysis/
  SKILL.md
  SKILL_en.md             # English reference; SKILL.md is the entrypoint
  scripts/analyze.py      # Invoke shared CLI; forward arguments and exit status
  references/result.md   # Result interpretation and coverage
  references/result_en.md

mj_video_intelligence/
  core.py
  openai.py
  runtime/               # New shared execution layer
    pipeline.py
    sources.py
    media.py
    contracts.py
    jobs.py
    cli.py
```

## Input and execution contract

The following is the proposed interface.

```bash
mj-video doctor --json
mj-video analyze --url 'https://www.youtube.com/shorts/VIDEO_ID' \
  --objective '등장하는 장소와 추천 이유를 정리해줘' --output ./analysis
mj-video analyze --file ./clip.mp4 \
  --objective '제품 사양과 가격을 추출해줘' --output ./analysis
mj-video status --job JOB_ID --json
```

- URL and file are mutually exclusive. Normalize file paths to absolute paths.
- The default semantic mode uses a local LLM. Missing model connectivity is a
  configuration error; do not silently fall back to rules.
- `--evidence-only` is a separate transcription/evidence-collection option.
- `--coverage selective|full-transcript` distinguishes selective search from
  full transcript processing.
- Full transcript processing analyzes chronological chunks and merges duplicates.
  It does not mean all screen information was analyzed. Record missing chunks
  and length limits in the result.
- Use a separate output directory per job; do not implicitly overwrite results.

The skill checks installation with `doctor` and submits a job. Long transcription
and inference run as a separate process returning a job ID, then continue through
`status`. If the conversation disconnects, inspect the same job without submitting
duplicates. Durable job/status support is a planned part of this design, not a
claim about the current CLI.

## Models and installation

- Separate the base Python core from optional `youtube` and `asr` dependencies.
- Use system ffmpeg/ffprobe executables.
- Default Whisper to CPU and allow model-name and cache-path configuration.
- Semantic analysis uses an OpenAI-compatible endpoint for user-installed open weights.
- Reuse `VIDEO_MODEL_BASE_URL` and `VIDEO_MODEL_NAME`.
- Check accuracy, license and hardware requirements when choosing a specific model.
- `doctor` should check tools, free disk space, model cache, endpoint connectivity
  and JSON responses.
- Download models during initial setup after disclosing size and destination.
  Do not unexpectedly install large dependencies or change servers during analysis.
- Local files can run offline when models are cached; YouTube requires network access.

## Source-specific paths

1. YouTube: collect metadata and captions, then analyze available captions.
2. No captions: preserve metadata and finish with `NEEDS_MEDIA`. Request an
   available original file. Do not infer video content from its thumbnail.
3. File: inspect duration, size and tracks → convert audio → ASR → transcript analysis.
4. No speech: finish with `NO_SPEECH` or `NEEDS_VISUAL_ANALYSIS`. A representative
   frame may be saved but must not be labeled completed OCR/vision analysis.
5. 429: distinguish rate limits from missing captions. Use cache and server retry
   guidance with bounded retries; persistent limits end as `SOURCE_RATE_LIMITED`.

Cache keys use video ID/caption language or file hash/transcription model.
Inference keys also include objective, schema and model version to avoid mixing requests.

## Result contract

Do not fix the domain to restaurants. The proposed default result contains:

```json
{
  "status": "completed",
  "source": {"type": "file", "title": "clip.mp4", "durationSeconds": 49},
  "execution": {"evidenceMode": "audio-asr", "analysisMode": "local-llm"},
  "coverage": {"requested": "full-transcript", "complete": true, "visualAnalyzed": false},
  "summary": "근거에 기반한 요약",
  "findings": [{
    "category": "place",
    "text": "장소 정보",
    "evidence": [{"type": "transcript", "startSeconds": 12, "endSeconds": 16, "text": "원문"}]
  }],
  "warnings": [],
  "artifacts": {"report": "report.md"}
}
```

Distinguish completed execution from extraction success. Use `completed`,
`partial`, `needs_input` and `failed`, with separate error codes and recovery
actions. Validate schema types, required fields, evidence-index references and
timestamp ranges. Explain that structural validation does not guarantee factual accuracy.

The skill reads JSON and presents a Korean report by default, or English on request,
with evidence links. Do not add unsupported facts or describe metadata-only results
as full video analysis. Treat instructions in descriptions/transcripts as data.

## Execution limits and errors

Limit file size, video duration, transcription time, model request time and total
job time. On cancellation/timeout, explicitly terminate execution and clean up
temporary files. Preserve results and user-selected caches; never alter originals.
Default local execution to a loopback model server. Sending files/transcripts to
an external server requires the user's explicit provider choice. Do not put API
keys or authentication cookies in results or logs.

## Implementation sequence and acceptance criteria

1. Extract the shared runtime while preserving caption/file-upload regression tests.
2. CLI, job storage and doctor: verify submission, retrieval, cancellation,
   failures and timeouts.
3. Local LLM: add a generic request schema, full-transcript chunks and evidence validation.
4. Skill package: write guidance/wrapper, validate structure and test actual invocation.
5. Shared demo: FastAPI invokes the same runtime and the frontend reflects the result contract.
6. Later vision work: add frames, OCR and local VLM, evaluated as separate evidence types.

Required cases: captioned URL, captionless URL, 429, valid speech file, silent file,
corrupt file, missing model, invalid model JSON, cancellation and timeout.
Verify ASR with real speech and semantic analysis with a real local LLM.
Report skill installation separately from feature implementation.
