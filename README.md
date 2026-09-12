# kan-jump-test

A certified, reproducible test of whether a language model can abandon its
canonical completion when explicitly stated constraints rule it out.
Companion code for the paper *When the Canonical Completion Is Wrong:
Formalizing and Measuring the Jump in Language Models*.

The test hands a model a finite category as explicit tables, a functor on an
observed subcategory, and a list of machine-checkable constraints. Every
instance carries a certificate that a correct completion exists, is unique up
to renaming of invented elements, and differs from both the left and right Kan
extensions of the data. Three certified families are released, the nine pointed-chain instances of the
first experiment, 180 scaled instances that carry the chance level down to
$6.1\times10^{-10}$, and 70 asymmetric instances on which the left and right Kan
extensions differ. The headline metric is the **Kan-default rate (KD)**,
the share of constrained answers that remain at the excluded canonical
default. Calibration and matched control instances make the measurement
attributable: KD is read only against each model's measured unconstrained
default, and controls separate default lock-in from failure to extend at all.

The certification, the grading, the datasets and every figure run on the Python
standard library, with `numpy`, `pandas` and `matplotlib` for the figures; serving
an open-weight model locally needs `vllm`.

PS: I am kind of a beginner to category theory; if you spot anything wrong, I am very happy to discuss with you to improve the paper :).


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

Rebuild every figure, table and number of the paper from the released rows, with
no model call and no GPU:

```bash
./verify_all.sh
```

Serve an open-weight model locally and evaluate it, or score the two candidate
answers by teacher forcing:

```bash
KJ_API_BASE=http://localhost:8000/v1 python3 run_gen.py --instances m1_p2 --models Qwen/Qwen3-8B
python3 score_logprob.py --model Qwen/Qwen3-8B --instances m1_p2 --out results_open/logprob_demo.jsonl
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
| `engine_asym.py` | the asymmetric family, where the left and right Kan extensions differ, with its own certification |
| `render_asym.py` | renderings for the asymmetric family |
| `grade_asym.py` | grader for the asymmetric family (ADM / LAN / RAN / VALID_OTHER / RULE_VIOL / INVALID) |
| `make_dataset_scaled.py` | reseeds the pointed-chain generator into 180 instances over eighteen configurations |
| `make_dataset_asym.py` | builds the 70 asymmetric instances over seven certified configurations |
| `search_asym_configs.py` | searches for further certified asymmetric configurations |
| `score_logprob.py` | teacher-forced log probabilities of the canonical and admissible answers, served locally with vLLM |
| `regrade.py` | re-grades saved rows under the current grader and the truncation rule |
| `repair_cot.py` | re-extracts the design block of the scratchpad arm from the stored raw text |
| `make_release_results.py` | writes `results_open/` from the raw logs |
| `viz.py`, `figstyle.py` | every figure in the paper, rebuilt from the saved rows |
| `make_report.py` | rebuilds `RESULTS_open.md` from the saved rows |
| `verify_all.sh` | re-grades, runs the three test suites, and rebuilds every figure and table |
| `tests.py`, `tests_asym.py`, `tests_cot.py` | end-to-end certification, grader audits, and scratchpad regression tests |
| `dataset/` | the nine certified instances used in the paper |
| `dataset_scaled/` | the 180 scaled instances |
| `dataset_asym/` | the 70 asymmetric instances |
| `seed/` | the original hand-certified seed instance and its prompt |
| `results/` | raw graded answers from the four models reached through an API |
| `results_open/` | graded answers from the ten open-weight models, with the log-probability scores |
| `figures/` | the figures of the paper, as vector PDF and as PNG |

## Integrity notes

Reasoning-budget truncation biases answers toward the shortest completion,
which is the default, so a truncated answer is graded as a format failure and
counts as neither a jump nor a reversion. The budget itself is measured: the
same four models were rerun at 18,000 tokens, and `results_open/local18k_*`
carries that arm. Provider content filters differ across model tiers and are
screened before any refusal is read. Three Gemma 4 checkpoints are absent
because the serving stack failed to build their kernels, which is recorded in
the paper rather than passed over.

`results_open/` is the release copy written by `make_release_results.py`. Every
field a number depends on is kept, an answer that finished cleanly is stored in
full, and the stored text of an answer cut off at the budget is capped at 2,000
characters. Re-grading the release copy reproduces all 30,304 stored grades.

## License

MIT. See `LICENSE`.

