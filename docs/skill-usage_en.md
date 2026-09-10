# Video analysis skill installation and usage

[한국어](skill-usage.md) | **English**

The skill source lives in [`skills/video-analysis`](../skills/video-analysis)
and can be installed separately from the demo. It calls the Python CLI directly;
Spring Boot, React and Docker are not required. Codex account terms and the cost
of running the local analysis model are separate.

## 1. Prepare Python

Run from the repository root.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[youtube,asr]'
```

File transcription also needs ffmpeg and ffprobe on PATH. On macOS, install them
with `brew install ffmpeg`. Existing captions or prepared JSON do not require
the optional `asr` dependencies or ffmpeg.

Whisper defaults to `tiny` on CPU/int8. The first ASR run downloads weights.
Set `WHISPER_MODEL` to a model name or prepared model directory. Once cached,
local file transcription can run offline.

## 2. Install the skill

Runtime installation and skill-folder installation are separate. The following
command stops if the destination already exists, preserving an existing skill.
After installation, check discovery in a new task with a refreshed skill list.
Use the Python environment above when executing it.

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
test ! -e "${CODEX_HOME:-$HOME/.codex}/skills/video-analysis" && \
  cp -R skills/video-analysis "${CODEX_HOME:-$HOME/.codex}/skills/video-analysis"
```

The repository contains the skill source only; it is not automatically installed
into your personal skill directory. `SKILL.md` is the Korean default entrypoint;
`SKILL_en.md` is its English reference, not a second installable skill.

## 3. Connect a local LLM

Specify the OpenAI-compatible endpoint and actual model ID of your installed
local model server. Replace the example model ID with one from your server.

```bash
export VIDEO_MODEL_BASE_URL=http://127.0.0.1:11434/v1
export VIDEO_MODEL_NAME=your-installed-model
mj-video doctor --check-model
```

The server must support `/chat/completions` and JSON object responses. The skill
does not install a model server or select weights automatically. Semantic analysis
fails without model configuration. Use `--evidence-only` for transcription alone.

## 4. Invocation examples

```text
$video-analysis Extract places and reasons to visit with evidence timestamps from this YouTube URL: URL
$video-analysis Analyze the full transcript of /absolute/path/clip.mp4 and summarize product specifications in English.
$video-analysis Transcribe /absolute/path/interview.wav without semantic analysis.
```

The skill explains results in Korean by default and English when requested.
Original evidence quotations and timestamps are preserved. This does not imply
that the CLI has an output-language switch.

The same functionality is available in a terminal without Codex.

```bash
mj-video analyze --file ./clip.mp4 --objective '제품 사양과 가격' \
  --coverage full-transcript --output ./analysis-product
mj-video analyze --url 'https://www.youtube.com/shorts/VIDEO_ID' \
  --objective '전사 수집' --evidence-only --output ./analysis-captions
```

`--evidence prepared.json` accepts the core library's evidence format
(`duration_seconds`, `transcript_segments`, etc.). Each run uses a new output
directory containing `result.json` and `report.md`. Always inspect the JSON status.
Exit code is 0 for success or additional input required, and 1 for failure.

## Limitations and troubleshooting

- Captionless YouTube: returns metadata and `needs_input`; provide a media file.
- Files: maximum 100 MB. ASR transcribes speech, not screen text or objects.
- Full analysis: processes collected transcript chunks, not all video imagery.
- Model JSON/evidence errors: fail the job, without substituting rule-based output.
- 429: do not loop; retry later or use a local file.
- Timeout: 900 seconds by default, configurable with `--timeout`. Timeout/cancel
  writes a failed result and terminates the worker. Forced termination may leave
  an OS temporary directory.
- Durable background job storage/resumption and OCR/VLM are future design items.
- An external model endpoint receives transcripts. The example uses loopback.

See the [design](video-analysis-skill-design_en.md) for the broader proposal.
This guide describes the implemented scope, not completion of every future feature.
