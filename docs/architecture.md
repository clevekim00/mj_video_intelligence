# Reusable Video Intelligence Module

## Purpose

`mj_video_intelligence`는 긴 영상을 모델에 통째로 전달하지 않고, 모델이 필요한 자막 구간과 허용된 프레임만 선택하도록 만드는 재사용 가능 Python 패키지다. Narmer뿐 아니라 회의, 교육, 미디어 검색 등 다른 프로젝트에서도 같은 bounded agent loop를 사용할 수 있다.

패키지는 영상 원본 다운로드, 플랫폼 로그인, 영속 저장과 도메인별 결과 schema를 소유하지 않는다. 이 책임은 패키지를 사용하는 host application에 남는다.

## Can it extract only the information I want?

가능하다. Host application이 `objective`로 추출 목표를 설명하고 `result_schema`로 원하는 결과 구조를 지정하면, agent는 전체 영상을 포괄적으로 요약하는 대신 그 목표와 관련된 자막 구간과 프레임 후보만 탐색한다.

예를 들어 다음과 같은 목표를 지정할 수 있다.

- 맛집 이름, 위치, 추천 메뉴와 가격
- 관광지 이름과 방문 팁
- 영상에서 특정 인물이 말한 내용과 시점
- 제품명, 기능과 화면에 표시된 가격
- 특정 사건이 발생한 시간 구간
- 간판, 메뉴판 또는 화면에 표시된 문구

처리 흐름은 다음과 같다.

```text
objective와 result_schema 지정
→ 자막에서 관련 구간 검색
→ 필요한 시간 범위만 조회
→ 시각적 확인이 필요할 때만 프레임 후보 선택
→ schema 형태로 결과 생성
→ host validator로 근거와 필수 필드 검증
```

이는 “요청한 정보만 반드시 완벽하게 찾는다”는 보장은 아니다. 결과 품질은 자막·프레임 artifact의 범위, 모델 성능과 검색 도구에 영향을 받는다. 자막에 없는 시각 정보는 실제 프레임을 준비한 host adapter와 vision-capable 모델이 필요하며, 최종 결과는 validator를 통과한 뒤 사용해야 한다.

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
    └── test_core.py       # Host application 없이 실행되는 package tests
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

`IndexedVideoTools`가 이해하는 기본 evidence 형식은 다음과 같다.

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

`artifact_ref`의 형식과 접근 제어는 host가 결정한다. 패키지는 해당 경로를 열거나 네트워크에서 영상을 내려받지 않는다.

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

예상 결과는 host가 지정한 schema를 따른다.

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

모델은 매 단계에 다음 형태 중 하나를 반환해야 한다.

```json
{"action":"search_transcript","arguments":{"query":"restaurant","limit":5}}
```

```json
{"action":"finish","result":{"answer":"...","evidence":[]}}
```

`OpenAIVideoAgentModel`은 native `tool_calls` 응답과 JSON action 응답을 모두 해석한다.

## Domain validation

패키지는 최종 결과의 의미를 알지 않는다. 다른 프로젝트는 validator를 주입한다.

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

Narmer의 `VideoAwareAnalyzer`는 이 지점에 장소·주장·timestamp 근거 검증을 연결한다. 자막이 없는 일반 페이지는 기존 analyzer로 전달한다.

## Custom tools

다른 프로젝트에서 DB 검색, object storage 또는 자체 frame service를 사용하려면 `VideoTools` protocol을 구현한다.

```python
class ProjectVideoTools:
    def call(self, name: str, arguments: dict) -> dict:
        if name == "search_transcript":
            return transcript_store.search(**arguments)
        if name == "get_frames":
            return frame_service.select(**arguments)
        raise ValueError(f"unsupported tool: {name}")
```

도구 구현은 모델이 전달한 인자를 그대로 신뢰하지 말고 권한, video ID, 시간 범위, FPS, 결과 크기를 다시 검사해야 한다.

## Model adapters

다른 provider를 사용하려면 다음 protocol만 구현한다.

```python
class VideoAgentModel:
    def next_action(self, state: dict) -> dict:
        ...
```

provider adapter는 인증, timeout, 오류 정규화와 응답 parsing을 책임진다. tool 실행 권한과 반복 제한은 core loop 및 host tool layer가 책임진다.

## Security and policy boundary

- 패키지는 URL을 직접 열거나 플랫폼 로그인을 자동화하지 않는다.
- host가 접근 권한을 확인한 artifact만 입력한다.
- tool output은 신뢰할 수 없는 입력이며 prompt injection으로 취급한다.
- private note, OAuth token, 현재 위치 같은 민감정보를 state에 포함하지 않는다.
- `VideoBudget`은 편의 설정이 아니라 resource/security boundary다.
- 모델 결과는 host의 JSON Schema와 evidence validator를 통과한 뒤 저장한다.

## Current limitations

- `IndexedVideoTools.get_frames`는 host가 미리 제공한 frame candidate를 선택한다. 영상 decoding은 host adapter 책임이다.
- 기본 transcript 검색은 단순 lexical matching이다. 다른 프로젝트는 FTS/vector backend를 구현하는 것이 좋다.
- audio extraction/ASR은 public API에 아직 포함하지 않았다.
- 모델 capability discovery는 model gateway에서 수행하고, `vision`이 없는 모델에는 frame content 분석을 요청하지 않아야 한다.
- `result_schema`는 모델에 목표 구조를 전달하지만 core가 직접 JSON Schema를 검증하지는 않는다. 엄격한 검증이 필요하면 `result_validator`에서 JSON Schema validator를 호출한다.

## Versioning

공개 import는 `mj_video_intelligence.__init__`를 통해 사용한다. protocol이나 evidence/action 형식을 깨뜨리는 변경은 major version으로 올린다. 새로운 optional field나 tool은 minor version으로 추가한다. host-specific schema와 migration은 이 패키지 버전에 포함하지 않는다.
