#!/usr/bin/env python3
"""make_dataset.py -- generate and certify the v1 dataset.

Configs: all (m, ps) with m in {1, 2}, p_i in {2, 3} (6 instances, certified
by full enumeration), plus the m = 3 tier M3_CONFIGS (certified by the
verified pointed-chain family theorem: closed-form |Ext_N| via Proposition
F7's transfer recursion, |Adm| = prod (1+p_i)(p_i-1)!, no enumeration;
meta.json notes certification_mode='theorem'). Per instance the dataset dir
contains:
  meta.json          params, |Ext_N|, |Adm|, chance, certification flags,
                     non-pinning statistics, control certification
  prompt_{rendering}_{variant}.txt   for rendering in {factory, library},
                     variant in {calibration, jump, control}
  answer_key.json    per-rendering grading metadata (names), structural
                     answer-key data, example admissible + Kan answer texts

An instance whose certification exceeds the time budget (600 s) is skipped
and reported; uncertified instances are never shipped.
"""
import json
import os
import time

import engine
import render
import grade_gen

CONFIGS = [(1, (2,)), (1, (3,)),
           (2, (2, 2)), (2, (2, 3)), (2, (3, 2)), (2, (3, 3))]

# m = 3 tier, shipped via the theorem-certified path (no enumeration).
M3_CONFIGS = [(3, (2, 2, 2)), (3, (2, 3, 3)), (3, (3, 3, 3))]

TIME_BUDGET_S = 600
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(HERE, 'dataset')


def inst_id(m, ps):
    return f"m{m}_p" + "".join(str(p) for p in ps)


# per-config N overrides adopted after independent verification:
# ps=(3,2) at the default N=5 fails the 10% single-constraint non-pinning
# floor on K2_2 (5.3%), while N=4 passes every floor (verified independently).
N_OVERRIDE = {(2, (3, 2)): 4}

# Seed tag for nonce-name generation. 'v1' reproduces the released dataset
# byte for byte; any other tag yields fresh names over the same certified
# structure (see --seed-tag).
SEED_TAG = 'v1'


def build_and_certify(m, ps):
    t0 = time.time()
    inst = engine.build_family(m, ps, N=N_OVERRIDE.get((m, tuple(ps))))
    ext = engine.enumerate_ext(inst)
    rep = engine.certify(inst, ext=ext)
    ctrl = engine.build_control(inst)
    crep = engine.certify_control(ctrl, ext=ext)
    elapsed = time.time() - t0
    return inst, rep, crep, elapsed


def choose_N_theorem(m, ps, floor=0.10):
    """N for a theorem-certified config: the default max(1+p_i)+1 unless the
    closed-form non-pinning floor fails there but passes at another
    admissible N (mirroring the enumerated m2_p32 override, which moved from
    the default 5 down to the minimal 4). Candidates: the default first,
    then the remaining N in [max(1+p_i), max(1+p_i)+3]. If no candidate
    passes, the default N is returned and the config ships flagged
    headline=False (like m2_p23).

    Checked for the M3_CONFIGS: (2,2,2) passes at the default N=4;
    (2,3,3) and (3,3,3) pass at no candidate N (raising N lifts the K1
    fractions but collapses the K2 fractions, and at the minimal N the
    middle-station K1 fraction is already below the floor), so both ship at
    the default N=5 with headline=False."""
    ps = tuple(ps)
    nmin = max(1 + p for p in ps)
    default = nmin + 1
    candidates = [default] + [n for n in range(nmin, nmin + 4)
                              if n != default]
    for N in candidates:
        tot = engine.ext_count_closed_form(m, ps, N)
        alive = engine.alive_counts_closed_form(m, ps, N)
        if all(a / tot >= floor for a in alive.values()):
            return N
    return default


def build_and_certify_theorem(m, ps):
    """Theorem path: no enumeration of Ext_N at any point."""
    t0 = time.time()
    inst = engine.build_family(m, ps, N=choose_N_theorem(m, ps))
    rep = engine.certify_by_theorem(inst)
    ctrl = engine.build_control(inst)
    crep = engine.certify_control_by_theorem(ctrl)
    elapsed = time.time() - t0
    return inst, rep, crep, elapsed


def anchor_check(rep):
    """The (1,(2,)) instance must reproduce the certified seed numbers."""
    return (rep['ext_count'] == 25 and rep['adm_count'] == 3
            and abs(rep['chance'] - 0.12) < 1e-12
            and rep['lan_eq_ran'] and rep['kan_trivial'])


