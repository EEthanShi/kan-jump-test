"""Exhaustive audit of the asymmetric-family grader against the certification engine.
For every certified configuration and both renderings: every enumerated extension is rendered as an
answer and graded; the grade must agree with the engine's membership (Lan / Ran / admissible class /
other). Rule-violating and malformed answers are also checked."""
import itertools, time
import engine_asym as ea, render_asym as ra, grade_asym as ga

# exhaustive where enumeration is small, a deterministic sample where it is not
CONFIGS = [(2, 1, 4), (3, 1, 5), (1, 2, 3), (2, 2, 4), (3, 2, 5), (4, 1, 6), (5, 1, 7)]
MAX_EXHAUSTIVE = 8000


def expected(inst, F, Lan, Ran, Adm0):
    if inst.gauge_equiv(F, Lan): return "LAN"
    if inst.gauge_equiv(F, Ran): return "RAN"
    if inst.gauge_equiv(F, Adm0): return "ADM"
    return "VALID_OTHER"


def main():
    t0 = time.time(); total = 0; fails = 0
    for (k, l, N) in CONFIGS:
        inst = ea.Inst(k, l, N); rep = inst.certify(); assert rep["certified"]
        Lan, Ran, Adm0 = rep["_Lan"], rep["_Ran"], rep["_Adm"][0]
        exts = inst.enumerate_ext(N)
        if len(exts) > MAX_EXHAUSTIVE:                      # deterministic stride, no randomness
            stride = len(exts) // MAX_EXHAUSTIVE + 1
            print(f"  ({k},{l},{N}): {len(exts)} extensions, auditing every {stride}th")
            exts = exts[::stride]
        for rd in ra.render.RENDERINGS:
            nm = ra.make_naming(k, l, rd, seed_tag="audit"); meta = ga.make_grade_meta(k, l, N, nm)
            bad = 0; cnt = {"LAN": 0, "RAN": 0, "ADM": 0, "VALID_OTHER": 0}
            for F in exts:
                got = ga.classify(meta, ra.answer_text(nm, F)); exp = expected(inst, F, Lan, Ran, Adm0); cnt[exp] += 1
                if got != exp: bad += 1; print(f"  MISMATCH {(k,l,N)} {rd} expected {exp} got {got}: F={F}") if bad <= 3 else None
            # rule-violating tables: break R1.3 (endo not an involution) on the admissible answer when |Q| >= 3
            n = Adm0["idb"][0]
            if n >= 3:
                txt = ra.answer_text(nm, Adm0); e = nm["endo_moves"][0]
                import re
                m = re.search(re.escape(e) + r"\s*:\s*([^\n]*)", txt); line = m.group(1)
                pairs = [p.strip() for p in line.split(",")]
                # rewrite the endo table so that q0 -> q1, q1 -> q2 (a 3-cycle piece) : not an involution
                names = [p.split("->")[0].strip() for p in pairs]
                new = ", ".join(f"{names[i]} -> {names[(i + 1) % n]}" for i in range(n))
                got = ga.classify(meta, txt.replace(line, new))
                if got != "RULE_VIOL": bad += 1; print(f"  MISMATCH rule-violation probe {(k,l,N)} {rd}: got {got}")
            # too many middle units -> INVALID
            got = ga.classify(meta, ra.answer_text(nm, Adm0).replace("}", ", zzz1, zzz2, zzz3, zzz4, zzz5}", 1))
            if got != "INVALID": bad += 1; print(f"  MISMATCH oversize probe {(k,l,N)} {rd}: got {got}")
            total += len(exts) + 2; fails += bad
            print(f"[{'PASS' if bad == 0 else 'FAIL'}] ({k},{l},{N}) {rd}: {len(exts)} extensions {cnt}, probes ok={bad == 0}")
    print(f"{total} checks, {fails} failures, {time.time() - t0:.1f}s")
    assert fails == 0


if __name__ == "__main__":
    main()
