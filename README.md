# mj_video_intelligence

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

## Public API

- `VideoBudget`: resource and security limits
- `IndexedVideoTools`: bounded access to prepared transcript and frame artifacts
- `VideoAgentModel`: model-provider protocol
- `OpenAIVideoAgentModel`: optional OpenAI-compatible HTTP adapter
- `VideoTools`: custom tool-backend protocol
- `AgenticVideoAnalyzer`: bounded model/tool loop

## Responsibility boundary

The host application owns source authorization, video acquisition, ASR, frame decoding, persistence, domain-specific schemas, evidence validation, and user ownership. This package owns only the bounded selection and analysis loop over artifacts supplied by the host.

Detailed architecture, contracts, extension points, and limitations are documented in [`docs/architecture.md`](docs/architecture.md).

## Test

```bash
python3 -m unittest discover -s tests -v
```

## Status

Version `0.1.0` is an alpha API. Breaking protocol or evidence-format changes will use a major version bump after the first stable release.

## License

MIT