def make_instance_dir(inst, rep, crep, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    m, ps = inst['m'], inst['ps']

    namings = {}
    answer_key = {'stations': [
        {'station': i, 'p': ps[i - 1], 'required_size': 1 + ps[i - 1],
         'structure': (f'one fixed point (= image of the constant incoming '
                       f'map) plus one {ps[i - 1]}-cycle on the remaining '
                       f'{ps[i - 1]} states; incoming map constant onto the '
                       f'fixed point; outgoing map constant on orbits')}
        for i in range(1, m + 1)],
        'renderings': {}}

    for rd in render.RENDERINGS:
        naming = render.make_naming(inst, rd, seed_tag=SEED_TAG,
                                    global_used=GLOBAL_NAME_REGISTRY)
        namings[rd] = naming
        for variant in render.VARIANTS:
            text, _ = render.render(inst, rd, variant, naming=naming)
            with open(os.path.join(out_dir, f'prompt_{rd}_{variant}.txt'),
                      'w') as f:
                f.write(text)
        answer_key['renderings'][rd] = {
            'grade_meta': grade_gen.make_grade_meta(inst, naming),
            'example_admissible_answer':
                render.answer_text(inst, naming, rep['_adm_rep']),
            'kan_answer': render.answer_text(inst, naming, rep['_lan']),
        }
    with open(os.path.join(out_dir, 'answer_key.json'), 'w') as f:
        json.dump(answer_key, f, indent=2)

    meta = {k: v for k, v in rep.items() if not k.startswith('_')}
    meta['control'] = {k: v for k, v in crep.items() if not k.startswith('_')}
    with open(os.path.join(out_dir, 'meta.json'), 'w') as f:
        json.dump(meta, f, indent=2)
    return namings


GLOBAL_NAME_REGISTRY = set()


def main(out_dir=DATASET_DIR, verbose=True):
    GLOBAL_NAME_REGISTRY.clear()
    os.makedirs(out_dir, exist_ok=True)
    summary = []
    jobs = ([(m, ps, build_and_certify) for m, ps in CONFIGS]
            + [(m, ps, build_and_certify_theorem) for m, ps in M3_CONFIGS])
    for m, ps, builder in jobs:
        iid = inst_id(m, ps)
        inst, rep, crep, elapsed = builder(m, ps)
        if elapsed > TIME_BUDGET_S:
            summary.append({'id': iid, 'skipped': True,
                            'reason': f'certification took {elapsed:.0f}s '
                                      f'> {TIME_BUDGET_S}s budget'})
            if verbose:
                print(f"[SKIP] {iid}: over time budget ({elapsed:.0f}s)")
            continue
        if (m, ps) == (1, (2,)):
            assert anchor_check(rep), "anchor instance numbers diverged"
        if not (rep['certified'] and crep['certified']):
            summary.append({'id': iid, 'skipped': True,
                            'reason': 'certification failed', 'meta': {
                                k: v for k, v in rep.items()
                                if not k.startswith('_')}})
            if verbose:
                print(f"[SKIP] {iid}: certification failed -- not shipped")
            continue
        make_instance_dir(inst, rep, crep, os.path.join(out_dir, iid))
        row = {
            'id': iid, 'skipped': False, 'm': m, 'ps': list(ps),
            'N': inst['N'], 'ext_count': rep['ext_count'],
            'adm_count': rep['adm_count'], 'chance': rep['chance'],
            'certified': rep['certified'],
            'certification_mode': rep['certification_mode'],
            'control_certified': crep['certified'],
            'non_pinning_ok': rep['non_pinning_ok'],
            'headline': bool(rep['non_pinning_ok']),
            'non_pinning': {k: round(v['fraction'], 4)
                            for k, v in rep['non_pinning'].items()},
            'seconds': round(elapsed, 1),
        }
        summary.append(row)
        if verbose:
            print(f"[OK]   {iid}: |Ext_{inst['N']}| = {rep['ext_count']}, "
                  f"|Adm| = {rep['adm_count']}, "
                  f"chance = {rep['chance']:.3g}, "
                  f"certified = {rep['certified']} "
                  f"({rep['certification_mode']}), "
                  f"control = {crep['certified']}, "
                  f"non-pinning ok = {rep['non_pinning_ok']} "
                  f"({elapsed:.1f}s)")
    with open(os.path.join(out_dir, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    return summary


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description="Build and certify the dataset.")
    ap.add_argument('--seed-tag', default='v1',
                    help="nonce-name seed; 'v1' regenerates the released dataset "
                         "byte for byte, any other value gives fresh names")
    ap.add_argument('--out-dir', default=DATASET_DIR)
    args = ap.parse_args()
    SEED_TAG = args.seed_tag
    main(out_dir=args.out_dir)
