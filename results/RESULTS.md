# Formal experiment results (2026-08-21, final)

9 certified instances (m = 1..3; 6 enumeration-certified, 3 theorem-certified),
4 models (GPT-5.6 Luna Pro, Claude Sonnet 5, Gemini 3.1 Pro, DeepSeek V4 Pro),
factory rendering primary + library rendering arm; 464 graded answers total;
raw data in results_gen.jsonl (+ pilot_v1/results.jsonl for the seed pilot).

## Headline numbers

- **KD = 0 / 248 jump answers across all difficulties and models.** Not one
  canonical-default answer under falsifying constraints. No canonical lock-in
  anywhere in the certified regime.
- **DC | non-truncated = 0.98**: unconstrained defaults are the Kan extension.
- **Controls 1.00** for all models except truncation-impaired DeepSeek at m=3.
- **Separation at m=3** (jump accuracy): Gemini 1.00/1.00/1.00,
  GPT 1.00/0.83/1.00, Sonnet 0.83/1.00/1.00, DeepSeek 0.83/0.33/0.33.
- **Failure composition at m=3** (72 jump answers): 61 ADM, 9 truncation,
  1 rule violation, 1 valid-but-inadmissible. Failures are search/budget
  phenomena, never default reversion.

## Reading for the debate

Within the certified regime (chance levels down to 8e-07), frontier models
always abandon the default when the stated constraints exclude it, and
increasingly fail by exhausting reasoning budget or by constraint errors as
difficulty grows. The selection step is not the bottleneck; if the "can't
jump" thesis holds, it must live in constraint genesis or codomain invention
(explicitly deferred tiers). Gemini 3.1 Pro solved all 9 instances at every
sample.

## Integrity notes carried to Appendix C

Truncation bias (reasoning-budget exhaustion masquerading as failure; DeepSeek
DC artifacts at m=3), provider content-filter tiering (Opus 5/Fable 5 refuse
all renderings; Sonnet-tier clean), rendering insensitivity confirmed on the
library arm (m1_p2: 16/16, m2_p22: 14/16).
