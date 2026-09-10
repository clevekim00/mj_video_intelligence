import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class AnalysisApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health(self) -> None:
        self.assertEqual(self.client.get("/health").json(), {"status": "UP"})

    def test_upload_preserves_asr_evidence_and_preview(self) -> None:
        evidence = {
            "url": "upload://clip.mp4", "title": "clip.mp4", "duration_seconds": 10,
            "thumbnail_url": "data:image/jpeg;base64,AA==",
            "transcript_segments": [{"start_seconds": 1, "end_seconds": 3, "text": "제품 소개입니다"}],
            "frame_candidates": [],
        }
        with patch("app.main.collect_uploaded_evidence", return_value=(evidence, "local-asr")):
            response = self.client.post("/analyses/upload", data={
                "objective": "모든 정보", "resultSchema": '{"required":["findings"]}',
            }, files={"file": ("clip.mp4", b"fixture", "video/mp4")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "local-asr+demo")
        self.assertEqual(response.json()["result"]["findings"][0]["text"], "제품 소개입니다")
        self.assertEqual(response.json()["result"]["video"]["thumbnailUrl"], evidence["thumbnail_url"])

    def test_demo_analysis_returns_grounded_restaurant(self) -> None:
        response = self.client.post("/analyses", json={
            "objective": "맛집과 가격을 추출하세요.",
            "resultSchema": {"type": "object", "required": ["restaurants"]},
            "evidence": {
                "url": "https://example.com/video/1",
                "title": "강릉 맛집 여행",
                "durationSeconds": 90,
                "transcriptSegments": [{
                    "startSeconds": 10,
                    "endSeconds": 15,
                    "text": "초당 카페의 옥수수 아이스크림은 5,000원입니다",
                }],
                "frameCandidates": [],
            },
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["mode"], "demo")
        self.assertEqual(body["result"]["restaurants"][0]["price"], 5000)
        self.assertEqual(body["result"]["restaurants"][0]["evidence"]["startSeconds"], 10)
        self.assertEqual(body["result"]["video"]["title"], "강릉 맛집 여행")
        self.assertEqual(body["result"]["video"]["durationSeconds"], 90)

    def test_general_analysis_returns_transcript_findings(self) -> None:
        response = self.client.post("/analyses", json={
            "objective": "추출 가능한 모든 것을 추출하세요.",
            "resultSchema": {"type": "object", "required": ["findings"]},
            "evidence": {
                "url": "https://example.com/video/1",
                "title": "제품 소개",
                "durationSeconds": 30,
                "transcriptSegments": [{
                    "startSeconds": 2,
                    "endSeconds": 6,
                    "text": "새로운 카메라는 무게가 200그램입니다",
                }],
                "frameCandidates": [],
            },
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["findings"][0]["text"], "새로운 카메라는 무게가 200그램입니다")


if __name__ == "__main__":
    unittest.main()
