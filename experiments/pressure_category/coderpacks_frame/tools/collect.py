# -*- coding: utf-8 -*-
"""판독을 모으고 빠진 것을 찾는다. 열쇠를 열지 않는다. 호출 0."""
import glob, os, re, json, sys
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = json.load(open(f"{H}/_KEY_F.json", encoding="utf-8"))
FR = {"있음", "없음"}
PU = {"1", "2", "어느 쪽도 아님", "해당 없음"}
got, bad = {}, []
for path in sorted(glob.glob(f"{H}/packs/OUT_F_*.md")):
    text = open(path, encoding="utf-8").read()
    blk = re.split(r"^##\s+(F-\d{3})\s*$", text, flags=re.M)
    for i in range(1, len(blk), 2):
        fid, body = blk[i], blk[i + 1]
        row = None
        for line in body.splitlines():
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) < 2 or c[0] in ("틀", "---") or c[0].startswith("--"): continue
            if c[0] not in FR: continue
            push = c[1] if len(c) > 1 else ""
            if push not in PU:
                bad.append((os.path.basename(path), fid, line.strip())); break
            row = dict(frame=c[0], push=push, quote=(c[2] if len(c) > 2 else "").strip())
            break
        if row is None:
            bad.append((os.path.basename(path), fid, "판정 줄 없음")); continue
        if row["frame"] == "있음" and not row["quote"]:
            bad.append((os.path.basename(path), fid, "「있음」인데 인용 없음")); continue
        got[fid] = row
miss = sorted(set(KEY) - set(got))
print(f"온전한 수첩 {len(got)}/{len(KEY)} · 형식 어긋남 {len(bad)}")
if miss:
    packs = sorted({f"{(int(n[2:]) - 1) // 8 + 1:02d}" for n in miss})
    print(f"  빠진 수첩 {len(miss)}: {', '.join(miss[:12])}{' …' if len(miss)>12 else ''}")
    print(f"  → 다시 돌릴 팩: {', '.join(packs)}")
for b in bad[:12]: print(f"  어긋남 {b[0]} {b[1]}: {b[2]}")
if len(got) == len(KEY) and not bad:
    json.dump(got, open(f"{H}/_COLLECTED_F.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("  → _COLLECTED_F.json 썼다. 이제 열쇠를 열어도 된다.")
    sys.exit(0)
print("\n빠진 팩만 다시 돌린 뒤 통과시킨다. 그 전에는 열쇠를 열지 않는다.")
sys.exit(1)
