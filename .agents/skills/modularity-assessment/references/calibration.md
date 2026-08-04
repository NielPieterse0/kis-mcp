# Calibration examples

Read only when a rubric anchor remains ambiguous. Match the reasoning, not the numbers.

| Unit | Evidence summary | Scores and result | Expected action |
|---|---|---|---|
| `shared/utils.py` | Catch-all, 2,140 LOC, fan-in 41, hidden mutable config, 6 RFC kinds, read:edit 9:1 | COH 0, CPL 1, BLR 2, RFC 0, AGT 1; MAS 20, B4; HF-2 and HF-3 | Findings `UD-1`, `UD-2`, `UD-5`; split by evidenced change kinds |
| `notifications/` | One purpose, declared interface, fan-in 3, 1 RFC kind, read:edit 2:1, isolated tests | 4, 3, 4, 4, 4; MAS 94, B1 | Preserve; `DEFER` until preferences gain an independent cadence |
| `orders/processor.py` | Order state, provider shape, and email copy; fan-in 7; 3 RFC kinds; read:edit 6:2 | 2, 0, 2, 2, 3; MAS 41, B3; HF-1 and HF-6 | Introduce a provider contract and separate notification composition |

Calibration rules:

1. Catch-all naming is evidence only when contents span unrelated responsibilities.
2. Hidden or implementation coupling overrides a superficially loose call pattern.
3. A sound unit receives `DEFER` with a trigger, not a cosmetic split.
4. Hard-fail conditions distinguish raw counts from 0-4 scores; read them literally.
