"""Re-grade every stored row with the current grader and the truncation rule.

Grading lives in grade_gen / grade_asym and has been tightened twice since the runs started: the
parser now reads the last complete design block in an answer, and a truncated answer is never
given a substantive grade. This applies both to the saved rows, so the results on disk always
match the audited grader, and records the grade each row was written with in class_asrun."""
import glob, json, os, sys, collections
import grade_gen, grade_asym, repair_cot

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = "results_gpu" if os.path.isdir(os.path.join(HERE, "results_gpu")) else "results_open"
DATASETS = ("dataset", "dataset_scaled", "dataset_asym")
KEYS = {}


def grade_meta(iid, rendering):
    k = (iid, rendering)
    if k not in KEYS:
        d = next(d for d in DATASETS if os.path.exists(os.path.join(HERE, d, iid, "answer_key.json")))
        KEYS[k] = json.load(open(os.path.join(HERE, d, iid, "answer_key.json")))["renderings"][rendering]["grade_meta"]
    return KEYS[k]


def main(paths=None):
    paths = paths or sorted(glob.glob(os.path.join(HERE, RESULTS, "*.jsonl")))
    paths = [p for p in paths if os.path.basename(p).split("_")[0] in ("local", "cot", "scaled", "asym", "local18k")]
    repair_cot.main([p for p in paths if os.path.basename(p).startswith("cot_")])
    changed = collections.Counter(); total = 0
    for p in paths:
        rows = [json.loads(l) for l in open(p) if l.strip()]
        dirty = False
        for r in rows:
            gm = grade_meta(r["instance"], r["rendering"])
            grader = grade_asym.classify if r["instance"].startswith("asym") else grade_gen.classify
            cls = grader(gm, r["answer"])
            if r.get("finish") not in (None, "stop"):
                cls = "INVALID"
            total += 1
            if cls != r["class"]:
                r.setdefault("class_asrun", r["class"]); changed[(r["class"], cls)] += 1
                r["class"] = cls; dirty = True
        if dirty:
            with open(p, "w") as f:
                for r in rows:
                    f.write(json.dumps(r) + "\n")
    print(f"regrade: {total} rows, {sum(changed.values())} changed")
    for (a, b), n in changed.most_common():
        print(f"  {a} -> {b}: {n}")
    return changed


if __name__ == "__main__":
    main(sys.argv[1:] or None)
