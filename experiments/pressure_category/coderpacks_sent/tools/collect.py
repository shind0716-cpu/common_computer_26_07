# -*- coding: utf-8 -*-
"""판독 산출물을 모으고 빠진 것을 찾는다. 열쇠를 열지 않는다. 호출 0."""
import glob, os, re, json, sys
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = json.load(open(f"{OUT}/_KEY_S.json", encoding="utf-8"))
GAL = {"사실", "결론", "되풀이", "단서", "지시", "그밖"}
NEW = {"예", "아니오"}

got, bad = {}, []
for path in sorted(glob.glob(f"{OUT}/packs/OUT_S_*.md")):
    text = open(path, encoding="utf-8").read()
    blocks = re.split(r"^##\s+(N-\d{2})\s*$", text, flags=re.M)
    for i in range(1, len(blocks), 2):
        nid, body = blocks[i], blocks[i + 1]
        rows = {}
        for line in body.splitlines():
            m = re.match(r"^\|\s*(s\d\d)\s*\|", line)
            if not m: continue
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) < 3 or c[1] not in GAL or c[2] not in NEW:
                bad.append((os.path.basename(path), nid, line.strip())); continue
            rows[m.group(1)] = (c[1], c[2])
        want = KEY[nid]["n_sents"] if nid in KEY else -1
        if len(rows) != want:
            bad.append((os.path.basename(path), nid, f"줄 {len(rows)}/{want}"))
        else:
            got[nid] = rows

miss = sorted(set(KEY) - set(got))
print(f"온전한 수첩 {len(got)}/{len(KEY)} · 형식 어긋남 {len(bad)}")
if miss:
    packs = sorted({f"{(int(n[2:]) - 1) // 8 + 1:02d}" for n in miss})
    print(f"  빠진 수첩 {len(miss)}: {', '.join(miss)}")
    print(f"  → 다시 돌릴 팩: {', '.join(packs)}")
for b in bad[:12]:
    print(f"  어긋남 {b[0]} {b[1]}: {b[2]}")
if len(got) == len(KEY) and not bad:
    json.dump(got, open(f"{OUT}/_COLLECTED_S.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("  → _COLLECTED_S.json 썼다. 이제 열쇠를 열어도 된다.")
    sys.exit(0)
print("\n빠진 팩만 다시 돌린 뒤 이 검사를 통과시킨다. 그 전에는 열쇠를 열지 않는다.")
sys.exit(1)
