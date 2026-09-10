import { afterEach, describe, expect, it, vi } from "vitest";
import { createAnalysis, createUploadAnalysis, waitForAnalysis } from "./api";

describe("analysis API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("posts a user objective", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "job-1", status: "QUEUED" }), { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);
    await createAnalysis("가격을 찾아줘", "https://video.example/custom");
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.objective).toBe("가격을 찾아줘");
    expect(body.evidence.url).toBe("https://video.example/custom");
    expect(body.evidence.transcriptSegments).toEqual([]);
    expect(body.resultSchema.required).toEqual(["findings"]);
  });

  it("keeps the restaurant schema for restaurant objectives", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "job-2", status: "QUEUED" }), { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);
    await createAnalysis("맛집과 가격을 찾아줘", "https://video.example/food");
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.resultSchema.required).toEqual(["restaurants"]);
  });

  it("polls until completion", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "job-1", status: "PROCESSING" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "job-1", status: "SUCCEEDED", result: { restaurants: [] } }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const job = await waitForAnalysis("job-1", async () => undefined);
    expect(job.status).toBe("SUCCEEDED");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("uploads an authorized video file as multipart data", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "job-upload", status: "QUEUED" }), { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["video"], "clip.mp4", { type: "video/mp4" });
    await createUploadAnalysis("모두 추출", file);
    const body = fetchMock.mock.calls[0][1].body as FormData;
    expect(body.get("objective")).toBe("모두 추출");
    expect((body.get("file") as File).name).toBe("clip.mp4");
  });
});
