# mj_video_intelligence

**한국어** | [English](README_en.md)

로컬 또는 호스팅 환경의 OpenAI 호환 모델을 위한 정책 제한형 선택적 영상 분석 패키지입니다.

영상 전체를 모델에 전달하지 않고, 허용된 자막과 프레임 자료에서 필요한 부분만 모델이 탐색하도록 합니다. 호스트 애플리케이션은 분석 자료, 추출 목표, 결과 스키마와 도메인 검증기를 제공합니다. 핵심 패키지는 영상을 직접 다운로드하거나 미디어 플랫폼에 로그인하지 않으며, 애플리케이션 데이터를 저장하지 않습니다.

## `mj_llm_wapper`와의 독립성

`mj_llm_wapper`는 선택적으로 사용할 수 있는 실행 게이트웨이이며 Python 패키지 의존성이 아닙니다. 핵심 모듈은 `VideoAgentModel`과 `VideoTools` 프로토콜에만 의존합니다. `OpenAIVideoAgentModel`은 `mj_llm_wapper`, Ollama 또는 `/chat/completions`를 지원하는 다른 OpenAI 호환 엔드포인트에 연결할 수 있습니다.

## 설치

```bash
python3 -m pip install .
```

개발 중에는 편집 가능 모드로 설치할 수 있습니다.

```bash
python3 -m pip install -e .
```

## 사용법

```python
from mj_video_intelligence import (
    AgenticVideoAnalyzer,
    IndexedVideoTools,
    OpenAIVideoAgentModel,
)

evidence = {
    "url": "https://example.com/video/1",
    "title": "맛집 여행",
    "duration_seconds": 90,
    "transcript_segments": [
        {
            "start_seconds": 10,
            "end_seconds": 15,
            "text": "옥수수 아이스크림을 드셔 보세요",
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
    objective="맛집 이름, 메뉴, 가격과 타임스탬프만 추출하세요.",
    result_schema={"type": "object", "required": ["restaurants"]},
)
result = analyzer.analyze(evidence)
```

## 공개 API

- `VideoBudget`: 자원 사용량과 보안 한계 설정
- `IndexedVideoTools`: 준비된 자막·프레임 자료에 대한 제한된 접근
- `VideoAgentModel`: 모델 제공자 연결 프로토콜
- `OpenAIVideoAgentModel`: 선택적 OpenAI 호환 HTTP 어댑터
- `VideoTools`: 사용자 정의 도구 백엔드 프로토콜
- `AgenticVideoAnalyzer`: 횟수와 자원이 제한된 모델·도구 실행 루프

## 책임 범위

영상 출처의 접근 권한 확인, 영상 획득, 음성 인식, 프레임 디코딩, 영속 저장, 도메인별 스키마, 근거 검증과 사용자 소유권 관리는 호스트 애플리케이션의 책임입니다. 이 패키지는 호스트가 제공한 자료를 대상으로 제한된 선택·분석 루프만 담당합니다.

상세한 구조, 계약, 확장 지점과 제한사항은 [`docs/architecture.md`](docs/architecture.md)에서 확인할 수 있습니다.

## 테스트

```bash
python3 -m unittest discover -s tests -v
```

## 현재 상태

버전 `0.1.0`은 알파 API입니다. 첫 안정 버전 이후 프로토콜이나 근거 데이터 형식의 호환성을 깨는 변경에는 주 버전 번호를 올립니다.

## 라이선스

MIT
