# -*- coding: utf-8 -*-
"""판독 산출물을 모으고 빠진 것을 찾는다. 열쇠를 열지 않는다. 호출 0.

    python tools/collect.py                # 둘 다
    python tools/collect.py meaning2       # 하나만
"""
import glob, os, re, sys, json

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = {
    # 사실 이름표는 재료마다 다르다 — 열 벌은 f01, cat_feeding_days_list 는 cfd_days_list_01.
    # 이름으로 맞추면 깨지므로 **자리 순서**로 맞춘다. 줄 수·순서·값은 그대로 검사한다.
    "meaning2": dict(prefix="OUT_M", per=3, rows=12, cols=2,
                     ok={"있음", "이름만", "없음"}, rowre=r"^\|\s*([A-Za-z0-9_]*[0-9]{2})\s*\|"),
    "path2":    dict(prefix="OUT_P", per=6, rows=4,  cols=1,
                     ok={"1", "2", "모름"}, rowre=r"^\|\s*글([1-4])\s*\|"),
}

def parse(track):
    s = SPEC[track]
    got, bad = {}, []
    for path in sorted(glob.glob(f"{OUT}/{track}/{s['prefix']}_*.md")):
        text = open(path, encoding="utf-8").read()
        blocks = re.split(r"^##\s+(P-\d{3})\s*$", text, flags=re.M)
        for i in range(1, len(blocks), 2):
            pid, body = blocks[i], blocks[i + 1]
            rows = {}
            for line in body.splitlines():
                m = re.match(s["rowre"], line)
                if not m: continue
                cells = [c.strip() for c in line.strip().strip("|").split("|")][1:]
                if len(cells) < s["cols"] or any(c not in s["ok"] for c in cells[:s["cols"]]):
                    bad.append((os.path.basename(path), pid, line.strip())); continue
                rows[m.group(1)] = cells[:s["cols"]]
            if track == "meaning2" and len(rows) == s["rows"]:
                nums = [int(re.search(r"(\d+)$", x).group(1)) for x in rows]
                if nums != list(range(1, s["rows"] + 1)):
                    bad.append((os.path.basename(path), pid, f"줄 순서 {nums}")); continue
            if len(rows) != s["rows"]:
                bad.append((os.path.basename(path), pid, f"줄 {len(rows)}/{s['rows']}"))
            else:
                got[pid] = list(rows.values()) if track == "meaning2" else rows
    return got, bad

def main(tracks):
    all_ok = True
    for t in tracks:
        s = SPEC[t]
        got, bad = parse(t)
        want = {f"P-{n:03d}" for n in range(1, 199)}
        missing = sorted(want - set(got))
        packs = sorted({f"{(int(p[2:]) - 1) // s['per'] + 1:02d}" for p in missing})
        print(f"[{t}] 온전한 판 {len(got)}/198 · 형식 어긋남 {len(bad)}")
        if missing:
            all_ok = False
            print(f"  빠진 판 {len(missing)}: {', '.join(missing[:12])}{' …' if len(missing) > 12 else ''}")
            print(f"  → 다시 돌릴 팩: {', '.join(packs)}")
        for b in bad[:10]:
            print(f"  어긋남 {b[0]} {b[1]}: {b[2]}")
        if len(got) == 198 and not bad:
            json.dump(got, open(f"{OUT}/_COLLECTED_{t}.json", "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            print(f"  → _COLLECTED_{t}.json 썼다. 이제 열쇠를 열어도 된다.")
    if not all_ok:
        print("\n빠진 팩만 다시 돌린 뒤 이 검사를 다시 통과시킨다. 그 전에는 열쇠를 열지 않는다.")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["meaning2", "path2"]))
