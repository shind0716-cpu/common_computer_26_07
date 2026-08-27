"""[공용 코어 · 압박×카테고리] 수첩 판독 팩 생성기 — 60판을 가린 채 읽기 위한 것.

사전고정 `SELECTION_live30_2026-08-27.md` §21 절차를 파일로 옮긴 것이다.

- 가리는 것: 가치 세트(A/B) · 각본 · 모델 · 표식 수 · 최종 선택 (§21-4)
- 여는 것: 재료의 사실 12개 · 구체 목록(§20) · 그 판의 r0/마지막 수첩 원문
- A/B 를 ①② 중 어디에 넣을지는 `md5(SALT + issue_id)` 홀짝으로 정한다(결정적).
  열쇠는 `READ60_key.json` 하나에만 있고, 판독을 닫기 전에 열지 않는다.

묶음은 재료 사전순 10벌씩 셋. 팩 자체에는 판정이 안 들어가므로 여섯 개를 한꺼번에
만들어 두어도 가림이 안 깨진다 — 깨지는 것은 「읽는 순서」이고 그건 사람이 지킨다.

  python make_read60_pack.py            # 여섯 개 전부
  python make_read60_pack.py 2 r0       # 묶음 2 · r0 만
"""
import hashlib
import json
import pathlib
import sys

SALT = "read60-2026-08-27"
ROOT = pathlib.Path(__file__).resolve().parent


def _load():
    ids = sorted((ROOT / "_live30_ids.txt").read_text(encoding="utf-8").split())
    byid = {}
    for p in (ROOT / "materials").glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("issue_id"):
            byid[d["issue_id"]] = (p.stem, d)
    conc = json.loads(
        (ROOT / "CONCRETE_LIST_2026-08-27.json").read_text(encoding="utf-8")
    )["materials"]
    return ids, byid, conc


def _key(ids):
    """열쇠는 한 번만 만든다. 이미 있으면 그대로 읽는다(재생성해도 같은 값이지만)."""
    p = ROOT / "READ60_key.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    key = {}
    for n, i in enumerate(ids):
        h = int(hashlib.md5((SALT + i).encode()).hexdigest(), 16)
        order = ["A", "B"] if h % 2 == 0 else ["B", "A"]
        key[i] = {"batch": n // 10 + 1, "slot1": order[0], "slot2": order[1]}
    p.write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    return key


def pack(batch, which, ids, byid, conc, key):
    mem = [i for i in ids if key[i]["batch"] == batch]
    label = "r0 수첩" if which == "r0" else "마지막 수첩"
    out = [
        f"# 수첩 판독 60판 — 묶음 {batch} · {label} (가린 판)",
        "",
        "판정 넷: `보존` 구체가 다 살아 있다 / `부분` 항목은 있는데 구체가 빠졌다 /",
        "`변형` 항목도 구체도 있는데 원본과 다르다 / `탈락` 어떤 형태로도 없다",
        "",
        "수첩 단위 라벨 하나: 「원본에 없는 것이 생겼나」",
        "",
    ]
    for i in mem:
        stem, mat = byid[i]
        C = conc[stem]
        out.append(f'\n## {i}   [{mat["options"][0]} / {mat["options"][1]}]')
        out.append(f'사안: {mat["stub"]}')
        out.append("\n| id | 사실 | 항목 | 구체 |")
        out.append("|---|---|---|---|")
        for f in mat["facts"]:
            e = C[f["id"]]
            grounds = " · ".join(e["grounds"])
            out.append(f'| {f["id"]} | {f["text"]} | {e["item"]} | {grounds} |')
        for slot in (1, 2):
            v = key[i][f"slot{slot}"]
            d = json.loads(
                (ROOT / "runs/gpt" / i / f"run_C0_{v}_rep1.json").read_text(
                    encoding="utf-8"
                )
            )
            notes = d.get("notes") or []
            note = notes[0] if which == "r0" else notes[-1]
            mark = "①" if slot == 1 else "②"
            out.append(f"\n**판 {mark}** ({len(note)}자)\n")
            out.append("> " + note.replace("\n", "<br>"))
    return "\n".join(out)


def main(argv):
    ids, byid, conc = _load()
    key = _key(ids)
    todo = [(b, w) for b in (1, 2, 3) for w in ("r0", "last")]
    if len(argv) == 3:
        todo = [(int(argv[1]), argv[2])]
    for b, w in todo:
        p = ROOT / f"READ60_pack_b{b}_{w}.md"
        p.write_text(pack(b, w, ids, byid, conc, key), encoding="utf-8")
        print(f"  {p.name}  {p.stat().st_size:>6,}바이트")


if __name__ == "__main__":
    main(sys.argv)
