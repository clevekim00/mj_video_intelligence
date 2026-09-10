import json
import unittest

from app.youtube import _caption_track, _json3_segments, is_youtube_url


class YouTubeAdapterTest(unittest.TestCase):
    def test_only_accepts_youtube_hosts(self) -> None:
        self.assertTrue(is_youtube_url("https://www.youtube.com/watch?v=abc"))
        self.assertTrue(is_youtube_url("https://youtu.be/abc"))
        self.assertFalse(is_youtube_url("https://youtube.com.example.org/watch?v=abc"))

    def test_prefers_manual_korean_json_captions(self) -> None:
        track = _caption_track({
            "subtitles": {"ko": [{"ext": "json3", "url": "https://captions/manual"}]},
            "automatic_captions": {"ko": [{"ext": "json3", "url": "https://captions/auto"}]},
        }, ("ko", "en"))
        self.assertEqual(track["url"], "https://captions/manual")

    def test_converts_json3_events_to_library_segments(self) -> None:
        payload = json.dumps({"events": [{
            "tStartMs": 1500,
            "dDurationMs": 2500,
            "segs": [{"utf8": "안녕"}, {"utf8": "하세요"}],
        }]}).encode()
        self.assertEqual(_json3_segments(payload), [{
            "start_seconds": 1.5,
            "end_seconds": 4.0,
            "text": "안녕하세요",
        }])


if __name__ == "__main__":
    unittest.main()
