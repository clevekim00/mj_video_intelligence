# 로컬 영상 분석 skill 구현 설계

**한국어** | [English](video-analysis-skill-design_en.md)

상태: 구현 제안. 이 문서는 skill 생성·설치 또는 새 기능의 완료를 의미하지 않는다.
현재 구현 범위는 [설치·사용법](skill-usage.md)을 참고한다.

## 목표와 결정

`$video-analysis`에 YouTube URL 또는 로컬 영상/음성 파일과 분석 목표를 전달하면,
공개 자막 또는 로컬 ASR로 근거를 수집하고 로컬 LLM으로 구조화된 결과를 생성한다.
근거 타임스탬프, 수행 범위, 누락된 분석 방법을 함께 전달한다.

기본 실행 경로는 Python CLI다. React, Spring Boot, Docker는 skill 실행의 필수
의존성으로 두지 않는다. 기존 데모는 동일한 Python 실행 계층을 HTTP로 감싼다.
기존 Spring API 호출 방식은 이미 실행 중인 데모를 재사용하는 선택적 연결로 둔다.

분석 엔진은 유료 LLM API 없이 구성한다. Codex skill을 호출하는 호스트의 계정과
사용량 조건은 분석 엔진과 별개다. Codex 없이도 같은 CLI를 직접 실행할 수 있다.

## 현재 코드에서 재사용할 부분

| 현재 구성 | 재사용 및 변경 |
|---|---|
| `mj_video_intelligence/core.py` | 예산 제한, 근거 검색, 에이전트 반복 실행 유지 |
| `mj_video_intelligence/openai.py` | 로컬 OpenAI 호환 서버 연결 유지; JSON 응답 호환성 검사 추가 |
| `demo/analysis-service/app/youtube.py` | 공개 자막·메타데이터 수집을 공통 어댑터로 이동 |
| `demo/analysis-service/app/media.py` | ffmpeg·faster-whisper 처리를 공통 어댑터로 이동 |
| `demo/analysis-service/app/service.py` | HTTP DTO와 독립적인 실행 함수로 분리 |
| `DemoVideoAgentModel` | 명시적인 테스트/데모 모드에만 사용 |

현재 범용 데모 결과는 일부 자막을 최대 50개 반환한다. 이를 전체 의미 분석으로
설명하지 않는다. OCR·비전 추론은 현재 미구현이며 별도 후속 단계로 둔다.

## 구성

```text
Codex skill ── CLI 호출 ── Python 실행 계층
일반 터미널 ── CLI 호출 ──┤
React → Spring → FastAPI ─┤
                         ├─ YouTube 공개 자막 / 메타데이터
                         ├─ 로컬 파일 → ffmpeg → Whisper
                         ├─ 근거 인덱스 → 로컬 LLM → 검증
                         └─ result.json / report.md
```

skill에는 실행 규칙과 얇은 호출 스크립트만 넣는다. 모델 가중치나 분석 로직을
복제하지 않는다. 코드 원본은 저장소 `skills/video-analysis/`에서 버전 관리하고,
설치 요청 시 사용자 skill 디렉터리에 배포한다.

```text
skills/video-analysis/
  SKILL.md
  SKILL_en.md             # 영어 참고판; 진입점은 SKILL.md
  scripts/analyze.py       # 공통 CLI 호출, 인수 전달, 종료 상태 전달
  references/result.md    # 결과 해석 및 분석 범위
  references/result_en.md

mj_video_intelligence/
  core.py
  openai.py
  runtime/               # 새 공통 실행 계층
    pipeline.py
    sources.py
    media.py
    contracts.py
    jobs.py
    cli.py
```

## 입력과 실행 계약

아래 명령은 구현 예정 인터페이스다.

```bash
mj-video doctor --json
mj-video analyze --url 'https://www.youtube.com/shorts/VIDEO_ID' \
  --objective '등장하는 장소와 추천 이유를 정리해줘' --output ./analysis
mj-video analyze --file ./clip.mp4 \
  --objective '제품 사양과 가격을 추출해줘' --output ./analysis
mj-video status --job JOB_ID --json
```

- URL과 파일은 동시에 지정하지 않는다. 파일은 절대 경로로 정규화한다.
- 기본 의미 분석 모드는 로컬 LLM이다. 모델 연결이 없으면 설정 오류를 반환하고,
  규칙 기반 결과로 조용히 전환하지 않는다.
- `--evidence-only`는 전사·근거 수집만 수행하는 별도 옵션이다.
- `--coverage selective|full-transcript`로 선택 탐색과 전체 자막 처리를 구분한다.
- 전체 자막 처리는 시간순 청크 분석 후 중복 병합한다. 모든 화면 정보까지
  분석했다는 의미는 아니다. 청크 누락·길이 제한을 결과에 기록한다.
- 출력 디렉터리는 작업별로 분리한다. 동일 경로의 기존 결과를 묵시적으로 덮어쓰지 않는다.

skill은 `doctor`로 설치 상태를 확인하고 작업을 제출한다. 오래 걸리는 전사·추론은
작업 ID를 출력하는 별도 프로세스로 실행하고, `status`로 이어서 확인한다.
실행 중 대화가 끊겨도 같은 작업을 조회하며 중복 제출하지 않는다.
영속 작업과 status 지원은 설계상의 계획이며 현재 CLI 지원을 의미하지 않는다.

