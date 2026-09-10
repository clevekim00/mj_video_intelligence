# MJ Video Intelligence 데모

**한국어** | [English](README_en.md)

React 클라이언트, Spring Boot 작업 API, FastAPI 분석 어댑터로 라이브러리와 호스트의
책임 경계를 보여주는 데모입니다. 기본 설정은 외부 모델 없이 동작합니다.

## 전체 실행

```bash
cd demo
docker compose up --build
```

[데모](http://localhost:5173)를 엽니다. 상태 확인 주소는
[Spring API](http://localhost:8080/actuator/health)와
[분석 서비스](http://localhost:8000/health)입니다.

## 서비스별 로컬 실행

분석 서비스:

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

## 모델 게이트웨이 연결

웹은 최대 100 MB의 영상·음성 파일을 받습니다. Docker에는 ffmpeg와 faster-whisper가
포함되며, `WHISPER_MODEL`의 기본값은 `tiny`입니다. 빠르지만 정확도에는 한계가 있습니다.
첫 음성 업로드 시 모델 가중치를 영속 Docker 볼륨에 내려받습니다.
자막 없는 YouTube URL은 메타데이터와 업로드 안내를 반환합니다. 무음 파일은 미리보기와
메타데이터만 반환하며 OCR·비전 분석은 아직 구현되지 않았습니다.
데모 모드는 규칙 기반 결과 또는 일부 자막 발췌만 반환합니다.

아래 주소와 모델명 두 변수를 모두 지정하지 않으면 결정론적 데모 모델을 사용합니다.

```bash
export VIDEO_MODEL_BASE_URL=http://127.0.0.1:3211/v1
export VIDEO_MODEL_NAME=gemma4:latest
export VIDEO_MODEL_API_KEY=local-gateway-token
```

엔드포인트는 OpenAI 호환 `/chat/completions` 응답을 제공해야 합니다.

## 테스트

```bash
python3 -m unittest discover -s tests -v
cd demo/analysis-service && python3 -m unittest discover -s tests -v
cd ../api && ./gradlew test
cd ../web && npm test && npm run build
```

기본 샘플은 준비된 자막을 사용합니다. 실제 파일에는 호스트가 소유하는 ASR·프레임
추출 처리가 필요하며, 데모는 업로드 경로에서 음성 전사와 대표 프레임 추출을 제공합니다.

공개 YouTube URL은 `yt-dlp`로 메타데이터와 사용 가능한 수동·자동 자막을 수집하며
영상 파일은 다운로드하지 않습니다. 비공개·연령 제한·지역 제한 영상은 인증이 필요하거나
수집에 실패할 수 있습니다. 자막 없는 영상의 음성 분석에는 별도 원본 파일이 필요합니다.
