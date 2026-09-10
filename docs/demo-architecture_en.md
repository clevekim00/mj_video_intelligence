# Video Intelligence Demo Architecture

[한국어](demo-architecture.md) | **English**

## Decision

The demo is a three-service application:

```text
React/Vite web
    -> Spring Boot host API
        -> FastAPI analysis service
            -> mj_video_intelligence
                -> demo model or OpenAI-compatible model gateway
```

Spring Boot is the host application and owns upload metadata, authorization,
analysis job state, persistence boundaries, and result validation. The Python
service is a replaceable execution adapter around `mj_video_intelligence`.
React never calls the Python service directly.

## Why a Python sidecar

`mj_video_intelligence` is a Python package. A small HTTP boundary avoids
embedding Python in the JVM, keeps Python/model dependencies isolated, and
allows the analysis workers to scale separately from the API. The boundary is
deliberately narrow and uses JSON that mirrors the package's evidence contract.

## Components

### Web (`demo/web`)

- Creates a demo analysis from a prepared evidence record.
- Polls job state until it reaches `SUCCEEDED` or `FAILED`.
- Renders extracted restaurant facts and clickable evidence timestamps.
- Uses `VITE_API_BASE_URL` when the API is not served from the same origin.

### Host API (`demo/api`)

- Exposes `POST /api/analyses` and `GET /api/analyses/{id}`.
- Assigns the job identifier and owns its lifecycle.
- Calls the Python service asynchronously.
- Applies host-side structural validation before accepting a result.
- Uses an in-memory job repository for the demo. A production host should use a
  database and durable queue.

### Analysis service (`demo/analysis-service`)

- Exposes `POST /analyses` and `GET /health`.
- Converts the HTTP DTO to the library's evidence mapping.
- Collects public YouTube metadata and manual/automatic captions with `yt-dlp`
  when a YouTube URL arrives without prepared transcript segments. Video media
  is not downloaded.
- Enforces `VideoBudget` and validates evidence timestamps in the final result.
- Defaults to a deterministic `DemoVideoAgentModel`, so the sample works
  offline.
- Uses `OpenAIVideoAgentModel` when `VIDEO_MODEL_BASE_URL` and
  `VIDEO_MODEL_NAME` are configured.

## Request flow

1. React posts evidence, objective, and result schema to Spring Boot.
2. Spring Boot returns `202 Accepted` with a job ID.
3. Its task executor posts the analysis payload to FastAPI.
4. FastAPI runs `AgenticVideoAnalyzer` over `IndexedVideoTools`.
5. The model searches the transcript and returns a schema-shaped result.
6. Python validates evidence ranges; Spring validates the response shape.
7. React polls and renders the completed result.

## API contract

`POST /api/analyses`

```json
{
  "objective": "맛집 이름, 추천 메뉴, 가격과 타임스탬프만 추출하세요.",
  "resultSchema": {"type":"object","required":["restaurants"]},
  "evidence": {
    "url": "https://example.com/video/1",
    "title": "강릉 맛집 여행",
    "durationSeconds": 90,
    "transcriptSegments": [
      {"startSeconds":10,"endSeconds":15,"text":"초당 카페의 옥수수 아이스크림은 5000원입니다"}
    ],
    "frameCandidates": []
  }
}
```

The response is initially `202`:

```json
{"id":"uuid","status":"QUEUED","result":null,"error":null}
```

`GET /api/analyses/{id}` returns the same envelope with status `QUEUED`,
`PROCESSING`, `SUCCEEDED`, or `FAILED`.

## Security and production boundaries

- The host must authorize every video and artifact reference.
- The Python service must not be internet-facing in production.
- Tool arguments, artifact references, and model output are untrusted input.
- Use object-store references rather than sending large frame bytes as JSON.
- Replace the in-memory repository with durable storage and a message queue.
- Add ASR and frame extraction before analysis; they are intentionally outside
  this library's current API.
- Keep model credentials only in the Python service environment.

## Local development

### Uploaded-media fallback

`POST /api/analyses/upload` accepts multipart `objective` and `file`. Spring
buffers the upload (100 MB maximum) before queuing the task and forwards it to
`POST /analyses/upload`. The Python worker uses a temporary directory, probes
duration with ffprobe, extracts a JPEG preview and mono 16 kHz audio with ffmpeg,
then transcribes speech with faster-whisper on CPU. Temporary media is deleted
after the job. Whisper weights are cached in the `asr-models` Docker volume;
the first speech job needs network access to download the selected model.

YouTube URLs with no available caption track return `metadata-only` with an
upload prompt. No YouTube audio/video is downloaded. Uploaded silent videos
return metadata and a preview, not OCR or visual recognition results. OCR and
Vision inference remain unimplemented; a preview must not be described as frame
analysis. Demo findings are sampled transcript excerpts, not exhaustive semantic
extraction. Configure a model gateway for objective-aware text analysis.

This local demo has no authentication or durable task queue and buffers uploads
in Java memory. Use only in a trusted local environment. Browser polling allows
up to 30 minutes for the first ASR run.

Each component can run independently; `docker-compose.yml` runs the complete
demo. See [the demo guide](../demo/README_en.md) for commands and environment variables.
