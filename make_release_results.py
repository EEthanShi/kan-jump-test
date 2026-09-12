"""Write the release copy of the graded results.

The raw logs keep every token a model produced, and most of that volume is reasoning that
was cut off at the budget. The release copy keeps every field a number in the paper depends
on, caps the stored text of an answer that was truncated at the budget, and drops the
pre-extraction text except in the scratchpad arm, where `repair_cot.py` reads it. An answer
that finished cleanly is stored in full, so re-grading the release copy reproduces every
grade.
"""
import glob, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, DST = os.path.join(HERE, "results_gpu"), os.path.join(HERE, "results_open")
CAP = 2000


def cap(row, field):
    v = row.get(field)
    if isinstance(v, str) and len(v) > CAP and row.get("finish") not in (None, "stop"):
        row[field] = v[:CAP]
        row[field + "_chars"] = len(v)


def main():
    os.makedirs(DST, exist_ok=True)
    kept = capped = 0
    for src in sorted(glob.glob(os.path.join(SRC, "*.jsonl"))):
        name = os.path.basename(src)
        with open(os.path.join(DST, name), "w") as out:
            for line in open(src):
                if not line.strip():
                    continue
                r = json.loads(line)
                before = len(r.get("answer", ""))
                if not name.startswith("cot_"):
                    r.pop("answer_raw", None)
                else:
                    cap(r, "answer_raw")
                cap(r, "answer")
                kept += 1
                capped += len(r.get("answer", "")) < before
                out.write(json.dumps(r) + "\n")
    for extra in ("MANIFEST.json", "RESULTS_open.md"):
        p = os.path.join(SRC, extra)
        if os.path.exists(p):
            open(os.path.join(DST, extra), "w").write(open(p).read())
    size = sum(os.path.getsize(os.path.join(DST, f)) for f in os.listdir(DST))
    print(f"{kept} rows written to results_open, {capped} answers capped at {CAP} characters, {size/1e6:.1f} MB")


if __name__ == "__main__":
    main()
