#!/usr/bin/env python3
"""tests.py -- full test run for generator_v1.

Runs: category-table validity, the mandatory anchor test, constructive-vs-
naive enumeration cross-checks, Kan unit/counit checks (asserted inside
lan/ran), the theorem-path validation (closed-form |Ext_N| / |Adm| /
non-pinning alive counts vs full enumeration on all six m<=2 configs and on
(3,(2,2,2),4)), all dataset certifications, render hygiene, grader
self-tests and grader round-trips (generated admissible / gauge-renamed /
Kan / rule-violating / junk answers for every instance and rendering,
including theorem-planted m=3 tables).
"""
import sys
import time

import engine
import render
import grade_gen
import make_dataset

ALL_CONFIGS = make_dataset.CONFIGS + make_dataset.M3_CONFIGS

FAILURES = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f"  ({detail})" if detail else ""))
    if not cond:
        FAILURES.append(name)
    return cond


def test_category_tables():
    print("\n== category / C0 / F0 table validity (all 9 configs) ==")
    for m, ps in ALL_CONFIGS:
        inst = engine.build_family(m, ps)
        ok = (engine.verify_category(inst) and engine.verify_C0_full(inst)
              and engine.verify_F0(inst))
        n_mor = len(inst['mors'])
        check(f"tables valid m={m} ps={ps}", ok, f"|mor C| = {n_mor}")


def test_anchor():
    print("\n== ANCHOR TEST: build_family(1, [2]) vs certified seed ==")
    inst = engine.build_family(1, [2])
    rep = engine.certify(inst)
    check("|Ext_4| = 25", rep['ext_count'] == 25, str(rep['ext_count']))
    check("|Adm| = 3", rep['adm_count'] == 3, str(rep['adm_count']))
    check("chance = 0.12", abs(rep['chance'] - 0.12) < 1e-12,
          f"{rep['chance']:.4f}")
    check("Lan* = Ran* = trivial", rep['lan_eq_ran'] and rep['kan_trivial'],
          f"lan_sizes={rep['lan_sizes']}")
    check("seed certified (J1-J4)", rep['certified'])
    check("seed non-pinning >= 10% per constraint", rep['non_pinning_ok'],
          str({k: round(v['fraction'], 3)
               for k, v in rep['non_pinning'].items()}))


def test_enumeration_cross_checks():
    print("\n== constructive vs naive enumeration cross-checks ==")
    cases = [((1, (2,)), 4), ((1, (3,)), 4), ((2, (2, 2)), 3),
             ((2, (2, 3)), 3)]
    for (m, ps), cap in cases:
        inst = engine.build_family(m, ps)
        fast = {engine.frz(F) for F in engine.enumerate_ext(inst, cap=cap)}
        naive = {engine.frz(F) for F in engine.enumerate_ext_naive(inst, cap)}
        check(f"enumerations agree m={m} ps={ps} cap={cap}",
              fast == naive, f"|Ext_cap| = {len(fast)} vs {len(naive)}")


def test_kan():
    print("\n== Kan extensions (comma formulas, unit/counit, strictness) ==")
    for m, ps in ALL_CONFIGS:
        inst = engine.build_family(m, ps)
        Lan, lsz = engine.lan_strict(inst)     # unit bijectivity asserted inside
        Ran, rsz = engine.ran_strict(inst)     # counit bijectivity asserted
        ok = (engine.is_functor(inst, Lan) and engine.is_functor(inst, Ran)
              and engine.restricts_to_F0(inst, Lan)
              and engine.restricts_to_F0(inst, Ran)
              and all(lsz[o] == 1 and rsz[o] == 1
                      for o in inst['new_objects'])
              and Lan == Ran)
        check(f"Lan*/Ran* strict, trivial, equal m={m} ps={ps}", ok)


