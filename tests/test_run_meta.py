"""run_meta 이벤트 테스트 — 산출물이 자기 조건을 아는가 (스키마 v0.3 §4‴). API 불필요.

검증 대상: ① 로그 첫 이벤트로 나오고 설정 사전 8축 좌표가 실제 실행값과 일치하는가
② config_ref.sha256 이 조건 파일의 지문으로 작동하는가(파일이 바뀌면 해시가 달라져
"같은 조건이 아님"이 드러난다) ③ validate 가 구조를 검사하되 구 로그는 통과시키는가.

민옥 측 CoopBase(협력 조건 하네스)를 재사용한다 — 저자 저장소 없이 도는 유일한 경로이고,
같은 픽스처를 두 벌 만들지 않는다(WORKING_RULES R4: 세 번째에 추출, 그 전엔 import).
"""
import contextlib
import io
import json
import unittest

import yaml

from modules import debate_engine, paths, validate
from tests.test_coop_engine import CoopBase


class RunMetaBase(CoopBase):
    def _events_with(self, **cfg_over):
        self._write_assignment(["none"] * 4)
        cfg_path = self._cfg(**cfg_over)
        with contextlib.redirect_stdout(io.StringIO()):
            path = debate_engine.run("issue_esa", "coop1", cfg_path,
                                     utterance_fn=lambda i, model=None, temperature=None: "말")
        events = [json.loads(l) for l in
                  path.read_text(encoding="utf-8").splitlines() if l.strip()]
        return events, path, cfg_path


class TestRunMeta(RunMetaBase):
    def test_is_first_event(self):
        events, _, _ = self._events_with()
        self.assertEqual(events[0]["event"], "run_meta")
        self.assertEqual(sum(1 for e in events if e["event"] == "run_meta"), 1)

    def test_settings_match_actual_run(self):
        """settings 는 config 원문 복사가 아니라 **엔진이 실제 실행한 값**이다."""
        events, _, _ = self._events_with(rounds=2, ledger_mode="off", seed=42)
        s = events[0]["settings"]
        self.assertEqual(s["rounds"], 2)
        self.assertEqual(s["ledger_mode"], "off")
        self.assertEqual(s["seed"], 42)
        self.assertEqual(s["agents"], 4)
        self.assertEqual(s["structure"], "full")      # config 미지정 → 엔진 기본값
        self.assertEqual(s["stance"], "none")         # assignment 에서 유도(협력 조건)
        # 미구현 축은 엔진의 현행 동작을 적는다 — 추측이 아니라 사실
        self.assertEqual(s["window"], "rolling")
        self.assertEqual(s["memory"], "none")
        # 정보 나누기 축은 assignment 에서 유도
        self.assertIn("overlap_k", s)
        self.assertIn("assignment_mode", s)

    def test_condition_slug_recorded_and_null_when_absent(self):
        events, _, _ = self._events_with(condition="talk-full")
        self.assertEqual(events[0]["condition"], "talk-full")
        events2, _, _ = self._events_with()          # config 에 condition 없음
        self.assertIsNone(events2[0]["condition"])

    def test_pilot_eligibility_labels_are_durable_in_run_meta(self):
        events, _, _ = self._events_with(
            condition="pilot/coop",
            promotion_tier="pilot_unvetted",
            aggregate_eligible=False,
            report_eligible=False,
        )
        meta = events[0]
        self.assertEqual(meta["promotion_tier"], "pilot_unvetted")
        self.assertFalse(meta["aggregate_eligible"])
        self.assertFalse(meta["report_eligible"])
        self.assertTrue(meta["condition"].startswith("pilot/"))

    def test_config_ref_is_a_fingerprint(self):
        """조건 파일이 바뀌면 해시가 달라진다 — 통제를 사람 기억이 아니라 지문으로 고정."""
        events, _, cfg_path = self._events_with(condition="talk-full")
        ref = events[0]["config_ref"]
        self.assertEqual(ref["name"], cfg_path.name)
        self.assertEqual(ref["sha256"],
                         debate_engine.sha256(cfg_path.read_text(encoding="utf-8")))
        # 조건을 한 칸 바꾸면 지문이 달라져야 한다(같은 조건으로 오인 방지)
        events2, _, _ = self._events_with(condition="talk-full", rounds=3)
        self.assertNotEqual(events2[0]["config_ref"]["sha256"], ref["sha256"])

    def test_same_config_same_fingerprint(self):
        """반대 방향도 지킨다 — 조건이 같으면 지문이 같아야 반복(replication)을 묶을 수 있다."""
        e1, _, _ = self._events_with(condition="talk-full")
        e2, _, _ = self._events_with(condition="talk-full")
        self.assertEqual(e1[0]["config_ref"]["sha256"], e2[0]["config_ref"]["sha256"])


class TestValidateRunMeta(RunMetaBase):
    def test_valid_log_passes(self):
        _, path, _ = self._events_with(condition="talk-full")
        with contextlib.redirect_stdout(io.StringIO()):
            validate.validate(path)          # fail 시 SystemExit

    def test_missing_field_fails(self):
        events, path, _ = self._events_with()
        del events[0]["settings"]
        path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events),
                        encoding="utf-8")
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
            validate.validate(path)

    def test_not_first_event_fails(self):
        events, path, _ = self._events_with()
        events.append(events[0])             # 두 번째 run_meta 를 뒤에 붙임
        path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events),
                        encoding="utf-8")
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
            validate.validate(path)

    def test_old_log_without_run_meta_passes(self):
        """구 로그 호환 — run_meta 가 없으면 종전대로 통과한다(append 호환)."""
        events, path, _ = self._events_with()
        rest = [e for e in events if e["event"] != "run_meta"]
        path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in rest),
                        encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            validate.validate(path)


if __name__ == "__main__":
    unittest.main()
