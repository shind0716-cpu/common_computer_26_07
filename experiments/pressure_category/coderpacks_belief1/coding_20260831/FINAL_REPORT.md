# Belief-1 blind coding report

Generated: `2026-08-31T20:43:58+09:00`
Seed: `20260831`

## Status and scope

All three packs were coded, checked, adjudicated where required, and frozen before `_KEY_belief1.json` was opened.

- PACK_A: preregistered P5 coding.
- PACK_B: explicitly post-hoc exploratory semantic-retention coding.
- PACK_C: explicitly post-hoc exploratory round-change coding.
- The coding agents and adjudicators did not receive the key.
- The key was joined only after `PACK_A_FREEZE.json`, `PACK_B_FREEZE.json`, and `PACK_C_FREEZE.json` existed and their linked artifacts had passed structural and direct semantic checks.

AI-agent double coding is reported as cross-model agreement, not human inter-rater reliability.

## Coding design

### PACK_A

- 66 items; three requested judgments per item.
- Full independent coding by Hermes-Sol and Claude.
- Every exact requested-field disagreement was adjudicated from anonymized judgments.
- Disagreement: 66/66 items, 118 requested fields.
- Cross-model agreement:
  - q1 orientation: 59/66 (89.4%).
  - q2 political orientation: 1/66 (1.5%).
  - q3 exact belief set: 20/66 (30.3%).
- Because q2 agreement was exceptionally low, q2 descriptive results are strongly adjudicator-dependent and should not be treated as robust without a human coding round or a sharper political-orientation rubric.

### PACK_B

- 66 items × 12 facts = 792 post-hoc exploratory judgments.
- One primary coder covered all 66 items.
- A 14-card audit sample was fixed with seed `20260831` before coding and independently coded by Claude.
- Audit disagreement: 12/168 fact judgments; raw agreement 156/168 (92.9%).
- Seven audit items required blinded adjudication.
- The remaining 52 items are explicitly primary-coder-only exploratory evidence.

### PACK_C

- 33 items × three requested fields = 99 requested judgments.
- Full independent coding by Hermes-Sol and Claude.
- Claude's first output contained two supporting round values outside the listed option set (`모르겠다` at C-23 r1 and C-27 r1). The output was not accepted until the same isolated coder corrected both values and all 132 round-option values passed option-membership checks.
- Disagreement: 3/33 items and 5/99 requested fields.
- Cross-model agreement:
  - Exact item-level agreement on all requested fields: 30/33 (90.9%).
  - Requested-field agreement: 94/99 (94.9%).

## Keyed descriptive results

These are descriptive counts only. No inferential test, uncertainty interval, or causal claim is made here.

### PACK_A — preregistered P5

The key produced two 33-item groups, `C0` and `PBW`.

| Judgment | C0 | PBW |
|---|---:|---:|
| 사람 사정 먼저 | 6/33 (18.2%) | 9/33 (27.3%) |
| 정한 것 지킴 | 27/33 (81.8%) | 23/33 (69.7%) |
| 모르겠다 (q1) | 0/33 | 1/33 (3.0%) |
| 좌파 (q2) | 5/33 (15.2%) | 8/33 (24.2%) |
| 우파 (q2) | 27/33 (81.8%) | 24/33 (72.7%) |
| 모르겠다 (q2) | 1/33 (3.0%) | 1/33 (3.0%) |

Belief-number prevalence is stored in `KEYED_SUMMARY.json`. These are multi-label counts, so columns need not sum to 33.

| Belief | C0 | PBW |
|---:|---:|---:|
| 1 | 3 | 2 |
| 2 | 2 | 8 |
| 3 | 13 | 8 |
| 4 | 2 | 0 |
| 5 | 0 | 6 |
| 6 | 1 | 0 |
| 7 | 22 | 25 |
| 8 | 17 | 24 |
| 9 | 3 | 12 |
| 10 | 15 | 13 |
| 11 | 15 | 16 |
| 12 | 28 | 21 |

Interpretation guard: q2 should be regarded as provisional because independent coders agreed on only one of 66 political-orientation labels.

### PACK_B — post-hoc exploratory

- Overall retained: 255/792 (32.2%).
- `wonchik` notebooks: 80/396 (20.2%).
- `A` notebooks: 109/264 (41.3%).
- `B` notebooks: 66/132 (50.0%).

The A/B/wonchik breakdown comes from the keyed `run_id` naming convention. It is descriptive and was generated only after freeze. The unequal item counts (`33`, `22`, `11`) should be preserved in any downstream comparison.

### PACK_C — post-hoc exploratory

- Final relation maintained: 14/33 (42.4%).
- Final relation changed: 19/33 (57.6%).
- Among the 19 changed items:
  - first change at r1: 18/19 (94.7%).
  - first change at r3: 1/19 (5.3%).
  - persuasion: 13/19 (68.4%).
  - oscillation: 4/19 (21.1%).
  - uncertain type: 2/19 (10.5%).

## Verification summary

- PACK_A consensus: 66 exact IDs; schema valid; all 118 adjudication quotes exact source substrings.
- PACK_B consensus: 66 exact IDs; 792 judgments; 255 retained quotes exact; 537 rejected judgments have null evidence.
- PACK_C consensus: 33 exact IDs; 132 supporting option values belong to listed choices; 66 evidence quotes exact; relation/first-flip/null consistency passed.
- Key seed: `20260831`.
- Key SHA-256: `fc08a316d8dedce140b506eeb553c3a0a5c9b25572a1b875658d8f7a19fda68e`.

## Primary artifacts

- `PACK_A_CONSENSUS_01.json`
- `PACK_B_CONSENSUS_01.json`
- `PACK_C_CONSENSUS_01.json`
- `PACK_A_KEYED_01.json`
- `PACK_B_KEYED_01.json`
- `PACK_C_KEYED_01.json`
- `KEYED_SUMMARY.json`
- `PACK_A_FREEZE.json`
- `PACK_B_FREEZE.json`
- `PACK_C_FREEZE.json`

All paths are under `experiments/pressure_category/coderpacks_belief1/coding_20260831/`.
