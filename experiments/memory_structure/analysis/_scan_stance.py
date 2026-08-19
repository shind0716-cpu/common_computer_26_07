# -*- coding: utf-8 -*-
"""54런 최종 발화의 결론 방향 스캔 (LLM 호출 0). 산출: _scan_stance.tsv"""
import json, glob, io, os

BASE = os.path.join(os.path.dirname(__file__), "..", "runs")
OUT = os.path.join(os.path.dirname(__file__), "_scan_stance.tsv")

MU = "무레온"   # 정답 = 무레온 (요건 3/4 충족)
DA = "다림재"

rows = []
for f in sorted(glob.glob(os.path.join(BASE, "**", "*.json"), recursive=True)):
    d = json.load(open(f, encoding="utf-8"))
    m = d["meta"]
    last = d["essays"][-1]
    rows.append([
        m["model_key"], d["arm"], d["arm_name"], d["memory"], d["rep"],
        last.count(MU), last.count(DA), len(last),
        last[-140:].replace("\n", " ").replace("\t", " "),
    ])

with io.open(OUT, "w", encoding="utf-8") as w:
    w.write("model\tarm\tarm_name\tmemory\trep\tn_mureon\tn_darim\tlen\ttail\n")
    for r in rows:
        w.write("\t".join(str(x) for x in r) + "\n")

print("rows", len(rows))
print("darim_dominant", sum(1 for r in rows if r[6] > r[5]))
print("zero_mureon", sum(1 for r in rows if r[5] == 0))
print("both_zero", sum(1 for r in rows if r[5] == 0 and r[6] == 0))
