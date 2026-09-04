from __future__ import annotations

import unittest

from mj_video_intelligence import AgenticVideoAnalyzer, IndexedVideoTools, VideoBudget


class ScriptedModel:
    def __init__(self, actions: list[dict]) -> None:
        self.actions = iter(actions)
        self.states: list[dict] = []

    def next_action(self, state: dict) -> dict:
        self.states.append(state)
        return next(self.actions)


class PackageCoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = {
            "url": "https://example.com/video",
            "title": "Example",
            "duration_seconds": 60,
            "transcript_segments": [
                {"start_seconds": 5, "end_seconds": 9, "text": "recommended restaurant"},
            ],
            "frame_candidates": [
                {"timestamp_seconds": 7, "artifact_ref": "frame-7.jpg"},
            ],
        }

    def test_package_runs_without_narmer(self) -> None:
        model = ScriptedModel(
            [
                {"action": "search_transcript", "arguments": {"query": "restaurant"}},
                {"action": "finish", "result": {"answer": "found"}},
            ]
        )
        result = AgenticVideoAnalyzer(model, IndexedVideoTools(self.evidence)).analyze(self.evidence)
        self.assertEqual(result, {"answer": "found"})

    def test_host_validator_is_injected(self) -> None:
        called = []
        model = ScriptedModel([{"action": "finish", "result": {"answer": "found"}}])
        analyzer = AgenticVideoAnalyzer(
            model,
            IndexedVideoTools(self.evidence),
            VideoBudget(),
            result_validator=lambda result, evidence: called.append((result, evidence)),
        )
        analyzer.analyze(self.evidence)
        self.assertEqual(len(called), 1)

    def test_objective_and_schema_are_sent_to_model(self) -> None:
        model = ScriptedModel([{"action": "finish", "result": {"products": []}}])
        schema = {"type": "object", "required": ["products"]}
        AgenticVideoAnalyzer(
            model,
            IndexedVideoTools(self.evidence),
            objective="Extract product names and prices only.",
            result_schema=schema,
        ).analyze(self.evidence)
        self.assertEqual(model.states[0]["objective"], "Extract product names and prices only.")
        self.assertEqual(model.states[0]["result_schema"], schema)


if __name__ == "__main__":
    unittest.main()
