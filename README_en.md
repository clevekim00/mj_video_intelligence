# mj_video_intelligence

[한국어](README.md) | **English**

Policy-bounded, selective video analysis for local or hosted OpenAI-compatible models.

The package lets a model search permitted transcript and frame artifacts instead of sending an entire video to the model. A host application supplies the artifacts, extraction objective, result schema, and domain validator. The core package does not download videos, authenticate to media platforms, or persist application data.

## Independence from `mj_llm_wapper`

`mj_llm_wapper` is an optional runtime gateway, not a Python package dependency. The core depends only on the `VideoAgentModel` and `VideoTools` protocols. `OpenAIVideoAgentModel` can connect to `mj_llm_wapper`, Ollama, or another compatible `/chat/completions` endpoint.

## Install

```bash
python3 -m pip install .
```

For editable development:

```bash
python3 -m pip install -e .
```

## Usage

```python
from mj_video_intelligence import (
    AgenticVideoAnalyzer,
    IndexedVideoTools,
    OpenAIVideoAgentModel,
)

evidence = {
    "url": "https://example.com/video/1",
    "title": "Food trip",
    "duration_seconds": 90,
    "transcript_segments": [
        {
            "start_seconds": 10,
            "end_seconds": 15,
            "text": "Try the corn ice cream",
        }
    ],
    "frame_candidates": [],
}

model = OpenAIVideoAgentModel(
    base_url="http://127.0.0.1:3210/v1",
    model="gemma4:latest",
)
analyzer = AgenticVideoAnalyzer(
    model=model,
    tools=IndexedVideoTools(evidence),
    objective="Extract restaurant names, menus, prices, and timestamps only.",
    result_schema={"type": "object", "required": ["restaurants"]},
)
result = analyzer.analyze(evidence)
```

## Codex skill and local CLI

Use `$video-analysis` in the separate [`skills/video-analysis`](skills/video-analysis)
folder for public YouTube captions, local video/audio Whisper transcription and
information extraction with a configured local LLM. It runs through the Python
CLI without Spring Boot or demo servers.

```bash
python3 -m pip install -e '.[youtube,asr]'
mj-video doctor
mj-video analyze --file ./clip.mp4 --objective '자막 전사' \
  --evidence-only --output ./analysis-output
```

Semantic analysis requires a local model connection. Captionless URLs return
metadata only; OCR/vision is not implemented. See the
[installation and usage guide](docs/skill-usage_en.md). The skill is included in the
repository but is not automatically installed into your personal environment.

## Public API

- `VideoBudget`: resource and security limits
- `IndexedVideoTools`: bounded access to prepared transcript and frame artifacts
- `VideoAgentModel`: model-provider protocol
- `OpenAIVideoAgentModel`: optional OpenAI-compatible HTTP adapter
- `VideoTools`: custom tool-backend protocol
- `AgenticVideoAnalyzer`: bounded model/tool loop

## Responsibility boundary

The host application owns source authorization, video acquisition, ASR, frame decoding, persistence, domain-specific schemas, evidence validation, and user ownership. This package owns only the bounded selection and analysis loop over artifacts supplied by the host.

Detailed architecture, contracts, extension points, and limitations are documented in [`docs/architecture_en.md`](docs/architecture_en.md).

## Test

```bash
python3 -m unittest discover -s tests -v
```

## React + Spring Boot demo

`demo/` contains a runnable React UI, Spring Boot host API and FastAPI analysis
adapter. The default demo needs no external model; configure environment variables
to connect an OpenAI-compatible model gateway.

```bash
cd demo
docker compose up --build
```

See the [demo guide](demo/README_en.md) for execution instructions and the
[demo architecture](docs/demo-architecture_en.md) for boundaries and API contracts.

## Documentation

Korean is the default documentation language. Every document has a language link
at the top. Default filenames contain Korean and `*_en.md` files contain English.
`README_ko.md` is a Korean compatibility path with the same content as the default
README. Update both languages together when changing documentation. Commands,
API identifiers and original evidence need not be translated.

- [Core architecture](docs/architecture_en.md)
- [Visual getting-started guide (HTML)](docs/usage-eli5_en.html)
- [Demo guide](demo/README_en.md)
- [Demo architecture](docs/demo-architecture_en.md)
- [Skill installation and usage](docs/skill-usage_en.md)
- [Skill implementation design](docs/video-analysis-skill-design_en.md)
- [Skill execution instructions](skills/video-analysis/SKILL_en.md)
- [Result interpretation](skills/video-analysis/references/result_en.md)

## Status

Version `0.1.0` is an alpha API. Breaking protocol or evidence-format changes will use a major version bump after the first stable release.

## License

MIT
