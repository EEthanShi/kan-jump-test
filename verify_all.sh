#!/bin/bash
# Rebuild and re-check everything from the saved data. Calls no model and needs no GPU.
set -e
cd "$(dirname "$0")"
# regrade first: a fresh pull from the box brings rows graded by the runner as it stood at run time
echo "== re-grade saved rows with the current grader =="; python3 regrade.py
echo "== certification and grader, base family =="; python3 tests.py | tail -2
echo "== grader, asymmetric family ==";            python3 tests_asym.py | tail -2
echo "== scratchpad extraction and stored rows =="; python3 tests_cot.py | tail -3
echo "== figures and tables =="; python3 viz.py | tail -2
echo "== results document =="; python3 make_report.py
echo "== done: figures/ and results_gpu/RESULTS_open.md are current =="