def test_closed_form():
    """MANDATORY theorem-path validation: Proposition F7's closed form and
    the theorem count/fraction fields against full enumeration."""
    print("\n== THEOREM PATH: closed form vs enumeration (6 configs) ==")
    for m, ps in make_dataset.CONFIGS:
        inst = engine.build_family(
            m, ps, N=make_dataset.N_OVERRIDE.get((m, tuple(ps))))
        N = inst['N']
        ext = engine.enumerate_ext(inst)
        cf = engine.ext_count_closed_form(m, tuple(ps), N)
        check(f"closed-form |Ext_{N}| == enumerated m={m} ps={ps}",
              cf == len(ext), f"{cf} vs {len(ext)}")
        adm = engine.compute_adm(inst, ext)
        at = engine.adm_count_theorem(ps)
        check(f"adm_count_theorem == enumerated |Adm| m={m} ps={ps}",
              at == len(adm), f"{at} vs {len(adm)}")
        alive_cf = engine.alive_counts_closed_form(m, tuple(ps), N)
        for c in inst['constraints']:
            alive_enum = sum(1 for F in ext if c['pred'](F))
            check(f"closed-form alive == enumerated {c['name']} "
                  f"m={m} ps={ps}", alive_cf[c['name']] == alive_enum,
                  f"{alive_cf[c['name']]} vs {alive_enum}")
        # both certification modes must agree on every shared numeric field
        rep_e = engine.certify(inst, ext=ext)
        rep_t = engine.certify_by_theorem(inst)
        fields = ['ext_count', 'adm_count', 'chance', 'lan_eq_ran',
                  'kan_trivial', 'kan_violations', 'non_pinning',
                  'non_pinning_ok', 'certified']
        diff = [f for f in fields if rep_e[f] != rep_t[f]]
        check(f"certify vs certify_by_theorem agree m={m} ps={ps}",
              not diff, f"diverging fields: {diff}" if diff else "")
        check(f"theorem planted witness in enumerated Adm m={m} ps={ps}",
              engine.frz(rep_t['_adm_rep']) in {engine.frz(F) for F in adm})

    print("\n== THEOREM PATH: the (3,(2,2,2),4) confirmation ==")
    # One big enumeration (~40 s incl. the per-table functor check) confirms
    # the closed form and the independent verifier's constant 1,257,409.
    inst3 = engine.build_family(3, (2, 2, 2), 4)
    t0 = time.time()
    ext3 = engine.enumerate_ext(inst3)
    dt = time.time() - t0
    check("enumerated |Ext_4(3,(2,2,2))| == 1257409",
          len(ext3) == 1257409, f"{len(ext3)} ({dt:.0f}s)")
    check("closed-form |Ext_4(3,(2,2,2))| == 1257409",
          engine.ext_count_closed_form(3, (2, 2, 2), 4) == 1257409)
    adm3 = engine.compute_adm(inst3, ext3)
    check("enumerated |Adm| == adm_count_theorem == 27",
          len(adm3) == 27 == engine.adm_count_theorem((2, 2, 2)),
          str(len(adm3)))
    alive_cf3 = engine.alive_counts_closed_form(3, (2, 2, 2), 4)
    for c in inst3['constraints']:
        alive_enum = sum(1 for F in ext3 if c['pred'](F))
        check(f"closed-form alive == enumerated {c['name']} (3,(2,2,2),4)",
              alive_cf3[c['name']] == alive_enum,
              f"{alive_cf3[c['name']]} vs {alive_enum}")
    planted3 = engine.build_planted(inst3)
    check("planted m=3 witness in enumerated Adm",
          engine.frz(planted3) in {engine.frz(F) for F in adm3})


def test_dataset():
    print("\n== dataset generation + certification ==")
    summary = make_dataset.main(verbose=True)
    shipped = [r for r in summary if not r.get('skipped')]
    check("all 9 configs shipped", len(shipped) == 9,
          f"{len(shipped)}/9 shipped")
    for r in shipped:
        check(f"{r['id']} certified", r['certified'])
        check(f"{r['id']} control certified", r['control_certified'])
    modes = {r['id']: r['certification_mode'] for r in shipped}
    check("m<=2 configs enumeration-certified, m=3 theorem-certified",
          all(v == ('theorem' if k.startswith('m3') else 'enumeration')
              for k, v in modes.items()), str(modes))
    return summary


def test_render_hygiene():
    print("\n== render hygiene (risky words, format-matched variants) ==")
    for m, ps in ALL_CONFIGS:
        inst = engine.build_family(m, ps)
        for rd in render.RENDERINGS:
            naming = render.make_naming(inst, rd)
            texts = {}
            for variant in render.VARIANTS:
                text, _ = render.render(inst, rd, variant, naming=naming)
                texts[variant] = text
                bad = [w for w in render.RISKY_WORDS if w in text.lower()]
                if bad:
                    check(f"no risky words m={m} ps={ps} {rd} {variant}",
                          False, str(bad))
            lens = {v: len(t.splitlines()) for v, t in texts.items()}
            check(f"variants format-matched m={m} ps={ps} {rd}",
                  len(set(lens.values())) == 1, f"line counts {lens}")
    print("  [PASS] no risky words in any rendered prompt")


