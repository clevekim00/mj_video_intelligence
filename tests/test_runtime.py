import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from types import SimpleNamespace

from mj_video_intelligence.runtime.cli import analyze_evidence, validate


class RuntimeTest(unittest.TestCase):
    def test_model_http_path_and_full_transcript_coverage(self):
        proof = {"startSeconds": 1, "endSeconds": 3, "text": "hello"}
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                action = {"action": "finish", "result": {"findings": [{"text": "Greeting", "evidence": proof}]}}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"choices": [{"message": {"content": json.dumps(action)}}]}).encode())
            def log_message(self, *args):
                pass
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = analyze_evidence({"duration_seconds": 10, "transcript_segments": [
                {"start_seconds": 1, "end_seconds": 3, "text": "hello"}]}, SimpleNamespace(
                    evidence_only=False, coverage="full-transcript", objective="Find greetings",
                    base_url=f"http://127.0.0.1:{server.server_port}/v1", model="test-model"))
            self.assertEqual(result["findings"][0]["text"], "Greeting")
            self.assertTrue(result["coverage"]["complete"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_cli_transcription_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "evidence.json"
            source.write_text(json.dumps({"url": "local", "title": "Fixture", "duration_seconds": 10,
                "transcript_segments": [{"start_seconds": 1, "end_seconds": 3, "text": "hello"}]}))
            output = root / "result"
            command = [sys.executable, "-m", "mj_video_intelligence.runtime.cli", "analyze",
                       "--evidence", str(source), "--objective", "transcribe", "--evidence-only", "--output", str(output)]
            completed = subprocess.run(command, capture_output=True, timeout=15)
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            result = json.loads((output / "result.json").read_text())
            self.assertEqual(result["transcript"][0]["text"], "hello")
            self.assertEqual(result["execution"]["analysisMode"], "evidence-only")
            self.assertNotEqual(subprocess.run(command, capture_output=True, timeout=15).returncode, 0)

    def test_rejects_fabricated_proof(self):
        evidence = {"duration_seconds": 10, "transcript_segments": [
            {"start_seconds": 1, "end_seconds": 3, "text": "hello"}]}
        result = {"findings": [{"text": "Claim", "evidence": {
            "startSeconds": 1, "endSeconds": 3, "text": "invented"}}]}
        with self.assertRaises(ValueError):
            validate(result, evidence)
