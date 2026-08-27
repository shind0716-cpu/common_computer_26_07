"""[공용 코어 · 압박×카테고리] 수첩 원문 보기 — 1차 1단계 60판.

원문을 그대로 찍는다(CLAUDE.md 규약 5). 요약하지 않는다.
사실마다 「안/밖」과 두 코더의 판독을 붙여 두어, 판독이 맞는지 눈으로 볼 수 있게 했다.

    python show_notes.py                       30벌 목록과 d 값
    python show_notes.py biz_meeting           그 벌의 A·B 두 판 전부
    python show_notes.py cat_feeding_party --r0    r0 수첩만
    python show_notes.py community_room --plain    사실표 없이 수첩만
    python show_notes.py --gate                관문 탈락 9벌만 목록

재료 이름은 `issue_` 를 떼도 되고 일부만 적어도 된다(`biz` → `issue_restaurant_biz_meeting`).
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import analyze_stage1 as S  # noqa: E402

MARK = {"보": "보존", "부": "부분", "변": "변형", "-": "탈락"}
BAR = "─" * 78


def resolve(key, q):
    q = q.lower().replace("issue_", "")
    hit = [i for i in sorted(key) if q in i.lower()]
    if len(hit) == 1:
        return hit[0]
    if not hit:
        print(f"그런 벌이 없다: {q}\n\n" + "\n".join("  " + i for i in sorted(key)))
    else:
        print("여럿이 걸린다:\n" + "\n".join("  " + i for i in hit))
    sys.exit(1)


def listing(key, mats, runs, rows, gate_only=False):
    print(f"{'재료':34s} {'관문':>4s} {'r0 d':>7s} {'생존 d':>7s}   최종 선택 (A / B)")
    print(BAR)
    for iid in sorted(key):
        fa, fb = runs[(iid, "A")]["final_poll"], runs[(iid, "B")]["final_poll"]
        g = fa != fb
        if gate_only and g:
            continue
        d0, ds, _ = rows[iid]
        f = lambda x: "   –  " if x is None else f"{x:+6.2f}"
        al = mats[iid]["aligned"]
        t = lambda s, v: "정렬" if v == al[s] else "역"
        print(f"  {iid:32s} {'통과' if g else '탈락':>4s} {f(d0)} {f(ds)}   {t('A', fa)} / {t('B', fb)}")
    print(f"\n  d = p안 − p밖. 「역」 = 그 판이 자기 가치의 정렬 답을 안 골랐다.")
    print(f"  한 벌 보기:  python show_notes.py <이름 일부>")


def show(iid, key, mats, runs, coders, only_r0=False, plain=False):
    M = mats[iid]
    slot_of = {key[iid]["slot1"]: "①", key[iid]["slot2"]: "②"}
    print(BAR)
    print(f"■ {iid}    (판독 팩에서는 ①=" + key[iid]["slot1"] + " · ②=" + key[iid]["slot2"] + ")")
    print(BAR)
    print(f"선택지  1) {M['options'][0]}    2) {M['options'][1]}")
    print(f"사실 {len(M['order'])}개 · 카테고리 A={sorted(M['sets']['A'])} B={sorted(M['sets']['B'])}")

    for s in ("A", "B"):
        r = runs[(iid, s)]
        slot = slot_of[s]
        print("\n" + BAR)
        print(f"▶ 가치 세트 {s}  (판독 팩 {slot})")
        print(BAR)
        print(f"  가치문 : {r['value_statement']}")
        print(f"  정렬 답 : {r['aligned']}")
        print(f"  최종 선택: {r['final_poll']}   → {'정렬' if r['final_poll'] == r['aligned'] else '★ 역 (가치를 안 따랐다)'}")

        if not plain:
            print(f"\n  {'id':22s} {'안/밖':4s} {'나':4s} {'헤':4s}  사실")
            for i, fid in enumerate(M["order"]):
                f = M["facts"][fid]
                side = "안" if f["category"] in M["sets"][s] else "밖"
                ja = coders["코더 A"][(iid, slot)]["r0"][i]
                jb = coders["헤르메스"][(iid, slot)][("r0")][i]
                la = coders["코더 A"][(iid, slot)]["last"][i]
                lb = coders["헤르메스"][(iid, slot)]["last"][i]
                d = "  " if (ja, la) == (jb, lb) else " ≠"
                print(f"  {fid:22s} {side:4s} {MARK[ja]}→{MARK[la]} {MARK[jb]}→{MARK[lb]}{d} {f['text']}")
            print("     (r0 → 마지막 · 왼쪽이 나, 오른쪽이 헤르메스 · ≠ 는 갈린 자리)")

        notes = r["notes"]
        for n, note in enumerate(notes):
            if only_r0 and n:
                break
            same = " ※ 앞 수첩과 글자까지 같다" if n and note == notes[n - 1] else ""
            print(f"\n  ── 수첩 r{n} ({len(note)}자){same} " + "─" * 30)
            for line in note.splitlines():
                print("  " + line)
    print()


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    key, mats, runs = S.load_all()
    coders = {n: S.load_coding(p) for n, p in
              (("코더 A", "READ60_coderA"), ("헤르메스", "READ60_hermes"))}
    rows = {i: S.pair_d(mats, coders["코더 A"], key, i) for i in key}
    if not args:
        listing(key, mats, runs, rows, gate_only="--gate" in flags)
        return 0
    show(resolve(key, args[0]), key, mats, runs, coders,
         only_r0="--r0" in flags, plain="--plain" in flags)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
