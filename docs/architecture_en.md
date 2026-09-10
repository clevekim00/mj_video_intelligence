# Reusable Video Intelligence Module

[한국어](architecture.md) | **English**

## Purpose

`mj_video_intelligence` is a reusable Python package that lets a model select
required transcript segments and permitted frames instead of receiving a whole
long video. The same bounded agent loop can serve Narmer, meetings, education
and media search.

The package does not own original-video downloads, platform login, persistent
storage or domain-specific result schemas. These remain the host application's
responsibility.

## Can it extract only the information I want?

Yes. The host describes the extraction objective with `objective` and the desired
structure with `result_schema`. The agent searches related transcript segments
and frame candidates instead of broadly summarizing the entire video.

Example objectives include:

- Restaurant names, locations, recommended dishes and prices
- Tourist attractions and visiting tips
- What a particular speaker said and when
- Product names, features and displayed prices
- Time ranges containing a particular event
- Signs, menus and text shown on screen

The processing flow is:

```text
Set objective and result_schema
→ Search relevant transcript segments
→ Fetch only the required time range
→ Select frame candidates only when visual confirmation is needed
→ Generate a schema-shaped result
→ Validate evidence and required fields with the host validator
```

This does not guarantee perfect retrieval of every requested fact. Quality
depends on transcript/frame coverage, the model and search tools. Visual
information absent from transcripts requires a host adapter supplying actual
frames and a vision-capable model. Use final results after validation.

## Directory structure

```text
mj_video_intelligence/
├── pyproject.toml
├── README.md
├── mj_video_intelligence/
│   ├── __init__.py        # stable public exports
│   ├── core.py            # budgets, protocols, tools, agent loop
│   └── openai.py          # OpenAI-compatible model adapter
└── tests/
    └── test_core.py       # Package tests without a host application
```

## Data flow

```text
Host application
  ├─ obtains permitted metadata/transcript/frame artifacts
  ├─ creates VideoTools implementation or IndexedVideoTools
  ├─ creates VideoAgentModel implementation
  └─ optionally injects a domain result validator
                  │
                  ▼
        AgenticVideoAnalyzer
          ├─ ask model for one action
          ├─ enforce iteration/tool budgets
          ├─ reject duplicate calls
          ├─ execute only registered tools
          └─ validate and return final result
```

## Evidence input

The basic evidence format accepted by `IndexedVideoTools` is:

```python
evidence = {
    "url": "https://example.com/video/1",
    "title": "Trip video",
    "description": "A food trip",
    "duration_seconds": 90,
    "transcript_segments": [
        {"start_seconds": 10, "end_seconds": 15, "text": "Try the corn ice cream"},
    ],
    "frame_candidates": [
        {"timestamp_seconds": 12, "artifact_ref": "frames/12.jpg", "text": "Cafe sign"},
    ],
}
```

The host determines the format and access control for `artifact_ref`.
The package does not open that path or download video from the network.

## Basic usage

```python
from mj_video_intelligence import (
    AgenticVideoAnalyzer,
    IndexedVideoTools,
    OpenAIVideoAgentModel,
    VideoBudget,
)

model = OpenAIVideoAgentModel(
    base_url="http://127.0.0.1:3211/v1",
    model="gemma4:latest",
    api_key="local-gateway-token",
)
budget = VideoBudget(max_iterations=6, max_tool_calls=10, max_frames=24)
analyzer = AgenticVideoAnalyzer(
    model=model,
    tools=IndexedVideoTools(evidence, budget),
    budget=budget,
    objective="Extract restaurant names, recommended menus, prices, and timestamps only.",
    result_schema={
        "type": "object",
        "required": ["restaurants"],
        "properties": {
            "restaurants": {"type": "array"},
        },
    },
)
result = analyzer.analyze(evidence)
```

The expected result follows the host-provided schema.

```json
{
  "restaurants": [
    {
      "name": "Chodang Cafe",
      "recommended_menu": "Corn ice cream",
      "price": null,
      "evidence": {
        "type": "transcript",
        "start_seconds": 10,
        "end_seconds": 15
      }
    }
  ]
}
```

At each step, the model must return one of these forms:

```json
{"action":"search_transcript","arguments":{"query":"restaurant","limit":5}}
```

```json
{"action":"finish","result":{"answer":"...","evidence":[]}}
```

`OpenAIVideoAgentModel` interprets both native `tool_calls` and JSON action responses.

## Domain validation

The package does not know the meaning of final results. Other projects inject a validator.

```python
def validate_result(result: dict, evidence: dict) -> None:
    if "answer" not in result:
        raise ValueError("answer is required")

analyzer = AgenticVideoAnalyzer(
    model,
    tools,
    result_validator=validate_result,
)
```

Narmer's `VideoAwareAnalyzer` attaches validation of places, claims and timestamped
evidence at this boundary. Ordinary pages without transcripts go to the existing analyzer.

## Custom tools

Implement the `VideoTools` protocol to use database search, object storage or
your own frame service.

```python
class ProjectVideoTools:
    def call(self, name: str, arguments: dict) -> dict:
        if name == "search_transcript":
            return transcript_store.search(**arguments)
        if name == "get_frames":
            return frame_service.select(**arguments)
        raise ValueError(f"unsupported tool: {name}")
```

Tool implementations must recheck permissions, video IDs, time ranges, FPS and
result sizes rather than trusting model arguments.

## Model adapters

Implement this protocol for another provider:

```python
class VideoAgentModel:
    def next_action(self, state: dict) -> dict:
        ...
```

The provider adapter owns authentication, timeout handling, error normalization
and response parsing. The core loop and host tool layer own execution permissions
and iteration limits.

## Security and policy boundary

- The package does not open URLs directly or automate platform login.
- Supply only artifacts whose access the host has authorized.
- Treat tool output as untrusted input and a potential prompt-injection source.
- Do not include sensitive data such as private notes, OAuth tokens or current location in state.
- `VideoBudget` is a resource/security boundary, not merely a convenience setting.
- Store model results only after the host's JSON Schema and evidence validation.

## Current limitations

- `IndexedVideoTools.get_frames` selects host-supplied frame candidates.
  Video decoding belongs to the host adapter.
- Default transcript search uses simple lexical matching. Other projects can
  implement an FTS/vector backend.
- Audio extraction/ASR is not part of the public core API.
- Model capability discovery belongs to the gateway. Do not request frame-content
  analysis from a model without `vision` capability.
- `result_schema` communicates the desired structure to the model, but the core
  does not validate JSON Schema itself. Call a JSON Schema validator from
  `result_validator` when strict validation is required.

## Versioning

Use public imports through `mj_video_intelligence.__init__`. Breaking protocol or
evidence/action format changes require a major version. New optional fields or
tools use minor versions. Host-specific schemas and migrations are outside this
package's versioning.
