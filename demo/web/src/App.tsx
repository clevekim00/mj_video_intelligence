import { FormEvent, useState } from "react";
import { AnalysisJob, createAnalysis, createUploadAnalysis, sampleRequest, waitForAnalysis } from "./api";
import "./styles.css";

const initialObjective = "맛집 이름, 추천 메뉴, 가격과 타임스탬프만 추출하세요.";
const initialVideoUrl = sampleRequest.evidence.url;

function formatTime(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

function formatDuration(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = String(Math.floor(seconds % 60)).padStart(2, "0");
  return `${minutes}:${remainingSeconds}`;
}

function timestampUrl(url: string, seconds: number) {
  return `${url}${url.includes("?") ? "&" : "?"}t=${Math.floor(seconds)}s`;
}

export default function App() {
  const [objective, setObjective] = useState(initialObjective);
  const [videoUrl, setVideoUrl] = useState(initialVideoUrl);
  const [sourceType, setSourceType] = useState<"url" | "upload">("url");
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const created = sourceType === "upload" && videoFile
        ? await createUploadAnalysis(objective, videoFile)
        : await createAnalysis(objective, videoUrl);
      setJob(created);
      setJob(await waitForAnalysis(created.id));
    } catch (error) {
      setJob({ id: "local-error", status: "FAILED", result: null, mode: null, error: error instanceof Error ? error.message : "알 수 없는 오류" });
    } finally {
      setBusy(false);
    }
  }

  const restaurants = job?.result?.restaurants ?? [];
  const findings = job?.result?.findings ?? [];
  const resultCount = restaurants.length + findings.length;
  const video = job?.result?.video;
  const remoteVideo = video?.url.startsWith("http") ?? false;
  const needsUpload = job?.mode?.includes("metadata-only") || (job?.status === "FAILED" && /자막|caption/i.test(job.error ?? ""));

  return (
    <main>
      <header className="hero">
        <span className="eyebrow">MJ VIDEO INTELLIGENCE · LAB 01</span>
        <h1>긴 영상에서<br /><em>필요한 장면만</em> 찾습니다.</h1>
        <p>전체 영상을 모델에 넘기지 않고, 자막과 프레임 후보를 근거로 목표에 맞는 정보만 선택합니다.</p>
      </header>

      <section className="workspace">
        <article className="source-card">
          {video?.thumbnailUrl && remoteVideo ? (
            <a className="video-thumbnail" href={video.url} target="_blank" rel="noreferrer" aria-label={`${video.title} YouTube에서 열기`}>
              <img src={video.thumbnailUrl} alt={`${video.title} 썸네일`} />
              <span className="play-icon" aria-hidden="true">▶</span>
              <small>{formatDuration(video.durationSeconds)}</small>
            </a>
          ) : video?.thumbnailUrl ? (
            <div className="video-thumbnail" aria-label={`${video.title} 대표 프레임`}>
              <img src={video.thumbnailUrl} alt={`${video.title} 대표 프레임`} />
              <small>{formatDuration(video.durationSeconds)}</small>
            </div>
          ) : (
            <div className="mock-video" aria-label="샘플 영상 미리보기">
              <span>DEMO</span>
              <strong>LOCAL<br />FOOD<br />TOUR</strong>
              <small>00:10 / 01:30</small>
            </div>
          )}
          <div className="source-meta">
            <span className="tag">{video ? (remoteVideo ? "YOUTUBE EVIDENCE" : "UPLOADED EVIDENCE") : "SAMPLE EVIDENCE"}</span>
            <h2>{video?.title ?? sampleRequest.evidence.title}</h2>
            <p>{video?.description ?? sampleRequest.evidence.description}</p>
          </div>
        </article>

        <form className="analysis-panel" onSubmit={submit}>
          <div className="panel-heading">
            <span>분석 설정</span>
            <span className="step">01 / 02</span>
          </div>
          <label className="field-label" htmlFor="video-url">영상 주소</label>
          <div className="source-tabs" role="tablist" aria-label="영상 입력 방식">
            <button type="button" className={sourceType === "url" ? "active" : ""} onClick={() => setSourceType("url")}>YouTube URL</button>
            <button type="button" className={sourceType === "upload" ? "active" : ""} onClick={() => setSourceType("upload")}>영상 파일 업로드</button>
          </div>
          {sourceType === "url" ? (
            <input
              id="video-url"
              type="url"
              value={videoUrl}
              onChange={event => setVideoUrl(event.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              required
            />
          ) : (
            <input
              id="video-file"
              type="file"
              accept="video/*,audio/*"
              onChange={event => setVideoFile(event.target.files?.[0] ?? null)}
              required
            />
          )}
          <p className="field-help">URL은 공개 자막을 우선 사용합니다. 직접 업로드한 파일은 ffmpeg와 로컬 Whisper로 음성을 전사합니다. 파일 제한은 100MB입니다.</p>
          <label htmlFor="objective">영상에서 무엇을 찾을까요?</label>
          <textarea id="objective" value={objective} onChange={event => setObjective(event.target.value)} rows={4} />
          <div className="limits">
            <span>최대 반복 6회</span><span>도구 호출 10회</span><span>프레임 24장</span>
          </div>
          <button disabled={busy || !objective.trim() || (sourceType === "url" ? !videoUrl.trim() : !videoFile)}>{busy ? "분석 중…" : "선택적 분석 시작 →"}</button>
          {job && <p className={`status ${job.status.toLowerCase()}`}>상태: {job.status}{job.mode ? ` · ${job.mode}` : ""}</p>}
          {needsUpload && <button type="button" className="fallback-button" onClick={() => setSourceType("upload")}>자막 없음 — 파일 업로드로 전환 →</button>}
        </form>
      </section>

      {(job?.status === "SUCCEEDED" || job?.status === "FAILED") && (
        <section className="results" aria-live="polite">
          <div className="results-heading"><span>검증된 결과</span><b>{resultCount.toString().padStart(2, "0")}</b></div>
          {job?.error && <p className="error">{job.error}</p>}
          {job?.result?.notice && <p>{job.result.notice}</p>}
          {job.status === "SUCCEEDED" && resultCount === 0 && (
            <div className="empty-result">
              <strong>요청 조건과 일치하는 결과가 없습니다.</strong>
              <p>영상 분석은 정상 완료됐지만 수집된 자막에서 요청을 뒷받침할 근거를 찾지 못했습니다. 더 구체적인 분석 요청을 입력하거나 자막이 충분한 영상을 사용해 보세요.</p>
            </div>
          )}
          {findings.map((item, index) => (
            <article className="result-row finding-row" key={`${item.startSeconds}-${index}`}>
              <span className="number">{String(index + 1).padStart(2, "0")}</span>
              <div><h3>자막 하이라이트</h3><p>{item.text}</p></div>
              <span className="finding-type">{item.type}</span>
              {(video?.url ?? videoUrl).startsWith("http") ? (
                <a className="timestamp" href={timestampUrl(video?.url ?? videoUrl, item.startSeconds)} target="_blank" rel="noreferrer">▶ {formatTime(item.startSeconds)}</a>
              ) : <span className="timestamp">▶ {formatTime(item.startSeconds)}</span>}
            </article>
          ))}
          {restaurants.map((item, index) => (
            <article className="result-row" key={`${item.name}-${index}`}>
              <span className="number">{String(index + 1).padStart(2, "0")}</span>
              <div><h3>{item.name}</h3><p>{item.recommendedMenu ?? "메뉴 확인 필요"}</p></div>
              <strong>{item.price ? `${item.price.toLocaleString()}원` : "가격 미상"}</strong>
              <button type="button" className="timestamp" title={item.evidence.text}>▶ {formatTime(item.evidence.startSeconds)}</button>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
