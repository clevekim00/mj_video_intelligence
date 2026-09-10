# MJ Video Intelligence Demo

[한국어](README.md) | **English**

The demo makes the library's host boundary visible through a React client,
Spring Boot job API, and FastAPI analysis adapter. It runs without an external
model by default.

## Run everything

```bash
cd demo
docker compose up --build
```

Open <http://localhost:5173>. The API health endpoints are available at
<http://localhost:8080/actuator/health> and <http://localhost:8000/health>.

## Run services locally

Analysis service:

```bash
python3 -m pip install -e . -e './demo/analysis-service[test]'
cd demo/analysis-service
uvicorn app.main:app --reload
```

Spring Boot API:

```bash
cd demo/api
./gradlew bootRun
```

React:

```bash
cd demo/web
npm install
npm run dev
```

## Connect a model gateway

The web UI also accepts video/audio uploads up to 100 MB. Docker includes ffmpeg
and faster-whisper; `WHISPER_MODEL` defaults to `tiny` (fast, lower accuracy).
The first upload containing speech downloads model weights into a persistent
Docker volume. No-caption YouTube URLs return metadata with an upload prompt.
Silent uploads return a preview and metadata; OCR/vision analysis is not yet
implemented. Demo mode only returns rule-based or sampled transcript results.

The deterministic demo model is used unless both variables below are set:

```bash
export VIDEO_MODEL_BASE_URL=http://127.0.0.1:3211/v1
export VIDEO_MODEL_NAME=gemma4:latest
export VIDEO_MODEL_API_KEY=local-gateway-token
```

The endpoint must implement OpenAI-compatible `/chat/completions` responses.

## Tests

```bash
python3 -m unittest discover -s tests -v
cd demo/analysis-service && python3 -m unittest discover -s tests -v
cd ../api && ./gradlew test
cd ../web && npm test && npm run build
```

The sample uses prepared transcript evidence. Real files require a host-owned
ASR/frame extraction pipeline; the demo upload path provides speech transcription
and a representative frame.

Public YouTube URLs are an exception: the analysis service uses `yt-dlp` to
collect metadata and available manual or automatic captions without downloading
the video. Private, age-restricted or region-restricted videos may require
authentication or fail collection. Speech analysis of captionless videos needs
a separately provided original media file.
