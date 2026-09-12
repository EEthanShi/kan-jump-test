"""Grader for the asymmetric-data family. Classes:
  LAN / RAN     the answer is gauge-equivalent to the left / right Kan extension
  ADM           gauge-equivalent to the certified admissible class
  VALID_OTHER   a well-formed functor satisfying the rules and the observation, none of the above
  RULE_VIOL     parses and is well-typed, but breaks an R-rule or the observation
  INVALID       cannot be parsed as a complete design with <= N middle units
Per-variant reading: calibration -> DC event is LAN or RAN (report which); jump -> success ADM,
Kan-default event LAN or RAN; control_ran -> PASS iff RAN; control_lan -> PASS iff LAN.
"""
import re
from functools import lru_cache
import engine_asym as ea
from grade_gen import _parse_table


@lru_cache(maxsize=None)
def _ref(k, l, N):
    rep = ea.Inst(k, l, N).certify()
    return ea.Inst(k, l, N), rep['_Lan'], rep['_Ran'], rep['_Adm'][0], rep['certified']


def make_grade_meta(k, l, N, naming):
    return {'family': 'asym', 'k': k, 'l': l, 'N': N, 'naming': naming}


def parse(meta, text):
    nm, N = meta['naming'], meta['N']
    H, cm, e = nm['stations'][1], nm['chain_moves'], nm['endo_moves'][0]
    ms = re.search(re.escape(H) + r"\s*=\s*\{([^}]*)\}", text, re.I)
    if not ms:
        return None
    Q = [s.strip() for s in ms.group(1).split(",") if s.strip()]
    if not Q or len(Q) > N or len(set(Q)) != len(Q):
        return None
    a_in, endo, a_out = _parse_table(text, cm[0]), _parse_table(text, e), _parse_table(text, cm[1])
    if a_in is None or endo is None or a_out is None:
        return None
    return {'Q': Q, 'a_in': a_in, 'endo': endo, 'a_out': a_out}


def classify(meta, text):
    if not isinstance(text, str) or not text.strip():
        return "INVALID"
    d = parse(meta, text)
    if d is None:
        return "INVALID"
    nm = meta['naming']; ins, outs = nm['in_slots'], nm['out_slots']
    Q = d['Q']; Qs = set(Q)
    a_in, endo, a_out = d['a_in'], d['endo'], d['a_out']
    # well-typed and total
    if set(a_in) != set(ins) or any(v not in Qs for v in a_in.values()): return "INVALID"
    if set(endo) != Qs or any(v not in Qs for v in endo.values()): return "INVALID"
    if set(a_out) != Qs or any(v not in set(outs) for v in a_out.values()): return "INVALID"
    # observation: every input unit ends at the first output unit
    if any(a_out[a_in[s]] != outs[0] for s in ins): return "RULE_VIOL"
    # R1.1 endo fixes the image of a_in; R1.2 a_out o endo = a_out; R1.3 endo o endo = id
    if any(endo[v] != v for v in a_in.values()): return "RULE_VIOL"
    if any(a_out[endo[q]] != a_out[q] for q in Q): return "RULE_VIOL"
    if any(endo[endo[q]] != q for q in Q): return "RULE_VIOL"
    # build the functor with Q indexed in listed order
    k, l, N = meta['k'], meta['l'], meta['N']
    qi = {q: i for i, q in enumerate(Q)}; n = len(Q)
    F = {'ida': ea.fs_id(k), 'idb': ea.fs_id(n), 'idc': ea.fs_id(l),
         'f': (k, n, tuple(qi[a_in[s]] for s in ins)),
         't': (n, n, tuple(qi[endo[q]] for q in Q)),
         'g': (n, l, tuple(outs.index(a_out[q]) for q in Q)),
         'h': (k, l, tuple([0] * k))}
    inst, Lan, Ran, Adm0, cert = _ref(k, l, N)
    if not inst.is_functor(F): return "RULE_VIOL"
    if inst.gauge_equiv(F, Lan): return "LAN"
    if inst.gauge_equiv(F, Ran): return "RAN"
    if inst.gauge_equiv(F, Adm0): return "ADM"
    return "VALID_OTHER"


def arm_outcome(variant, cls):
    if variant == 'calibration': return cls
    if variant == 'jump': return {'ADM': 'PASS', 'LAN': 'KANDEF', 'RAN': 'KANDEF'}.get(cls, 'FAIL')
    if variant == 'control_ran': return 'PASS' if cls == 'RAN' else 'FAIL'
    if variant == 'control_lan': return 'PASS' if cls == 'LAN' else 'FAIL'
    raise ValueError(variant)


if __name__ == '__main__':
    import render_asym as ra
    for (k, l, N) in [(2, 1, 4), (3, 1, 5), (1, 2, 3)]:
        nm = ra.make_naming(k, l, 'factory'); meta = make_grade_meta(k, l, N, nm)
        inst, Lan, Ran, Adm0, cert = _ref(k, l, N)
        got = [classify(meta, ra.answer_text(nm, Lan)), classify(meta, ra.answer_text(nm, Ran)),
               classify(meta, ra.answer_text(nm, Adm0))]
        bad = ra.answer_text(nm, Adm0).replace(' -> ', ' => ', 1)             # unparsable table
        viol = ra.answer_text(nm, Lan).replace(f"{nm['chain_moves'][1]}:", f"{nm['chain_moves'][1]}: q1_1 -> {nm['out_slots'][-1]},", 1) if l > 1 else None
        res = {'Lan': got[0], 'Ran': got[1], 'Adm': got[2], 'garbled': classify(meta, bad)}
        if viol: res['wrong_obs'] = classify(meta, viol)
        print(f'({k},{l},{N}) certified={cert}', res)
        assert got == ['LAN', 'RAN', 'ADM'] and classify(meta, bad) == 'INVALID'
    print('grade_asym round-trip OK')
