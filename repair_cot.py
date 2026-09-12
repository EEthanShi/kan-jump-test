"""Re-extract and re-grade CoT rows whose design block was lost by the first FINAL DESIGN rule.

Early CoT runs took everything after the last "FINAL DESIGN"; models that wrote the block first
and the words afterwards were left with an empty answer and graded INVALID. This rewrites those
rows in place using run_gen.extract_final, keeping the original grade in class_preextract.
Idempotent: a row is rewritten only when the current rule extracts a different answer, and the
grade the row was first written with is kept in class_preextract."""
import glob, json, os, sys
import grade_gen, grade_asym, run_gen

HERE = os.path.dirname(os.path.abspath(__file__))
KEYS = {}


def grade_meta(iid, rendering, dataset_dir):
    k = (iid, rendering)
    if k not in KEYS:
        KEYS[k] = json.load(open(os.path.join(HERE, dataset_dir, iid, "answer_key.json")))["renderings"][rendering]["grade_meta"]
    return KEYS[k]


def main(paths):
    changed = files = 0
    for p in paths:
        rows = [json.loads(l) for l in open(p) if l.strip()]
        dirty = False
        for r in rows:
            if not r.get("cot"):
                continue
            raw = r.get("answer_raw", r["answer"])
            ans = raw.split("</think>")[-1].strip() if "</think>" in raw else raw
            ans = run_gen.extract_final(ans)
            if ans.strip() == r["answer"].strip():
                continue
            dd = "dataset_asym" if r["instance"].startswith("asym") else "dataset"
            gm = grade_meta(r["instance"], r["rendering"], dd)
            cls = (grade_asym if dd == "dataset_asym" else grade_gen).classify(gm, ans)
            r.setdefault("class_preextract", r["class"]); r["class"] = cls
            r["answer"], r["repaired"] = ans, True
            dirty = True; changed += 1
        if dirty:
            with open(p, "w") as f:
                for r in rows:
                    f.write(json.dumps(r) + "\n")
            files += 1
    print(f"repair_cot: {changed} rows re-extracted in {files} files")
    return changed


if __name__ == "__main__":
    main(sys.argv[1:] or glob.glob(os.path.join(HERE, "results_gpu", "cot_*.jsonl")))
