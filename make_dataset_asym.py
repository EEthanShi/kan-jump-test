"""Dataset for the asymmetric-data family (A3): configs (k, l, N) x seeds x renderings x variants."""
import argparse, json, os
import engine_asym as ea, render_asym as ra, grade_asym as ga

# every configuration certified by search_asym_configs.py: the two Kan extensions differ, exactly
# one admissible class survives, and it is neither of them
CONFIGS = [(2, 1, 4), (3, 1, 5), (1, 2, 3), (2, 2, 4), (3, 2, 5), (4, 1, 6), (5, 1, 7)]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='dataset_asym'); ap.add_argument('--seeds', type=int, default=10)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); summary = []
    for (k, l, N) in CONFIGS:
        rep = ea.Inst(k, l, N).certify(); assert rep['certified'], (k, l, N)
        Lan, Ran, Adm0 = rep['_Lan'], rep['_Ran'], rep['_Adm'][0]
        for s in range(1, a.seeds + 1):
            iid = f'asym_k{k}l{l}_s{s}'; d = os.path.join(a.out, iid); os.makedirs(d, exist_ok=True)
            key = {'family': 'asym', 'k': k, 'l': l, 'N': N, 'lan_size_b': Lan['idb'][0], 'ran_size_b': Ran['idb'][0],
                   'ext_count': rep['ext_count'], 'adm_count': rep['adm_count'], 'chance': rep['chance'], 'renderings': {}}
            for rd in ra.render.RENDERINGS:
                nm = ra.make_naming(k, l, rd, seed_tag=f's{s}')
                for v in ra.VARIANTS:
                    text, _ = ra.render_asym(k, l, N, rd, v, nm)
                    open(os.path.join(d, f'prompt_{rd}_{v}.txt'), 'w').write(text)
                key['renderings'][rd] = {'grade_meta': ga.make_grade_meta(k, l, N, nm),
                                         'lan_answer': ra.answer_text(nm, Lan), 'ran_answer': ra.answer_text(nm, Ran),
                                         'example_admissible_answer': ra.answer_text(nm, Adm0)}
            json.dump(key, open(os.path.join(d, 'answer_key.json'), 'w'), indent=1)
            json.dump({'id': iid, 'family': 'asym', 'k': k, 'l': l, 'N': N}, open(os.path.join(d, 'meta.json'), 'w'))
            summary.append({'id': iid, 'k': k, 'l': l, 'N': N, 'chance': rep['chance'], 'adm_count': rep['adm_count'], 'ext_count': rep['ext_count']})
    json.dump(summary, open(os.path.join(a.out, 'summary.json'), 'w'), indent=1)
    print(f'{len(summary)} instances written to {a.out}')


if __name__ == '__main__':
    main()