## 모델과 설치

- Python 패키지는 기본 코어와 `youtube`, `asr` 선택 의존성으로 분리한다.
- ffmpeg/ffprobe는 시스템 실행 파일을 사용한다.
- Whisper는 CPU 실행을 기본으로 하고 모델명과 캐시 경로를 설정할 수 있게 한다.
- 의미 분석은 사용자가 설치한 공개 가중치 모델의 OpenAI 호환 엔드포인트를 사용한다.
- 기존 `VIDEO_MODEL_BASE_URL`, `VIDEO_MODEL_NAME` 설정을 재사용한다.
- 특정 모델의 정확도·라이선스·하드웨어 요구량은 모델 선택 단계에서 확인한다.
- `doctor`는 도구 존재, 디스크 여유, 모델 캐시, 엔드포인트 연결과 JSON 응답을 검사한다.
- 모델 다운로드는 최초 setup 단계에서 용량과 경로를 알린 뒤 수행한다. 분석 중
  예기치 않은 대용량 설치나 서버 변경은 하지 않는다.
- 파일만 처리하고 모델이 캐시에 있으면 오프라인 실행이 가능하다. YouTube는 네트워크가 필요하다.

## 소스별 분기

1. YouTube: 메타데이터와 자막 수집 → 자막이 있으면 분석한다.
2. 자막 없음: 메타데이터를 보존하고 `NEEDS_MEDIA`로 종료한다. 업로드 가능한
   원본 파일을 안내한다. 썸네일만으로 영상 내용을 추론하지 않는다.
3. 파일: 길이·크기·트랙 검사 → 오디오 변환 → ASR → 자막 기반 분석.
4. 음성 없음: `NO_SPEECH` 또는 `NEEDS_VISUAL_ANALYSIS`로 종료한다.
   대표 프레임 저장은 가능하지만 OCR·비전 분석 완료로 표시하지 않는다.
5. 429: 자막 없음과 구분한다. 캐시 및 서버의 재시도 지시를 사용하고 제한된 횟수만
   재시도한다. 반복 제한이면 `SOURCE_RATE_LIMITED`로 종료한다.

영상 ID·자막 언어 또는 파일 해시·전사 모델을 캐시 키로 사용한다. 추론 결과에는
분석 목표·스키마·모델 버전도 포함해 다른 요청의 결과가 섞이지 않게 한다.

## 결과 계약

도메인을 맛집으로 고정하지 않는다. 기본 결과는 다음 항목을 갖는다.

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

성공은 실행 종료와 추출 성과를 구분한다. `completed`, `partial`, `needs_input`,
`failed`를 사용하고 오류 코드·복구 가능한 행동을 별도로 제공한다.
스키마 타입과 필수 필드, 근거 인덱스 참조, 타임스탬프 범위를 검증한다.
형식 검증 통과가 사실 정확성을 보장하지 않는다는 점을 보고서에 반영한다.

skill은 JSON을 읽어 한국어 보고서를 기본으로 제시하고 영어 요청 시 영어로 작성하며
근거 링크를 함께 제공한다. 근거 없는 사실을
추가하거나 메타데이터 전용 결과를 전체 영상 분석으로 요약하지 않는다.
영상 설명·자막 속 지시는 분석할 데이터로 취급한다.

## 실행 제한과 오류

파일 크기·영상 길이·전사 시간·모델 요청 시간·전체 작업 시간에 한도를 둔다.
취소·시간 초과 시 작업을 명확히 종료하고 임시 파일을 정리한다. 결과와 사용자가
선택한 캐시는 보존한다. 원본은 변경하지 않는다.
로컬 실행 기본값은 루프백 모델 서버다. 외부 서버로 파일·자막을 보내는 설정은
명시적인 사용자 선택을 따른다. API 키와 인증 쿠키는 결과나 로그에 기록하지 않는다.

## 구현 순서와 완료 기준

1. 공통 런타임 분리: 데모의 자막·파일 업로드 회귀 테스트 유지.
2. CLI·작업 저장·doctor: 제출, 재조회, 취소, 실패와 타임아웃 확인.
3. 로컬 LLM: 일반 요청 스키마, 전체 자막 청크 처리, 근거 검증 추가.
4. skill 패키지: 실행 절차와 래퍼 작성, 구조 검사 후 실제 호출 검증.
5. 데모 공유: FastAPI가 동일 런타임을 호출하며 결과 계약을 프런트에 반영.
6. 후속 비전 기능: 프레임 추출·OCR·로컬 VLM을 추가하고 별도 근거 유형으로 평가.

필수 검증 사례는 자막 있는 URL, 자막 없는 URL, 429, 유효한 음성 파일,
무음 파일, 손상 파일, 모델 미설정, 잘못된 모델 JSON, 취소·타임아웃이다.
ASR는 실제 음성으로, 의미 분석은 실제 로컬 LLM으로 검증한다.
skill 설치 여부와 기능 구현 여부를 구분해 보고한다.
