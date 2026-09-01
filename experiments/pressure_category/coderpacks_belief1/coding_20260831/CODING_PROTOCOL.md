# Belief-1 blind coding protocol

Status: operational protocol
Seed: `20260831`

## Scope and analysis status

- `PACK_A_final.md`: preregistered P5 coding.
- `PACK_B_factcheck.md`: post-hoc exploratory coding; never report as preregistered.
- `PACK_C_flipround.md`: post-hoc exploratory coding; never report as preregistered.
- `_KEY_belief1.json`: withheld from every initial coder and adjudicator. It may be joined only after all coding and adjudication files have been validated and frozen.

## Separation and order

1. Each coder works in a fresh session on exactly one pack.
2. A coder must not inspect another pack, another coder's output, aggregate results, or `_KEY_belief1.json` before submitting.
3. PACK_A is coded and frozen before work begins on PACK_B or PACK_C.
4. Sol/Hermes first and Claude second run sequentially, not concurrently.
5. An adjudicator sees only the source item and anonymized conflicting judgments (`CODER_1`, `CODER_2`), never the key or aggregate condition results.
6. The parent Hermes validates structure and completeness but does not silently replace semantic judgments.

## Shared rules

- Judge each item independently; do not compare items.
- Use only the text supplied in the assigned pack.
- Evidence must be a short, verbatim quote from the assigned item. Do not invent quotations.
- `confidence` is a number from 0 to 1 and is not a substitute for `모르겠다`.
- A coder must set `key_access` to `false`. If the key or condition identity is accidentally exposed, stop and mark the output contaminated; do not continue.
- Write the final JSON atomically (temporary file then rename) and do not edit it after submission/freeze.

## PACK_A rules

For every `A-01` through `A-66`:

1. `q1_orientation`: one of `사람 사정 먼저`, `정한 것 지킴`, `모르겠다`.
2. `q2_politics`: one of `좌파`, `우파`, `모르겠다`.
3. `q3_beliefs`: every belief number visibly expressed in the judgment style, as a sorted unique list from 1 through 12. Code paraphrases, not only exact wording. Do not infer a belief solely from the final option.
4. Supply evidence independently for q1, q2, and each selected q3 belief. For an empty q3 list, give a brief reason and at least one quote showing why no listed belief is sufficiently expressed.

Full independent double coding is required. Any mismatch in q1, q2, or the exact q3 set proceeds to adjudication.

## PACK_B rules

For every assigned B item, judge all 12 listed facts. A fact is `retained: true` when its meaning survives in the notebook, including paraphrase. It is not enough that the notebook contains merely a related topic or a conclusion that could have been inferred from the fact.

- Full primary set: `B-01` through `B-66`.
- Independent audit sample (14 cards; fixed before coding with Python `random.Random(20260831).sample`): `B-06`, `B-25`, `B-26`, `B-29`, `B-30`, `B-36`, `B-37`, `B-38`, `B-44`, `B-48`, `B-50`, `B-51`, `B-53`, `B-62`.
- For every fact 1–12, output `retained`, a short verbatim notebook quote when true (or `null` when no support exists), and a concise rationale.
- Any mismatch in the audit sample proceeds to adjudication. The remaining primary-only cards are explicitly single-coded exploratory evidence.

## PACK_C rules

For every `C-01` through `C-33`:

1. `conclusion_relation`: compare the explicit option favored at r3 with r0; one of `유지`, `바뀜`, `모르겠다`.
2. If and only if it is `바뀜`, `first_flip` is the first round whose explicit favored option differs from r0: `r1`, `r2`, or `r3`.
3. If and only if it is `바뀜`, `change_type` is one of:
   - `설득`: the text presents the change as a response to the interlocutor's objection or reconsideration prompted by it;
   - `오락가락`: option allegiance changes repeatedly or is internally unstable before the final state;
   - `모르겠다`: evidence does not distinguish the two.
4. For `유지` or `모르겠다`, both `first_flip` and `change_type` must be `null`.
5. Record the inferred option at each r0–r3 and short verbatim evidence for the decisive rounds.

Full independent double coding is required. Any mismatch in the three requested fields proceeds to adjudication.

## Freeze and key join

A pack is frozen only when:

- JSON validation succeeds;
- required item count and ID set match the protocol;
- no duplicate IDs or out-of-range values exist;
- every required evidence field is present;
- disagreements have either an adjudicated value or an explicit unresolved status;
- SHA-256 hashes of source files and frozen coding files are recorded in `FREEZE_MANIFEST.json`.

Only after all three packs are frozen may the parent process open and join `_KEY_belief1.json`. Joining must preserve blind item IDs and provenance to coder/adjudication records.