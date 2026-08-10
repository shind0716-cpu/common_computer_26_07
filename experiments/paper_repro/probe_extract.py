# -*- coding: utf-8 -*-
"""논문 재현 트랙 — 착수 전 검증 프로브 Q1/Q2/Q3a (2026-08-10 · 요한).

지위: **사전 검증** (설계 확정 전 · 본 추출 아님). 여기서 나온 수치로 추출 모델과
질문 문자열을 정한 뒤에 본 추출을 짓는다. 결정 규칙은 **돌리기 전에** 박았다
(docs/proposals/PAPER_REPRO_HANDOFF.md 및 2026-08-10 대화).

무엇을 재는가
  Q1  추출 모델(gpt-5 vs gpt-5.4-mini)이 팩트 토대를 바꾸는가
      관측량: 항목당 팩트 개수 · critical 비율 · (사람 판독용) 두 목록 병기
      **문자열 대조는 쓰지 않는다** — 팩트 텍스트가 재작성되므로 구조적으로 틀린다
      (NOTE_SLOT §4 · H2 근접도 0.641 실측). LLM 대조기도 넣지 않는다(판정 층 증식).
  Q2  질문 언어가 중요도 선정을 바꾸는가 (한국어 획일 vs 영어 획일)
  Q3a 질문 형태가 중요도 선정을 바꾸는가 (영어 획일 vs 항목별 제목)
      Q2·Q3a 는 refined_facts 를 고정하고 facts_select 만 갈아 끼우므로 **정확 비교**다
      (같은 팩트 목록에 대한 0/1 배열 일치율, 단위는 팩트).
  Q5  팩트 수 하한을 정할 근거 — 팩트 개수 분포 (부산물, 추가 비용 0)

표본
  ethics_issues.json 710건에서 **동점 28건 제외**(RIGHT==WRONG 인데 gold_label 이 전건
  YES 로 강제돼 있다 — 2026-08-10 감사) → 682건 풀. gold_label 층화 + 시드 고정 무작위.
  뽑힌 id 전체를 산출물에 기록한다.

저자 계승
  프롬프트는 저자 저장소 원문 직독(modules.authors_prompts) — 복사본 금지.
  단계·온도·n 은 저자 facts.py 그대로 (facts_initial → facts_refine → facts_select,
  temperature=0, n=1).

안전장치: 전역 호출 상한 · 호출 단위 체크포인트(재개) · --dry(0콜) · 응답 원문 보존(규약 5).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from modules import authors_prompts, llm  # noqa: E402

# --- 편차 P-1: 출력 상한 완화 (2026-08-10 실측으로 강제됨) --------------------
# 저자 utils.obtain_response 는 max_tokens 를 **아예 보내지 않는다**(API 기본값).
# 우리 llm.MAX_TOKENS=2048 은 우리 쪽 인위적 상한이고, gpt-5 의 사고 토큰이 그
# 예산을 먹어 첫 호출부터 LLMTruncated 로 죽었다(민옥 7/30 절단 관문이 정상 작동).
# reasoning 을 끄는 대신 상한만 올린다 — reasoning="off" 는 모델의 계산 자체를
# 바꿔 저자(파라미터 미전송=default)와 달라지지만, 상한 완화는 우리가 덧붙인
# 제약을 걷어내 저자 조건에 **가까워지는** 방향이다.
# llm.py 는 동범 님 담당 파일이라 수정하지 않는다 — 이 러너에서 모듈 상수만 올린다.
_MAX_TOKENS_PROBE = 8192
llm.MAX_TOKENS = _MAX_TOKENS_PROBE

# 질문 후보 3종 (Q2·Q3a)
Q_KO_UNIFORM = "이 상황에서 글 작성자는 도덕적으로 잘못했는가?"      # 데이터 원본
Q_EN_UNIFORM = "Is the author in the wrong in this situation?"       # 영어 획일
# 항목별 제목은 실행 시 item['title'] 로 채운다

MODELS = ["gpt-5", "gpt-mini"]          # gpt-mini -> gpt-5.4-mini
_calls = 0
_cap = 0
_ck_path: Path | None = None            # main 에서 지정 — dry/live 별도 파일


def call(inputs: str, model: str, tag: str, ckpt, dry: bool) -> str:
    """PR#34 리뷰 반영: dry/live 네임스페이스 격리(별도 파일) + 매 성공 호출 직후
    append+flush(항목 중간 실패 시 유료 결과 유실 방지) + 적중 시 좌표 대조."""
    global _calls
    key = tag
    mode = "dry" if dry else "live"
    if key in ckpt:
        rec = ckpt[key]
        # 부재=모름: mode/prompt_ver 없는 구 기록(프로브 40콜)은 live 실측으로 허용.
        if rec.get("mode", "live") != mode:
            raise SystemExit(
                f"체크포인트 모드 오염({tag}): 기록={rec.get('mode')} 현재={mode} — "
                f"dry 잔재가 live 캐시에 섞임. 파일 확인: {_ck_path}")
        if "prompt_ver" in rec and rec["prompt_ver"] != authors_prompts.version_tag():
            raise SystemExit(
                f"체크포인트 prompt_ver 불일치({tag}): 기록={rec['prompt_ver']} "
                f"현재={authors_prompts.version_tag()} — 낡은 캐시 재사용 금지")
        return rec["raw"]
    if dry:
        raw = '["dry"]'
    else:
        if _calls >= _cap:
            raise RuntimeError(f"전역 호출 상한 {_cap} 도달 — 중단(체크포인트 저장됨)")
        raw = llm.obtain_response(inputs, model=model, temperature=0.0)
        _calls += 1
    rec = {"tag": tag, "model": model, "temperature": 0.0, "n": 1,
           "prompt_ver": authors_prompts.version_tag(), "mode": mode,
           "raw": raw}          # 규약 5 — 원문 그대로
    if _ck_path is not None:
        _ck_path.parent.mkdir(parents=True, exist_ok=True)
        with _ck_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
    ckpt[key] = rec
    return raw


def obtain_json(data: str):
    """저자 utils.obtain_json 계승 — 실패 시 원문을 그대로 돌려준다."""
    try:
        return json.loads(data.replace("```json", "").replace("```", "").replace("\\n", ""))
    except Exception:  # noqa: BLE001
        return data


def sample_items(items: list[dict], n: int, seed: int) -> list[dict]:
    """동점 제외 + gold_label 층화 + 시드 고정."""
    pool = [x for x in items if x["label_scores"]["RIGHT"] != x["label_scores"]["WRONG"]]
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


def main() -> None:
    global _cap
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(Path.home() / "Downloads" / "ethics_issues.json"))
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20260810)
    ap.add_argument("--max-calls", type=int, default=60)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--out-dir", default=str(HERE / "probe"))
    args = ap.parse_args()
    _cap = args.max_calls

    src = Path(args.src)
    raw_bytes = src.read_bytes()
    src_sha = hashlib.sha256(raw_bytes).hexdigest()
    items = json.loads(raw_bytes.decode("utf-8"))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # dry 는 별도 파일 — live 캐시(probe_calls.jsonl)를 읽지도 쓰지도 않는다(PR#34 리뷰).
    ck_path = out_dir / ("probe_calls_dry.jsonl" if args.dry else "probe_calls.jsonl")
    global _ck_path
    _ck_path = ck_path
    ckpt = {}
    if ck_path.exists():
        for line in ck_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if not args.dry and r.get("mode", "live") != "live":
                    raise SystemExit(
                        f"live 체크포인트에 dry 잔재 발견(tag={r['tag']}): {ck_path} — "
                        "오염 행을 제거하거나 파일을 격리한 뒤 재실행하라")
                ckpt[r["tag"]] = r
    n_before = len(ckpt)

    sample, pool_n, share = sample_items(items, args.n, args.seed)
    print(f"[probe] 원본 {len(items)}건 sha256={src_sha[:16]}… · 동점 제외 후 풀 {pool_n}건")
    print(f"[probe] 표본 {len(sample)}건 (층화 {share}, seed={args.seed}) · "
          f"체크포인트 {n_before}건 · 상한 {_cap} · dry={args.dry}")
    for x in sample:
        print(f"    {x['id']}  [{x['gold_label']}] {x['title'][:58]}")

    results = []
    for it in sample:
        rec = {"id": it["id"], "title": it["title"], "gold_label": it["gold_label"],
               "n_chars": len(it["background"]), "by_model": {}}
        for model in MODELS:
            p1 = authors_prompts.load("facts_initial").replace("<===text===>", it["background"])
            raw1 = call(p1, model, f"{it['id']}|{model}|initial", ckpt, args.dry)
            rawf = obtain_json(raw1)

            ft = "".join(f"{x}\n" for x in rawf) if isinstance(rawf, list) else str(rawf)
            p2 = (authors_prompts.load("facts_refine")
                  .replace("<===text===>", it["background"]).replace("<===facts===>", ft))
            raw2 = call(p2, model, f"{it['id']}|{model}|refine", ckpt, args.dry)
            refined = obtain_json(raw2)

            rt = "".join(f"{x}\n" for x in refined) if isinstance(refined, list) else str(refined)
            # Q1 은 질문을 고정한다 — 항목별 제목(후보 2, 권장 기본값)
            p3 = (authors_prompts.load("facts_select")
                  .replace("<===question===>", it["title"]).replace("<===facts===>", rt))
            raw3 = call(p3, model, f"{it['id']}|{model}|select|title", ckpt, args.dry)
            imp = obtain_json(raw3)

            rec["by_model"][model] = {
                "n_raw": len(rawf) if isinstance(rawf, list) else None,
                "n_refined": len(refined) if isinstance(refined, list) else None,
                "refined": refined if isinstance(refined, list) else None,
                "important_title": imp if isinstance(imp, list) else None,
            }

        # Q2·Q3a — 저자 모델(gpt-5)의 refined 고정, 질문만 교체
        ref = rec["by_model"]["gpt-5"].get("refined")
        if ref:
            rt = "".join(f"{x}\n" for x in ref)
            for label, q in (("ko_uniform", Q_KO_UNIFORM), ("en_uniform", Q_EN_UNIFORM)):
                p3 = (authors_prompts.load("facts_select")
                      .replace("<===question===>", q).replace("<===facts===>", rt))
                r = call(p3, "gpt-5", f"{it['id']}|gpt-5|select|{label}", ckpt, args.dry)
                rec[f"important_{label}"] = obtain_json(r) if isinstance(obtain_json(r), list) else None
        results.append(rec)
        # 파일 기록은 call() 안에서 매 성공 호출 직후 append+flush 로 이미 끝났다.
        print(f"[probe] {it['id'][:28]}… 완료 · 누적 호출 {_calls}/{_cap}")

    meta = {"deviations": [f"P-1 max_tokens {_MAX_TOKENS_PROBE} (llm.MAX_TOKENS 2048 완화 — "
                           "저자는 상한 미전송)"] + list(getattr(llm, "LAST_DEVIATIONS", [])),
            "source": {"path": str(src), "sha256": src_sha, "n_items": len(items)},
            "sample": {"seed": args.seed, "n": len(sample), "pool_after_tie_drop": pool_n,
                       "strata": share, "ids": [x["id"] for x in sample]},
            "models": MODELS, "prompt_ver": authors_prompts.version_tag(),
            "questions": {"ko_uniform": Q_KO_UNIFORM, "en_uniform": Q_EN_UNIFORM,
                          "title": "<item title>"},
            "n_calls_this_run": _calls,
            "results": results}
    (out_dir / "probe_result.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[probe] 저장: {out_dir/'probe_result.json'} · 이번 실행 호출 {_calls}")


if __name__ == "__main__":
    main()
