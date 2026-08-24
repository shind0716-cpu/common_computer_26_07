"""A/B/C same-parent judge adapter contract (LLM calls mocked: 0)."""
import json
import unittest
from unittest import mock

from modules import judge


class SameParentJudgeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.parent = "동결된 부모 응답\n둘째 줄".encode("utf-8")
        self.coordinate = {
            "issue_id": "issue_demo_v2", "arm": "B",
            "coordinate_id": "coord-b", "parent_r0_sha256": "abc",
            "condition_bundle_sha256": "def",
        }
        self.bundle = {
            "role": "posthoc_judge",
            "canonical_material": {
                "issue": {"issue_id": "issue_demo_v2", "body": "사안"},
                "facts": {"issue_id": "issue_demo_v2", "facts": []},
            },
            "common_protocol": "JSON 객체만 출력하라.",
            "detection_spec": {"issue_id": "issue_demo_v2", "spec_version": "0.2"},
        }

    def test_factory_reuses_llm_preflight_and_obtain_response_only(self):
        config = {"model": "gpt", "temperature": 0, "reasoning": "default"}
        with mock.patch.object(judge._llm, "preflight", return_value={}) as preflight, \
             mock.patch.object(judge._llm, "obtain_response",
                               return_value='{"status":"unknown"}') as obtain:
            evaluator = judge.make_same_parent_bundle_evaluator(config)
            raw = evaluator(self.parent, self.bundle, self.coordinate)
        self.assertEqual(raw, '{"status":"unknown"}')
        preflight.assert_called_once_with("gpt", temperature=0.0, reasoning="default")
        obtain.assert_called_once()
        _, kwargs = obtain.call_args
        self.assertEqual(kwargs, {"model": "gpt", "temperature": 0.0,
                                  "reasoning": "default"})

    def test_prompt_preserves_parent_text_and_declares_bundle_without_mutation(self):
        original = json.loads(json.dumps(self.bundle, ensure_ascii=False))
        with mock.patch.object(judge._llm, "preflight", return_value={}), \
             mock.patch.object(judge._llm, "obtain_response", return_value="{}") as obtain:
            evaluator = judge.make_same_parent_bundle_evaluator(
                {"model": "gpt", "temperature": 0})
            evaluator(self.parent, self.bundle, self.coordinate)
        prompt = obtain.call_args.args[0]
        self.assertIn(self.parent.decode("utf-8"), prompt)
        self.assertIn('"detection_spec"', prompt)
        self.assertIn('"coordinate_id":"coord-b"', prompt)
        self.assertEqual(self.bundle, original)

    def test_invalid_config_or_non_utf8_parent_fails_before_provider_call(self):
        invalid_configs = [
            {},
            {"model": "gpt", "temperature": 0.1},
            {"model": "gpt", "temperature": 0, "reasoning": "hidden"},
        ]
        for config in invalid_configs:
            with self.subTest(config=config), \
                 mock.patch.object(judge._llm, "preflight") as preflight:
                with self.assertRaises((ValueError, KeyError)):
                    judge.make_same_parent_bundle_evaluator(config)
                preflight.assert_not_called()
        with mock.patch.object(judge._llm, "preflight", return_value={}), \
             mock.patch.object(judge._llm, "obtain_response") as obtain:
            evaluator = judge.make_same_parent_bundle_evaluator(
                {"model": "gpt", "temperature": 0})
            with self.assertRaises(UnicodeDecodeError):
                evaluator(b"\xff", self.bundle, self.coordinate)
            obtain.assert_not_called()


if __name__ == "__main__":
    unittest.main()