def test_grader():
    print("\n== grader self-tests (hand-written answers, m=1, m=2, m=3) ==")
    ok = grade_gen.self_test()
    check("grader self-tests", ok)

    print("\n== grader round-trips on generated instances ==")
    # m <= 2 via enumeration-certified reports, m = 3 via the theorem path
    # (rep['_adm_rep'] is then the theorem-constructed planted table).
    jobs = ([(m, ps, engine.certify) for m, ps in make_dataset.CONFIGS]
            + [(m, ps, engine.certify_by_theorem)
               for m, ps in make_dataset.M3_CONFIGS])
    for m, ps, certifier in jobs:
        N = (make_dataset.choose_N_theorem(m, ps)
             if certifier is engine.certify_by_theorem else None)
        inst = engine.build_family(m, ps, N=N)
        rep = certifier(inst)
        adm0, lan = rep['_adm_rep'], rep['_lan']
        # a nontrivial gauge renaming of adm0 (cyclic shift at each station)
        sigma = {}
        for o in inst['new_objects']:
            n = adm0[f'id_{o}'][0]
            sigma[o] = tuple((j + 1) % n for j in range(n))
        adm0_renamed = engine.apply_gauge(inst, adm0, sigma)
        assert engine.adm_structure_ok(inst, adm0_renamed)
        for rd in render.RENDERINGS:
            naming = render.make_naming(inst, rd)
            meta = grade_gen.make_grade_meta(inst, naming)
            got = {
                'adm': grade_gen.classify(
                    meta, render.answer_text(inst, naming, adm0)),
                'adm_renamed': grade_gen.classify(
                    meta, render.answer_text(inst, naming, adm0_renamed)),
                'kan': grade_gen.classify(
                    meta, render.answer_text(inst, naming, lan)),
                'junk': grade_gen.classify(meta, "no idea, sorry"),
            }
            want = {'adm': 'ADM', 'adm_renamed': 'ADM', 'kan': 'KAN',
                    'junk': 'INVALID'}
            check(f"round-trip m={m} ps={ps} {rd}", got == want,
                  str(got) if got != want else "ADM/ADM/KAN/INVALID")
            check(f"verdicts m={m} ps={ps} {rd}",
                  grade_gen.verdict('jump', got['adm']) == 'PASS'
                  and grade_gen.verdict('control', got['kan']) == 'PASS'
                  and grade_gen.verdict('jump', got['kan']) == 'FAIL')


def test_grader_exhaustive():
    """For every enumerated extension of every enumeration-certified (m<=2)
    instance, under both renderings, the grader must return ADM exactly on
    the admissible tables, KAN exactly on the trivial (all-singleton)
    extension, and VALID_OTHER on everything else; RULE_VIOL/INVALID must
    never occur on a genuine member of Ext_N. This is the check the paper
    cites (138,691 extensions across the six released m<=2 instances)."""
    print("\n== exhaustive grader-vs-enumeration check (m<=2, both renderings) ==")
    total = 0
    for m, ps in make_dataset.CONFIGS:
        N = make_dataset.N_OVERRIDE.get((m, tuple(ps)))
        inst = engine.build_family(m, ps, N=N)
        ext = engine.enumerate_ext(inst)
        total += len(ext)
        for rd in render.RENDERINGS:
            naming = render.make_naming(inst, rd)
            meta = grade_gen.make_grade_meta(inst, naming)
            mism = 0
            for F in ext:
                adm = engine.adm_structure_ok(inst, F)
                triv = all(F[f'id_b{i}'][0] == 1 for i in range(1, m + 1))
                want = 'ADM' if adm else ('KAN' if triv else 'VALID_OTHER')
                got = grade_gen.classify(meta, render.answer_text(inst, naming, F))
                if got != want:
                    mism += 1
            check(f"grader == certified membership m={m} ps={ps} {rd} "
                  f"({len(ext)} extensions)", mism == 0, f"{mism} mismatches")
    check("total enumerated extensions over the six m<=2 instances",
          total == 138691, str(total))

def print_summary_table(summary):
    print("\n" + "=" * 78)
    print("DATASET SUMMARY")
    print("=" * 78)
    hdr = (f"{'id':10s} {'m':>2s} {'ps':10s} {'N':>2s} {'|Ext_N|':>10s} "
           f"{'|Adm|':>6s} {'chance':>9s} {'mode':>6s} {'cert':>5s} "
           f"{'ctrl':>5s} {'headline':>8s}")
    print(hdr)
    print("-" * len(hdr))
    for r in summary:
        if r.get('skipped'):
            print(f"{r['id']:10s} SKIPPED: {r['reason']}")
            continue
        ch = (f"{r['chance']:9.5f}" if r['chance'] >= 1e-4
              else f"{r['chance']:9.2e}")
        mode = 'thm' if r['certification_mode'] == 'theorem' else 'enum'
        print(f"{r['id']:10s} {r['m']:2d} {str(tuple(r['ps'])):10s} "
              f"{r['N']:2d} {r['ext_count']:10d} {r['adm_count']:6d} "
              f"{ch} {mode:>6s} {str(r['certified']):>5s} "
              f"{str(r['control_certified']):>5s} "
              f"{str(r['headline']):>8s}")
    print("\nper-constraint non-pinning fractions (floor 0.10):")
    for r in summary:
        if not r.get('skipped'):
            print(f"  {r['id']:10s} {r['non_pinning']}")


def main():
    t0 = time.time()
    print("=" * 78)
    print("GENERATOR v1 TEST RUN (family: pointed chain with cyclic symmetries)")
    print("=" * 78)
    test_category_tables()
    test_anchor()
    test_enumeration_cross_checks()
    test_kan()
    test_closed_form()
    summary = test_dataset()
    test_render_hygiene()
    test_grader()
    test_grader_exhaustive()
    print_summary_table(summary)
    print("\n" + "=" * 78)
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} FAILURE(S): {FAILURES}")
    else:
        print("RESULT: ALL TESTS GREEN")
    print(f"total time: {time.time() - t0:.1f}s")
    print("=" * 78)
    return 0 if not FAILURES else 1


if __name__ == '__main__':
    sys.exit(main())
