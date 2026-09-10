# Video analysis skill 설치와 사용

skill 소스는 [`skills/video-analysis`](../skills/video-analysis)에 있으며 데모와
별도로 설치할 수 있습니다. Python CLI를 직접 호출하므로 Spring Boot·React·Docker가
필요하지 않습니다. Codex 이용 조건과 로컬 분석 모델 실행 비용은 별개입니다.

## 1. Python 환경 준비

저장소 루트에서 실행합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[youtube,asr]'
```

파일 음성 전사에는 ffmpeg와 ffprobe도 PATH에 있어야 합니다. macOS에서는
`brew install ffmpeg`로 설치할 수 있습니다. 기존 자막 또는 준비된 JSON만
사용한다면 `asr` 선택 의존성과 ffmpeg는 필요하지 않습니다.

Whisper는 기본 `tiny`, CPU/int8 설정입니다. 첫 ASR 실행은 모델 가중치를
다운로드합니다. `WHISPER_MODEL`로 모델명 또는 준비된 모델 디렉터리를 선택할 수
있습니다. 캐시가 준비되면 로컬 파일 전사는 오프라인으로도 가능합니다.

## 2. skill 설치

런타임 설치와 skill 폴더 설치는 별개입니다. 아래 명령은 설치 폴더가 이미 있으면
중단해 기존 skill을 덮어쓰지 않습니다. 설치 후 skill 목록이 갱신되는 새 작업에서
확인하세요. 실행 시 위 Python 환경을 사용해야 합니다.

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
test ! -e "${CODEX_HOME:-$HOME/.codex}/skills/video-analysis" && \
  cp -R skills/video-analysis "${CODEX_HOME:-$HOME/.codex}/skills/video-analysis"
```

이 저장소에는 skill 원본만 추가되어 있으며 개인 skill 디렉터리에 자동 설치하지 않습니다.

## 3. 로컬 LLM 연결

설치한 로컬 모델 서버의 OpenAI 호환 엔드포인트와 실제 모델 ID를 지정합니다.
아래 모델명은 예시 값이므로 자신의 서버에 맞게 바꿔야 합니다.

```bash
export VIDEO_MODEL_BASE_URL=http://127.0.0.1:11434/v1
export VIDEO_MODEL_NAME=your-installed-model
mj-video doctor --check-model
```

서버는 `/chat/completions`와 JSON 객체 응답을 지원해야 합니다. 이 skill이
모델 서버를 자동 설치하거나 가중치를 선택하지는 않습니다. 모델 설정이 없으면
의미 분석은 실패합니다. 전사만 필요하면 `--evidence-only`를 사용하세요.

## 4. 호출 예시

```text
$video-analysis 이 YouTube URL에서 장소와 추천 이유를 근거 시간과 함께 추출해줘: URL
$video-analysis /절대경로/clip.mp4의 전체 자막을 분석해 제품 사양을 정리해줘
$video-analysis /절대경로/interview.wav를 의미 분석 없이 전사해줘
```

Codex 없이 터미널에서도 동일 기능을 실행할 수 있습니다.

```bash
mj-video analyze --file ./clip.mp4 --objective '제품 사양과 가격' \
  --coverage full-transcript --output ./analysis-product
mj-video analyze --url 'https://www.youtube.com/shorts/VIDEO_ID' \
  --objective '전사 수집' --evidence-only --output ./analysis-captions
```

`--evidence prepared.json`은 핵심 라이브러리 형식(`duration_seconds`,
`transcript_segments` 등)의 자료를 입력받습니다. 매 실행마다 새 출력 디렉터리를
사용하며 `result.json`, `report.md`가 생성됩니다. JSON의 상태를 반드시 확인하세요.
종료 코드는 성공/추가입력 필요 시 0, 실패 시 1입니다.

## 제한과 문제 해결

- 자막 없는 YouTube: 메타데이터와 `needs_input` 반환. 파일 업로드가 필요합니다.
- 파일: 최대 100 MB. ASR는 음성을 전사하며 화면 글자·사물을 추출하지 않습니다.
- 전체 분석: 수집된 자막을 청크별로 분석합니다. 전체 영상 화면 분석은 아닙니다.
- 모델 JSON/근거 오류: 작업 실패로 반환합니다. 규칙 기반 결과로 대체하지 않습니다.
- 429: 반복 호출하지 말고 잠시 뒤 재시도하거나 로컬 파일을 사용합니다.
- 시간 제한: 기본 900초, `--timeout`으로 조절합니다. 시간 초과/취소는 실패 결과를
  남기고 작업 프로세스를 종료합니다. 강제 종료 시 OS 임시 디렉터리가 남을 수 있습니다.
- 백그라운드 영속 작업 저장·재개 및 OCR/VLM은 설계상의 후속 기능입니다.
- 외부 모델 서버를 지정하면 자막이 해당 서버로 전송됩니다. 기본 예시는 루프백입니다.

설계 전체는 [설계서](video-analysis-skill-design.md)를 참고하세요. 위 내용은
현재 구현 범위이며 설계서의 모든 후속 기능이 구현됐다는 뜻은 아닙니다.
