#!/bin/sh
# Re-certifies every instance, self-tests the pipeline, and reprints the
# paper's result table from the released raw data. Needs no API key.
set -e
python3 tests.py
python3 run_gen.py --report --results results/results_gen.jsonl
