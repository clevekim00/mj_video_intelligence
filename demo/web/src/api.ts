export type JobStatus = "QUEUED" | "PROCESSING" | "SUCCEEDED" | "FAILED";

export interface Restaurant {
  name: string;
  recommendedMenu?: string | null;
  price?: number | null;
  evidence: { type: string; startSeconds: number; endSeconds: number; text?: string };
}

export interface VideoMetadata {
  url: string;
  title: string;
  description?: string | null;
  thumbnailUrl?: string | null;
  durationSeconds: number;
}

export interface Finding {
  type: string;
  text: string;
  startSeconds: number;
  endSeconds: number;
}

export interface AnalysisJob {
  id: string;
  status: JobStatus;
  result: { restaurants?: Restaurant[]; findings?: Finding[]; video?: VideoMetadata; notice?: string } | null;
  mode: string | null;
  error: string | null;
}

export const sampleRequest = {
  objective: "맛집 이름, 추천 메뉴, 가격과 타임스탬프만 추출하세요.",
  resultSchema: {
    type: "object",
    required: ["restaurants"],
    properties: { restaurants: { type: "array" } },
  },
  evidence: {
    url: "https://example.com/videos/gangneung-food-tour",
    title: "강릉 로컬 맛집 여행",
    description: "현지 카페와 시장을 방문하는 90초 여행 영상",
    durationSeconds: 90,
    transcriptSegments: [
      { startSeconds: 10, endSeconds: 15, text: "초당 카페의 옥수수 아이스크림은 5,000원입니다" },
      { startSeconds: 42, endSeconds: 48, text: "중앙시장에서는 닭강정을 추천합니다" },
    ],
    frameCandidates: [],
  },
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`API 요청 실패 (${response.status})`);
  return response.json() as Promise<T>;
}

export async function createAnalysis(objective: string, videoUrl: string): Promise<AnalysisJob> {
  const usesPreparedSample = videoUrl === sampleRequest.evidence.url;
  const restaurantRequest = /맛집|식당|restaurant|food/i.test(objective);
  const resultSchema = restaurantRequest ? sampleRequest.resultSchema : {
    type: "object",
    required: ["findings"],
    properties: { findings: { type: "array" } },
  };
  return json(await fetch(`${API_BASE}/api/analyses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...sampleRequest,
      objective,
      resultSchema,
      evidence: {
        ...sampleRequest.evidence,
        url: videoUrl,
        transcriptSegments: usesPreparedSample ? sampleRequest.evidence.transcriptSegments : [],
      },
    }),
  }));
}

export async function createUploadAnalysis(objective: string, file: File): Promise<AnalysisJob> {
  const body = new FormData();
  body.append("objective", objective);
  body.append("file", file);
  return json(await fetch(`${API_BASE}/api/analyses/upload`, {
    method: "POST",
    body,
  }));
}

export async function getAnalysis(id: string): Promise<AnalysisJob> {
  return json(await fetch(`${API_BASE}/api/analyses/${id}`));
}

export async function waitForAnalysis(
  id: string,
  delay: (milliseconds: number) => Promise<void> = (milliseconds) => new Promise(resolve => setTimeout(resolve, milliseconds)),
): Promise<AnalysisJob> {
  for (let attempt = 0; attempt < 1800; attempt += 1) {
    const job = await getAnalysis(id);
    if (job.status === "SUCCEEDED" || job.status === "FAILED") return job;
    await delay(1000);
  }
  throw new Error("분석 대기 시간이 초과되었습니다.");
}
