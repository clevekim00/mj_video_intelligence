"""Local CLI. Heavy adapters are imported only for their selected source."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request

from mj_video_intelligence import AgenticVideoAnalyzer, IndexedVideoTools, OpenAIVideoAgentModel


SCHEMA = {"type": "object", "required": ["findings"], "properties": {
    "findings": {"type": "array", "items": {"type": "object", "required": ["text", "evidence"],
        "properties": {"text": {"type": "string"}, "evidence": {"type": "object",
            "required": ["startSeconds", "endSeconds", "text"], "properties": {
                "startSeconds": {"type": "number"}, "endSeconds": {"type": "number"},
                "text": {"type": "string"}}}}}}}}


def validate(result, evidence):
    if not isinstance(result.get("findings"), list):
        raise ValueError("Model result must contain a findings array")
    for finding in result["findings"]:
        if not isinstance(finding, dict) or not isinstance(finding.get("text"), str):
            raise ValueError("Finding text must be a string")
        proof = finding.get("evidence", {})
        start, end = proof.get("startSeconds"), proof.get("endSeconds")
        if (type(start) not in (int, float) or type(end) not in (int, float)
                or not 0 <= start < end <= evidence["duration_seconds"]):
            raise ValueError("Invalid evidence timestamps")
        if not any(start == row["start_seconds"] and end == row["end_seconds"]
                   and proof.get("text") == row["text"] for row in evidence["transcript_segments"]):
            raise ValueError("Evidence must quote one original transcript segment exactly")


def analyze_evidence(evidence, args):
    rows = evidence.get("transcript_segments", [])
    result = {"status": "completed", "source": {key: evidence.get(key) for key in
              ("url", "title", "description", "duration_seconds", "thumbnail_url")},
              "execution": {"analysisMode": "evidence-only" if args.evidence_only else "local-llm"},
              "coverage": {"requested": args.coverage, "visualAnalyzed": False},
              "findings": [], "warnings": []}
    if not rows:
        result.update(status="needs_input", code="NEEDS_MEDIA")
        result["warnings"].append("No transcript available. Provide a local file with speech; OCR/vision is not implemented.")
        result["coverage"]["complete"] = False
        return result
    if args.evidence_only:
        result["transcript"] = rows
        result["coverage"]["complete"] = True
        result["warnings"].append("Transcript collection only; no semantic analysis was performed.")
        return result
    if not args.model or not args.base_url:
        raise ValueError("Set VIDEO_MODEL_BASE_URL and VIDEO_MODEL_NAME, or explicitly use --evidence-only")
    model = OpenAIVideoAgentModel(args.base_url, args.model,
                                 os.getenv("VIDEO_MODEL_API_KEY", "local"), timeout=60)
    # Whole transcript mode splits by character count without changing source timestamps.
    chunks, chunk, size = [], [], 0
    for row in rows:
        if chunk and size + len(row["text"]) > 12000:
            chunks.append(chunk)
            chunk, size = [], 0
        chunk.append(row)
        size += len(row["text"])
    if chunk:
        chunks.append(chunk)
    if args.coverage == "selective":
        chunks = [rows]
    result["coverage"]["chunks"] = len(chunks)
    for chunk in chunks:
        source = {**evidence, "transcript_segments": chunk}
        goal = args.objective + " Return findings with exact quoted transcript evidence and original timestamps."
        if args.coverage == "full-transcript":
            goal += " Inspect all of these transcript segments: " + json.dumps(chunk, ensure_ascii=False)
        analyzer = AgenticVideoAnalyzer(model, IndexedVideoTools(source), objective=goal,
                                        result_schema=SCHEMA, result_validator=validate)
        result["findings"].extend(analyzer.analyze(source)["findings"])
    unique = {json.dumps(item, sort_keys=True, ensure_ascii=False): item for item in result["findings"]}
    result["findings"] = list(unique.values())
    result["coverage"]["complete"] = args.coverage == "full-transcript"
    result["execution"]["model"] = args.model
    result["warnings"].append("Evidence matching validates provenance, not semantic correctness. No visual analysis.")
    return result


def worker(args):
    with tempfile.TemporaryDirectory(prefix="mj-video-") as directory:
        if args.url:
            from .youtube import collect_youtube_evidence
            evidence = collect_youtube_evidence(args.url)
            mode = "youtube-caption"
        elif args.file:
            from .media import collect_uploaded_evidence
            path = Path(args.file).resolve(strict=True)
            if not path.is_file() or path.stat().st_size > 100 * 1024 * 1024:
                raise ValueError("Local media must be a file of at most 100 MB")
            evidence, mode = collect_uploaded_evidence(path, path.name, Path(directory))
        else:
            evidence = json.loads(Path(args.evidence).read_text())
            mode = "prepared-transcript"
        result = analyze_evidence(evidence, args)
        result["execution"]["evidenceMode"] = mode if evidence.get("transcript_segments") else "metadata-only"
        return result


def save_result(output, result):
    (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    lines = ["# Video analysis", "", f"Status: {result['status']}", ""]
    for warning in result.get("warnings", []):
        lines.extend([warning, ""])
    if result.get("error"):
        lines.append(result["error"])
    for finding in result.get("findings", []):
        proof = finding["evidence"]
        lines.extend([f"- {proof['startSeconds']}–{proof['endSeconds']}s: {finding['text']}",
                      f"  Evidence: {proof['text']}"])
    if "transcript" in result:
        lines.extend(f"- {row['start_seconds']}–{row['end_seconds']}s: {row['text']}" for row in result["transcript"])
    (output / "report.md").write_text("\n".join(lines) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local video evidence collection and model analysis")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--check-model", action="store_true")
    run = commands.add_parser("analyze")
    source = run.add_mutually_exclusive_group(required=True)
    source.add_argument("--url")
    source.add_argument("--file")
    source.add_argument("--evidence", help="Prepared library-format evidence JSON")
    run.add_argument("--objective", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--evidence-only", action="store_true")
    run.add_argument("--coverage", choices=["selective", "full-transcript"], default="selective")
    run.add_argument("--base-url", default=os.getenv("VIDEO_MODEL_BASE_URL"))
    run.add_argument("--model", default=os.getenv("VIDEO_MODEL_NAME"))
    run.add_argument("--timeout", type=int, default=900)
    run.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.command == "doctor":
        checks = {"python": sys.version.split()[0], "ffmpeg": shutil.which("ffmpeg"),
                  "ffprobe": shutil.which("ffprobe"), "youtube": importlib.util.find_spec("yt_dlp") is not None,
                  "asr": importlib.util.find_spec("faster_whisper") is not None,
                  "modelConfigured": bool(os.getenv("VIDEO_MODEL_BASE_URL") and os.getenv("VIDEO_MODEL_NAME"))}
        if args.check_model:
            try:
                model = OpenAIVideoAgentModel(os.environ["VIDEO_MODEL_BASE_URL"], os.environ["VIDEO_MODEL_NAME"],
                                             os.getenv("VIDEO_MODEL_API_KEY", "local"), timeout=15)
                checks["modelResponse"] = model.next_action({"objective": "Return finish with result {}"})["action"]
            except Exception as error:
                checks["modelError"] = type(error).__name__
        print(json.dumps(checks, ensure_ascii=False, indent=2))
        return 0
    output = Path(args.output).resolve()
    if args.worker:
        try:
            result = worker(args)
        except Exception as error:
            result = {"status": "failed", "error": f"{type(error).__name__}: analysis failed; check dependencies, source and model connection"}
        save_result(output, result)
        return 1 if result["status"] == "failed" else 0
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-m", "mj_video_intelligence.runtime.cli", *(argv if argv is not None else sys.argv[1:]), "--worker"]
    process = subprocess.Popen(command, start_new_session=True)
    try:
        code = process.wait(timeout=args.timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        import signal
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait()
        save_result(output, {"status": "failed", "error": "Cancelled or overall time limit exceeded"})
        code = 1
    print(json.dumps({"result": str(output / "result.json"), "report": str(output / "report.md")}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
