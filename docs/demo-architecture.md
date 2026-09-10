# 영상 분석 데모 아키텍처

**한국어** | [English](demo-architecture_en.md)

## 설계 결정

데모는 세 개의 서비스로 구성된다.

```text
React/Vite 웹
    → Spring Boot 호스트 API
        → FastAPI 분석 서비스
            → mj_video_intelligence
                → 데모 모델 또는 OpenAI 호환 모델 게이트웨이
```

Spring Boot는 호스트 애플리케이션으로 업로드 메타데이터, 권한 확인,
분석 작업 상태, 영속 저장 경계와 결과 검증을 담당한다. Python 서비스는
`mj_video_intelligence`를 감싸는 교체 가능한 실행 어댑터다.
React는 Python 서비스를 직접 호출하지 않는다.

## Python 사이드카를 사용하는 이유

`mj_video_intelligence`는 Python 패키지다. 작은 HTTP 경계를 두면 JVM에
Python을 내장하지 않아도 되고, Python·모델 의존성을 격리하며 분석 작업자를
API와 별도로 확장할 수 있다. 인터페이스는 패키지 근거 계약에 대응하는 JSON으로
의도적으로 좁게 유지한다.

## 구성 요소

### 웹 (`demo/web`)

- 준비된 근거 레코드로 데모 분석을 생성한다.
- 작업 상태가 `SUCCEEDED` 또는 `FAILED`가 될 때까지 조회한다.
- 추출한 맛집 정보와 클릭 가능한 근거 타임스탬프를 표시한다.
- API가 같은 출처에서 제공되지 않으면 `VITE_API_BASE_URL`을 사용한다.

### 호스트 API (`demo/api`)

- `POST /api/analyses`, `GET /api/analyses/{id}`를 제공한다.
- 작업 식별자를 발급하고 생명주기를 관리한다.
- Python 서비스를 비동기로 호출한다.
- 결과를 수락하기 전에 호스트 측 구조 검증을 수행한다.
- 데모는 메모리 작업 저장소를 사용한다. 운영 호스트에는 데이터베이스와
  영속 큐가 필요하다.

### 분석 서비스 (`demo/analysis-service`)

- `POST /analyses`, `GET /health`를 제공한다.
- HTTP DTO를 라이브러리의 근거 매핑으로 변환한다.
- 준비된 자막 없이 YouTube URL이 들어오면 `yt-dlp`로 공개 메타데이터와
  수동·자동 자막을 수집한다. 영상 미디어는 다운로드하지 않는다.
- `VideoBudget`을 적용하고 최종 결과의 근거 타임스탬프를 검증한다.
- 기본값은 결정론적 `DemoVideoAgentModel`이므로 샘플은 오프라인에서 동작한다.
- `VIDEO_MODEL_BASE_URL`, `VIDEO_MODEL_NAME`을 설정하면
  `OpenAIVideoAgentModel`을 사용한다.

## 요청 흐름

1. React가 근거, 분석 목표와 결과 스키마를 Spring Boot로 전송한다.
2. Spring Boot가 작업 ID와 `202 Accepted`를 반환한다.
3. 작업 실행기가 분석 데이터를 FastAPI로 전송한다.
4. FastAPI가 `IndexedVideoTools`를 대상으로 `AgenticVideoAnalyzer`를 실행한다.
5. 모델이 자막을 검색하고 스키마에 맞는 결과를 반환한다.
6. Python은 근거 범위를, Spring은 응답 구조를 검증한다.
7. React가 상태를 조회하고 완료 결과를 표시한다.

## API 계약

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

초기 응답은 `202`다.

```json
{"id":"uuid","status":"QUEUED","result":null,"error":null}
```

`GET /api/analyses/{id}`는 같은 응답 구조에 `QUEUED`, `PROCESSING`,
`SUCCEEDED` 또는 `FAILED` 상태를 반환한다.

## 보안과 운영 환경 경계

- 호스트는 모든 영상과 자료 참조에 대한 접근 권한을 확인해야 한다.
- 운영 환경에서 Python 서비스를 인터넷에 직접 노출하지 않는다.
- 도구 인수, 자료 참조와 모델 출력은 신뢰하지 않는 입력이다.
- 큰 프레임 데이터를 JSON으로 보내지 않고 객체 저장소 참조를 사용한다.
- 메모리 저장소를 영속 저장소와 메시지 큐로 교체한다.
- 분석 전 ASR와 프레임 추출을 호스트 어댑터에서 수행한다.
  이는 현재 핵심 라이브러리 API 밖의 책임이다.
- 모델 인증 정보는 Python 서비스 환경에만 둔다.

## 로컬 개발

### 업로드 미디어 대체 경로

`POST /api/analyses/upload`는 multipart `objective`와 `file`을 받는다.
Spring은 최대 100 MB 업로드를 메모리에 보관한 뒤 작업을 큐에 넣고
`POST /analyses/upload`로 전달한다. Python 작업자는 임시 디렉터리에서
ffprobe로 길이를 확인하고 ffmpeg로 JPEG 미리보기와 모노 16 kHz 오디오를
추출한 뒤 CPU의 faster-whisper로 전사한다. 작업 후 임시 미디어를 삭제한다.
Whisper 가중치는 Docker의 `asr-models` 볼륨에 캐시되며 첫 음성 작업에는
선택한 모델을 다운로드할 네트워크가 필요하다.

자막이 없는 YouTube URL은 업로드 안내와 `metadata-only`를 반환한다.
YouTube 영상·음성을 다운로드하지 않는다. 무음 업로드는 메타데이터와
미리보기를 반환하며 OCR·시각 인식 결과가 아니다. OCR·비전 추론은 미구현이므로
미리보기를 프레임 분석으로 설명하지 않는다. 데모 결과는 샘플링된 자막 발췌이며
전체 의미 추출이 아니다. 목표에 따른 텍스트 분석에는 모델 게이트웨이를 설정한다.

이 로컬 데모는 인증이나 영속 작업 큐가 없으며 Java 메모리에 업로드를 보관한다.
신뢰할 수 있는 로컬 환경에서만 사용한다. 첫 ASR 실행을 위해 브라우저는
최대 30분까지 상태를 조회한다.

각 구성 요소는 독립 실행할 수 있고 `docker-compose.yml`로 전체 데모를
실행할 수 있다. 명령과 환경변수는 [데모 실행 안내](../demo/README.md)를 참고한다.
