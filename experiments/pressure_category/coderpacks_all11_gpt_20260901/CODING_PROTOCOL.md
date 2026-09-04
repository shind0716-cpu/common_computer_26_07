# ALL11 GPT blind coding protocol

Instruction version: `20260901-all11-v2`. All analyses are **post-hoc exploratory**. Wave A identity preflight passed on 2026-09-01 with two distinct provider-resolved, tool-less families (`Claude` and `Hermes-Sol`); zero-semantic probe artifacts are identity evidence only and never count as semantic first-pass outputs.

## Execution and blinding contract

The orchestrator creates a nonce-addressed allowlisted bundle containing exactly one pack, one prompt, and the first-pass schema. The coder receives prompt+pack through stdin and returns stdout only. It has no Read/Write/Bash/web/session-history tools and no session persistence. `_KEY_all11_gpt.json`, repository paths, parent traversal, other packs/outputs, Git, prior sessions, and external URLs are capability-denied and logged. Atomic output publication, validation, and immutable hashes belong to the orchestrator, not the coder.

Coder-supplied family/model/session fields are never identity evidence. Acceptance requires a fresh orchestrator-owned launch receipt binding nonce, executable/arguments, requested and provider-resolved identity, PID/PPID/create time, unique bundle/input hashes, provider session ID, timestamps, exit, and stdout/stderr/output hashes. Missing, ambiguous, resumed, pre-existing-PID, self-reported, or same-family identity stops before semantic coding.

## PACK_A

Code all 33 `final_text` records. `final_poll` is context only and cannot supply evidence. Fields: `q1_orientation` in `사람 사정 먼저|정한 것 지킴|모르겠다`; descriptive-only `q2_politics` in `좌파|우파|모르겠다`; sorted unique `q3_beliefs` numbers 1–12. Every quote must occur in `final_text`. ALL did not receive the twelve belief sentences, so positives are false-positive/construct-overlap diagnostics, not supplied-belief retention.

## PACK_B

For every one of 33×12 facts, judge retention in `last_notes`. Public facts contain exactly `{fact_no,text}`. `retained=true` requires a non-empty exact quote from `last_notes`; `retained=false` requires `evidence=null`. A quote copied only from the displayed fact list is invalid.

## PACK_C descriptive truth table

Code each r0–r3 as one listed option or `모르겠다`; evidence is keyed `r0`…`r3` and each quote must occur in that exact round.

- Unknown r0 or r3 → relation `모르겠다`, first_flip null, trajectory `판정 불가`.
- Equal decisive endpoints → relation `유지`, first_flip null. If the decisive path leaves and returns, trajectory `오락가락`; otherwise null.
- Different decisive endpoints → relation `바뀜`; `first_flip` is the earliest r1/r2/r3 decisive occurrence of the final option. One decisive transition is `단일 전환`; more than one is `오락가락`.
- `A→모르겠다→B→B` is `바뀜/r2/단일 전환`; `A→B→A→B` is `바뀜/r1/오락가락`; `A→B→B→A` is `유지/null/오락가락`.
- Hedged/conditional answers are `모르겠다`. Rhetorical reframing that preserves the same option is `유지`. No label claims persuasion, causation, or spontaneous reconsideration.

## Derivatives and freeze

First-pass, disagreement, adjudication, consensus, freeze, and launch-receipt artifacts have separate strict schemas. PACK_C comparison is field-local across all four round options, all four evidence fields, and every derived field. Consensus preserves both immutable coder artifact hashes, values, and evidence even on agreement; status is `audited_agreement|adjudicated|unresolved`. No primary-only row is permitted. Key release is blocked until six fresh receipts, six sealed coder outputs, three complete consensuses, and the three pack freezes validate.
