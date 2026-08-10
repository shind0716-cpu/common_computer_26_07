# -*- coding: utf-8 -*-
"""논문 재현 트랙 — loader: 원본(ethics_issues.json) → issues/ 계약 (2026-08-10 · 요한).

지위: 모듈 1/3 (사양 docs/proposals/PAPER_REPRO_HANDOFF.md §5-1). **LLM 호출 0.**
저자 대응물 없음(저자는 datasets/*.json 을 그대로 읽는다) — 우리 계약으로 옮기는 순수 변환.

매핑 (§5-1 그대로):
  background -> body · title -> title · "paper" -> source
  question   -> 항목별 제목 (HANDOFF §12 Q3 판정: 영어 AITA 제목. 원본의 한국어 획일
                질문은 쓰지 않되 source_meta.origin_question 에 보존한다 — 버리지 않는다)
  gold       -> {label, scores}  (계약 밖 §7 임시 처리 — 버리는 것만 금지)
  source_meta-> {url: null, fetched_at: 적재 시각, usage_approved: null(라이선스 미확인),
                origin_id: 원본 id, origin_question: 원본 질문}

issue_id 는 순번제 issue_ethics_NNNN — **원본 710건 파일 내 위치(1-based)로 고정**한다.
표본을 다시 뽑아도 같은 항목은 같은 id 를 갖는다(재추출 시 인덱스 밀림 방지 — 저자
위치 인덱스 방식의 함정을 id 계약으로 막는 지점).

표본 (§6 + §12-4):
  동점 28건 제외(RIGHT==WRONG, gold_label 전건 YES 강제 실측) → 풀 682건.
  gold_label 층화(NO 394/YES 288 비율 유지) + 시드 고정 무작위.
  선정 시드·뽑힌 id 전체(원본 id + issue_id)를 sample_manifest.json 에 기록한다.
  앞에서부터 자르지 않는다(news_raw 의 선두 편향과 겹치지 않기 위해).

산출: experiments/paper_repro/data/issues/ (§8 — 팀 data/ 에 쏟지 않는다).
검사: 산출 전건 python -m modules.validate 통과 (규약 3). 이 러너가 직접 돌린다.

사용:
  PYTHONUTF8=1 python experiments/paper_repro/load_issues.py            # 기본 n=200
  PYTHONUTF8=1 python experiments/paper_repro/load_issues.py --n 20 --dry
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

SCHEMA_VER = "0.3"
CREATED_BY = "paper_repro_loader"

# 정본 원본의 sha256 (2026-08-10 probe·manifest 실측 고정). issue_id 순번이 이 파일의
# 항목 순서에 전적으로 의존하므로, 다른/재정렬된 원본으로 재실행하면 같은 issue_id 가
# 다른 내용으로 덮어써진다 — 역리뷰 R-4(GPT-sol, 2026-08-10). 기본 동작은 불일치 즉사이며
# 정본 교체는 --expect-sha 로 명시해야만 가능하다(조용한 교체 금지).
CANONICAL_SHA256 = "019dc13464de7783f705c8856a2bda6ba485772c1068dbafc12af64b78f5d989"


def sample_items(items: list[dict], n: int, seed: int):
    """동점 제외 + gold_label 층화 + 시드 고정. probe_extract.sample_items 와 동일 규칙.
    반환 항목에 원본 파일 내 1-based 위치(pos)를 실어 issue_id 순번의 근거로 쓴다."""
    indexed = [dict(x, _pos=i + 1) for i, x in enumerate(items)]
    pool = [x for x in indexed if x["label_scores"]["RIGHT"] != x["label_scores"]["WRONG"]]
    rng = random.Random(seed)
    by = {"NO": [x for x in pool if x["gold_label"] == "NO"],
          "YES": [x for x in pool if x["gold_label"] == "YES"]}
    for v in by.values():
        rng.shuffle(v)
    share = {k: round(n * len(v) / len(pool)) for k, v in by.items()}
    while sum(share.values()) < n:
        share[max(by, key=lambda k: len(by[k]))] += 1
    while sum(share.values()) > n:
        share[max(share, key=share.get)] -= 1
    out = [x for k, c in share.items() for x in by[k][:c]]
    rng.shuffle(out)
    return out, len(pool), share


def to_issue_doc(item: dict, fetched_at: str) -> dict:
    """원본 항목 1건 → issues/ 계약 문서. 순수 함수 — 여기서만 매핑한다."""
    issue_id = f"issue_ethics_{item['_pos']:04d}"
    return {
        "schema_ver": SCHEMA_VER,
        "created_by": CREATED_BY,
        "created_at": fetched_at,
        "issue_id": issue_id,
        "source": "paper",
        "source_meta": {
            "url": None,
            "fetched_at": fetched_at,
            "usage_approved": None,  # Scruples/RealNews 라이선스 미확인 — 확인 전엔 null 유지
            "origin_id": item["id"],
            "origin_question": item["question"],  # 한국어 획일 질문 — 쓰지 않되 보존(규약 8)
        },
        "title": item["title"],
        # HANDOFF §12 Q3 판정: 질문 문자열 = 항목별 제목(영어 AITA). SCHEMA §1′ 경계 1
        # (폴백의 조용한 발동)을 피하기 위해 **명시적으로** 채운다 — 부재 폴백에 맡기지 않는다.
        "question": item["title"],
        "body": item["background"],
        "gold": {"label": item["gold_label"], "scores": item["label_scores"]},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(Path.home() / "Downloads" / "ethics_issues.json"))
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20260810)
    ap.add_argument("--out-dir", default=str(HERE / "data"))
    ap.add_argument("--dry", action="store_true", help="파일을 쓰지 않고 표본·매핑만 리허설")
    ap.add_argument("--expect-sha", default=CANONICAL_SHA256,
                    help="원본 sha256 정본값. 불일치 시 즉사 — issue_id 순번이 원본 순서에 "
                         "의존하므로 다른 원본으로는 재실행 금지 (역리뷰 R-4)")
    args = ap.parse_args()

    src = Path(args.src)
    raw_bytes = src.read_bytes()
    src_sha = hashlib.sha256(raw_bytes).hexdigest()
    if src_sha != args.expect_sha:
        raise SystemExit(
            f"[loader] 원본 sha256 불일치 — 정본 {args.expect_sha[:16]}… vs 실제 {src_sha[:16]}…\n"
            "  issue_id 는 원본 파일 내 위치 순번이라, 재정렬/교체된 원본으로 실행하면\n"
            "  같은 issue_id 가 다른 내용으로 덮어써진다. 정본 교체가 의도라면 --expect-sha 로\n"
            "  새 값을 명시하고 기존 data/issues/ 를 함께 재생성하라.")
    items = json.loads(raw_bytes.decode("utf-8"))

    sample, pool_n, share = sample_items(items, args.n, args.seed)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    print(f"[loader] 원본 {len(items)}건 sha256={src_sha[:16]}… · 동점 제외 후 풀 {pool_n}건")
    print(f"[loader] 표본 {len(sample)}건 (층화 {share}, seed={args.seed}) · dry={args.dry}")

    out_root = Path(args.out_dir)
    issues_dir = out_root / "issues"
    docs = [to_issue_doc(it, fetched_at) for it in sample]

    if args.dry:
        for d in docs[:5]:
            print(f"    {d['issue_id']}  [{d['gold']['label']}] {d['title'][:58]}")
        print(f"[loader] --dry — 파일 미작성 (예정 경로: {issues_dir})")
        return

    issues_dir.mkdir(parents=True, exist_ok=True)
    for d in docs:
        p = issues_dir / f"{d['issue_id']}.json"
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "schema_ver": SCHEMA_VER,
        "created_by": CREATED_BY,
        "created_at": fetched_at,
        "source": {"path": str(src), "sha256": src_sha, "n_items": len(items)},
        "sample": {
            "seed": args.seed,
            "n": len(sample),
            "pool_after_tie_drop": pool_n,
            "n_tie_dropped": len(items) - pool_n,
            "strata": share,
            "ids": [{"issue_id": d["issue_id"], "origin_id": d["source_meta"]["origin_id"],
                     "gold_label": d["gold"]["label"]} for d in docs],
        },
        "deviations": ["P-2 표본 출처(역추정 710건)", "P-3 동점 28건 제외",
                       "라이선스 미확인 — usage_approved 전건 null"],
    }
    (out_root / "sample_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # 규약 3 — 산출 전건 자가 검사. 통과 전엔 완료가 아니다.
    from modules import validate as validate_mod  # noqa: E402
    for d in docs:
        validate_mod.validate(issues_dir / f"{d['issue_id']}.json")
    print(f"[loader] {len(docs)}건 작성·검사 통과 · manifest: {out_root / 'sample_manifest.json'}")


if __name__ == "__main__":
    main()
