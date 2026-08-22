# kan-jump-test

A certified, regenerable test of whether a language model can abandon its
canonical completion when explicitly stated constraints rule it out.
Companion code for the paper *When the Canonical Completion Is Wrong:
Formalizing and Measuring the Jump in Language Models* (under review).

The test hands a model a finite category as explicit tables, a functor on an
observed subcategory, and a list of machine-checkable constraints. Every
instance carries a certificate that a correct completion exists, is unique up
to renaming of invented elements, and differs from both the left and right Kan
extensions of the data. The headline metric is the **Kan-default rate (KD)**,
the share of constrained answers that remain at the excluded canonical
default. Calibration and matched control instances make the measurement
attributable: KD is read only against each model's measured unconstrained
default, and controls separate default lock-in from failure to extend at all.

Everything runs on the Python standard library. There are no dependencies.

## Quick start

Re-certify every instance and self-test the whole pipeline (no API needed):

```bash
python3 tests.py
```

Reprint the paper's result table from the released raw data (no API needed):

```bash
python3 run_gen.py --report --results results/results_gen.jsonl
```

Evaluate a model yourself (OpenRouter key required; a smoke test costs well
under one dollar, the full paper run about five dollars):

```bash
export OPENROUTER_API_KEY=sk-or-...
python3 run_gen.py --smoke
python3 run_gen.py --report
```

Regenerate the released dataset byte for byte (default seed tag `v1`), or a
fresh, contamination-proof copy with new nonce names over the same certified
structure by choosing any other seed tag and output directory:

```bash
python3 make_dataset.py
python3 make_dataset.py --seed-tag v2 --out-dir dataset_v2
```

Nonce names are CVCV strings screened against a short blocklist; a handful
coincide with real words in some language, none related to the task.

## Layout

| Path | Content |
| --- | --- |
| `engine.py` | instance construction, exhaustive certification, pointwise Kan extensions, closed-form counts via the family theorem |
| `render.py` | natural-language renderings (factory and library cover stories) with a global nonce registry |
| `grade_gen.py` | mechanical grader (ADM / KAN / VALID_OTHER / RULE_VIOL / INVALID) |
| `make_dataset.py` | builds the nine-instance dataset with certificates |
| `run_gen.py` | evaluation harness (OpenRouter), resumable, with finish-reason logging |
| `tests.py` | end-to-end certification and self-tests |
| `dataset/` | the nine certified instances used in the paper |
| `seed/` | the original hand-certified seed instance and its prompt |
| `results/` | raw graded model answers behind every number in the paper |

## Integrity notes

Reasoning-budget truncation biases answers toward the shortest completion,
which is the default, so truncated answers are tracked separately and never
graded as jumps or reversions. Provider content filters differ across model
tiers and must be screened before any refusal is interpreted. Details are in
the paper's appendix on the experimental protocol.

## License

MIT. See `LICENSE`.
