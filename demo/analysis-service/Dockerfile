FROM python:3.13-slim
WORKDIR /workspace
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY mj_video_intelligence ./mj_video_intelligence
COPY demo/analysis-service ./demo/analysis-service
RUN pip install --no-cache-dir . ./demo/analysis-service
WORKDIR /workspace/demo/analysis-service
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
