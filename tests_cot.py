"""Regression tests for the scratchpad arm: prompt rewriting, answer extraction, repair.

The first version of the extraction took everything after the last "FINAL DESIGN" and lost the
design block whenever a model wrote the block first and the words afterwards. These tests pin the
behaviour on the shapes seen in the runs, including that one."""
import json, glob, os
import grade_gen, run_gen

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = "results_gpu" if os.path.isdir(os.path.join(HERE, "results_gpu")) else "results_open"
KEY = json.load(open(os.path.join(HERE, "dataset", "m2_p22", "answer_key.json")))["renderings"]["factory"]
BLOCK = KEY["example_admissible_answer"]
KAN = KEY["kan_answer"]
GM = KEY["grade_meta"]


def case(name, text, want_class, want_block=None):
    """The grade is what matters; the extracted text only has to end with the intended block,
    since surrounding prose is harmless once the grader reads the last complete design."""
    got = run_gen.extract_final(text)
    cls = grade_gen.classify(GM, got)
    ok = cls == want_class and (want_block is None or got.strip().endswith(want_block.strip()))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: class={cls}")
    assert ok, f"{name}: got class {cls}\n---\n{got[:400]}"


def main():
    case("block after the marker", f"thinking...\nFINAL DESIGN\n{BLOCK}", "ADM", BLOCK)
    case("marker decorated", f"reasoning\n**FINAL DESIGN:**\n{BLOCK}", "ADM", BLOCK)
    case("block before the marker", f"reasoning\n\n{BLOCK}\nFINAL DESIGN", "ADM", BLOCK)
    case("draft, then marker, then block", f"draft:\n{KAN}\nthat breaks D1.2.\nFINAL DESIGN\n{BLOCK}", "ADM", BLOCK)
    case("draft and block in one segment, marker last",
         f"draft:\n\n{KAN}\n\nthat breaks D1.2, so instead:\n\n{BLOCK}\n\nFINAL DESIGN", "ADM", BLOCK)
    case("no marker, draft then block", f"draft:\n\n{KAN}\n\nbetter:\n\n{BLOCK}", "ADM", BLOCK)
    case("marker written twice, block after the second", f"FINAL DESIGN\n{KAN}\nno wait\nFINAL DESIGN\n{BLOCK}", "ADM", BLOCK)
    case("no marker at all", BLOCK, "ADM", BLOCK)
    case("marker but no table anywhere", "FINAL DESIGN\nI cannot solve this.", "INVALID")
    case("kan answer after the marker", f"FINAL DESIGN\n{KAN}", "KAN", KAN)

    # every stored scratchpad row must re-extract to exactly what was graded
    rows = [json.loads(l) for f in glob.glob(os.path.join(HERE, RESULTS, "cot_*.jsonl")) for l in open(f)]
    bad = 0
    for r in rows:
        raw = r.get("answer_raw", r["answer"])
        ans = raw.split("</think>")[-1].strip() if "</think>" in raw else raw
        if run_gen.extract_final(ans).strip() != r["answer"].strip():
            bad += 1
    print(f"[{'PASS' if bad == 0 else 'FAIL'}] {len(rows)} stored scratchpad rows re-extract to their graded answer ({bad} mismatches)")
    assert bad == 0
    graded_truncated = [r for r in rows if r.get("finish") not in (None, "stop") and r["class"] != "INVALID"]
    print(f"[{'PASS' if not graded_truncated else 'FAIL'}] no truncated row carries a substantive grade ({len(graded_truncated)} found)")
    assert not graded_truncated
    empty = [r for r in rows if not r["answer"].strip() and r["finish"] == "stop"]
    print(f"[{'PASS' if not empty else 'FAIL'}] no stored row is an empty answer with a clean finish ({len(empty)} found)")
    assert not empty
    print(f"{len(rows)} rows checked, all tests passed")


if __name__ == "__main__":
    main()
