import json
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, File, Form, UploadFile

from .models import AnalysisRequest, AnalysisResponse
from .service import analyze, analyze_prepared_evidence
from .media import MediaAnalysisError, collect_uploaded_evidence
from .youtube import YouTubeCollectionError

app = FastAPI(title="MJ Video Intelligence Analysis Service", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "UP"}


@app.post("/analyses", response_model=AnalysisResponse)
def create_analysis(request: AnalysisRequest) -> AnalysisResponse:
    try:
        result, mode = analyze(request)
    except YouTubeCollectionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return AnalysisResponse(result=result, mode=mode)


@app.post("/analyses/upload", response_model=AnalysisResponse)
def create_upload_analysis(
    objective: str = Form(...),
    result_schema: str = Form(..., alias="resultSchema"),
    file: UploadFile = File(...),
) -> AnalysisResponse:
    try:
        schema = json.loads(result_schema)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=400, detail="resultSchema must be valid JSON") from error
    try:
        with tempfile.TemporaryDirectory(prefix="mj-video-") as directory:
            workdir = Path(directory)
            media_path = workdir / "source.bin"
            with media_path.open("wb") as output:
                total = 0
                while chunk := file.file.read(1024 * 1024):
                    total += len(chunk)
                    if total > 100 * 1024 * 1024:
                        raise HTTPException(status_code=413, detail="업로드 파일은 100MB 이하여야 합니다.")
                    output.write(chunk)
            if media_path.stat().st_size > 100 * 1024 * 1024:
                raise MediaAnalysisError("업로드 파일은 100MB 이하여야 합니다.")
            evidence, source_mode = collect_uploaded_evidence(media_path, file.filename or "uploaded-video", workdir)
            request = AnalysisRequest(objective=objective, resultSchema=schema, evidence=evidence)
            result, mode = analyze_prepared_evidence(request, evidence, source_mode)
    except MediaAnalysisError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        file.file.close()
    return AnalysisResponse(result=result, mode=mode)
