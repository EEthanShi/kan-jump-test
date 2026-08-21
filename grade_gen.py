#!/usr/bin/env python3
"""grade_gen.py -- gauge-free grader for generated instances.

Given an instance's grading metadata (params + rendered names), parse a model
answer and classify it:

  ADM          in the certified admissible orbit, checked structurally
               (gauge-free): per station i, |Q_i| = 1 + p_i, internal move
               has order p_i with exactly one fixed point (its non-fixed
               points forming a single p_i-cycle), the fixed point equals
               the image of the (constant) incoming map; outgoing constant.
  KAN          the Kan-default answer: every station a singleton with the
               identity internal move (rules hold).
  VALID_OTHER  a well-formed design satisfying the R-rules and the
               end-to-end observation, but neither ADM nor KAN
               (D-requirement violations land here, as in the pilot).
  RULE_VIOL    parses, but violates an R-rule or the observation.
  INVALID      cannot be parsed as a complete design with <= N states
               per station.

Variant-level verdicts follow the pilot:
  calibration: N/A (the DC event is class == KAN)
  jump:        PASS iff ADM
  control:     PASS iff KAN
"""
import re
import sys
import json


def make_grade_meta(inst, naming):
    """Grading metadata for one (instance, rendering)."""
    return {
        'm': inst['m'], 'ps': list(inst['ps']), 'N': inst['N'],
        'naming': naming,
    }


def _parse_table(text, move):
    mm = re.search(re.escape(move) + r"\s*:\s*([^\n]+)", text, re.I)
    if not mm:
        return None
    table = {}
    for pair in mm.group(1).split(","):
        pm = re.match(r"\s*(\S+)\s*->\s*(\S+)\s*$", pair.rstrip().rstrip(".;"))
        if not pm:
            return None
        src = pm.group(1).strip()
        dst = pm.group(2).strip().rstrip(",.;")
        if src in table:
            return None
        table[src] = dst
    return table


def parse_answer(meta, text):
    """Extract per-station state sets and tables. Returns dict or None."""
    m, N = meta['m'], meta['N']
    nm = meta['naming']
    stations, cmoves, emoves = (nm['stations'], nm['chain_moves'],
                                nm['endo_moves'])
    out = {'Q': [], 'inc': [], 'endo': []}
    for i in range(1, m + 1):
        ms = re.search(re.escape(stations[i]) + r"\s*=\s*\{([^}]*)\}",
                       text, re.I)
        if not ms:
            return None
        states = [s.strip() for s in ms.group(1).split(",") if s.strip()]
        if not states or len(states) > N or len(set(states)) != len(states):
            return None
        out['Q'].append(states)
        inc = _parse_table(text, cmoves[i - 1])
        endo = _parse_table(text, emoves[i - 1])
        if inc is None or endo is None:
            return None
        out['inc'].append(inc)
        out['endo'].append(endo)
    final = _parse_table(text, cmoves[m])
    if final is None:
        return None
    out['final'] = final
    return out


def classify(meta, text):
    if not isinstance(text, str) or not text.strip():
        return "INVALID"
    d = parse_answer(meta, text)
    if d is None:
        return "INVALID"
    m, ps = meta['m'], meta['ps']
    nm = meta['naming']
    in_slot, out_slot = nm['in_slot'], nm['out_slot']

    # ---- well-formedness (typing/totality) -> INVALID if broken
    Qs = [set(q) for q in d['Q']]
    for i in range(m):
        dom = {in_slot} if i == 0 else Qs[i - 1]
        cod = Qs[i]
        inc, endo = d['inc'][i], d['endo'][i]
        if set(inc.keys()) != dom or any(v not in cod for v in inc.values()):
            return "INVALID"
        if set(endo.keys()) != cod or any(v not in cod for v in endo.values()):
            return "INVALID"
    final = d['final']
    if set(final.keys()) != Qs[m - 1]:
        return "INVALID"
    if any(v != out_slot for v in final.values()):
        # the out station has exactly one slot; anything else is ill-typed
        return "INVALID"

    # ---- R-rules + end-to-end observation -> RULE_VIOL if broken
    x = in_slot
    for i in range(m):
        x = d['inc'][i][x]
    if final[x] != out_slot:
        return "RULE_VIOL"
    for i in range(m):
        inc, endo = d['inc'][i], d['endo'][i]
        nxt = d['inc'][i + 1] if i + 1 < m else final
        # R{i}.1: endo fixes the image of the incoming map
        if any(endo[v] != v for v in inc.values()):
            return "RULE_VIOL"
        # R{i}.2: nxt o endo = nxt
        if any(nxt[endo[q]] != nxt[q] for q in Qs[i]):
            return "RULE_VIOL"
        # R{i}.3: endo^{p_i} = id
        for q in Qs[i]:
            y = q
            for _ in range(ps[i]):
                y = endo[y]
            if y != q:
                return "RULE_VIOL"

    # ---- KAN: all singletons with identity moves
    if all(len(q) == 1 for q in Qs) and all(
            all(endo[q] == q for q in Qs[i])
            for i, endo in enumerate(d['endo'])):
        return "KAN"

    # ---- ADM: structural characterization of the admissible orbit
    adm = True
    for i in range(m):
        p = ps[i]
        Q, inc, endo = Qs[i], d['inc'][i], d['endo'][i]
        if len(Q) != 1 + p:
            adm = False
            break
        fixed = {q for q in Q if endo[q] == q}
        image = set(inc.values())
        if len(fixed) != 1 or len(image) != 1 or fixed != image:
            adm = False
            break
        moved = [q for q in Q if q not in fixed]
        # non-fixed points must form a single p-cycle
        orb = {moved[0]}
        y = endo[moved[0]]
        while y not in orb:
            orb.add(y)
            y = endo[y]
        if len(orb) != p or orb != set(moved):
            adm = False
            break
    if adm:
        return "ADM"

    return "VALID_OTHER"


def verdict(variant, cls):
    if variant == "jump":
        return "PASS" if cls == "ADM" else "FAIL"
    if variant == "control":
        return "PASS" if cls == "KAN" else "FAIL"
    return "N/A"


# ----------------------------------------------------------------- self-tests
def _meta_m1():
    return {'m': 1, 'ps': [2], 'N': 4, 'naming': {
        'stations': ['NARV', 'QUILB', 'SORM'],
        'chain_moves': ['dax', 'rell'], 'endo_moves': ['fen'],
        'in_slot': 'n1', 'out_slot': 's1', 'slot_prefixes': ['q1_'],
    }}


def _meta_m2():
    return {'m': 2, 'ps': [2, 3], 'N': 5, 'naming': {
        'stations': ['SOKU', 'GINU', 'SITA', 'ZOZU'],
        'chain_moves': ['romu', 'nivu', 'nimi'], 'endo_moves': ['rabo', 'lata'],
        'in_slot': 'n1', 'out_slot': 's1', 'slot_prefixes': ['q1_', 'q2_'],
    }}


def _meta_m3():
    return {'m': 3, 'ps': [2, 2, 2], 'N': 4, 'naming': {
        'stations': ['DALO', 'VETU', 'RIMU', 'POSA', 'KANI'],
        'chain_moves': ['zeku', 'moli', 'febi', 'daru'],
        'endo_moves': ['sopi', 'gavu', 'niru'],
        'in_slot': 'n1', 'out_slot': 's1',
        'slot_prefixes': ['q1_', 'q2_', 'q3_'],
    }}


def self_test():
    m1 = _meta_m1()
    m2 = _meta_m2()
    cases = []

    adm1 = ("QUILB = {q1_1, q1_2, q1_3}\ndax: n1 -> q1_1\n"
            "fen: q1_1 -> q1_1, q1_2 -> q1_3, q1_3 -> q1_2\n"
            "rell: q1_1 -> s1, q1_2 -> s1, q1_3 -> s1")
    adm1_renamed = ("QUILB = {qa, qb, qc}\ndax: n1 -> qc\n"
                    "fen: qc -> qc, qa -> qb, qb -> qa\n"
                    "rell: qa -> s1, qb -> s1, qc -> s1")
    kan1 = ("QUILB = {q1_1}\ndax: n1 -> q1_1\nfen: q1_1 -> q1_1\n"
            "rell: q1_1 -> s1")
    viol1 = ("QUILB = {q1_1, q1_2}\ndax: n1 -> q1_1\n"
             "fen: q1_1 -> q1_2, q1_2 -> q1_1\n"
             "rell: q1_1 -> s1, q1_2 -> s1")           # breaks R1.1
    other1 = ("QUILB = {q1_1, q1_2}\ndax: n1 -> q1_1\n"
              "fen: q1_1 -> q1_1, q1_2 -> q1_2\n"
              "rell: q1_1 -> s1, q1_2 -> s1")
    junk1 = "I think the answer is obvious."
    cases += [(m1, adm1, 'ADM'), (m1, adm1_renamed, 'ADM'),
              (m1, kan1, 'KAN'), (m1, viol1, 'RULE_VIOL'),
              (m1, other1, 'VALID_OTHER'), (m1, junk1, 'INVALID')]

    adm2 = ("GINU = {q1_1, q1_2, q1_3}\nromu: n1 -> q1_1\n"
            "rabo: q1_1 -> q1_1, q1_2 -> q1_3, q1_3 -> q1_2\n"
            "SITA = {q2_1, q2_2, q2_3, q2_4}\n"
            "nivu: q1_1 -> q2_1, q1_2 -> q2_1, q1_3 -> q2_1\n"
            "lata: q2_1 -> q2_1, q2_2 -> q2_3, q2_3 -> q2_4, q2_4 -> q2_2\n"
            "nimi: q2_1 -> s1, q2_2 -> s1, q2_3 -> s1, q2_4 -> s1")
    adm2_renamed = ("GINU = {x, y, z}\nromu: n1 -> y\n"
                    "rabo: y -> y, x -> z, z -> x\n"
                    "SITA = {u4, u3, u2, u1}\n"
                    "nivu: y -> u3, x -> u3, z -> u3\n"
                    "lata: u3 -> u3, u1 -> u2, u2 -> u4, u4 -> u1\n"
                    "nimi: u1 -> s1, u2 -> s1, u3 -> s1, u4 -> s1")
    kan2 = ("GINU = {q1_1}\nromu: n1 -> q1_1\nrabo: q1_1 -> q1_1\n"
            "SITA = {q2_1}\nnivu: q1_1 -> q2_1\nlata: q2_1 -> q2_1\n"
            "nimi: q2_1 -> s1")
    viol2 = ("GINU = {q1_1, q1_2, q1_3}\nromu: n1 -> q1_1\n"
             "rabo: q1_1 -> q1_1, q1_2 -> q1_3, q1_3 -> q1_2\n"
             "SITA = {q2_1, q2_2, q2_3, q2_4}\n"
             "nivu: q1_1 -> q2_2, q1_2 -> q2_2, q1_3 -> q2_2\n"
             "lata: q2_1 -> q2_1, q2_2 -> q2_3, q2_3 -> q2_4, q2_4 -> q2_2\n"
             "nimi: q2_1 -> s1, q2_2 -> s1, q2_3 -> s1, q2_4 -> s1")
    # ^ breaks R2.1: lata moves the image of nivu
    other2 = ("GINU = {q1_1, q1_2, q1_3}\nromu: n1 -> q1_1\n"
              "rabo: q1_1 -> q1_1, q1_2 -> q1_3, q1_3 -> q1_2\n"
              "SITA = {q2_1}\nnivu: q1_1 -> q2_1, q1_2 -> q2_1, q1_3 -> q2_1\n"
              "lata: q2_1 -> q2_1\nnimi: q2_1 -> s1")
    # ^ rules hold; station 2 is singleton-with-identity but station 1 is not
    junk2 = "GINU = {}\nnothing else"
    cases += [(m2, adm2, 'ADM'), (m2, adm2_renamed, 'ADM'),
              (m2, kan2, 'KAN'), (m2, viol2, 'RULE_VIOL'),
              (m2, other2, 'VALID_OTHER'), (m2, junk2, 'INVALID')]

    m3 = _meta_m3()
    adm3 = ("VETU = {q1_1, q1_2, q1_3}\nzeku: n1 -> q1_1\n"
            "sopi: q1_1 -> q1_1, q1_2 -> q1_3, q1_3 -> q1_2\n"
            "RIMU = {q2_1, q2_2, q2_3}\n"
            "moli: q1_1 -> q2_1, q1_2 -> q2_1, q1_3 -> q2_1\n"
            "gavu: q2_1 -> q2_1, q2_2 -> q2_3, q2_3 -> q2_2\n"
            "POSA = {q3_1, q3_2, q3_3}\n"
            "febi: q2_1 -> q3_1, q2_2 -> q3_1, q2_3 -> q3_1\n"
            "niru: q3_1 -> q3_1, q3_2 -> q3_3, q3_3 -> q3_2\n"
            "daru: q3_1 -> s1, q3_2 -> s1, q3_3 -> s1")
    adm3_renamed = ("VETU = {xa, xb, xc}\nzeku: n1 -> xb\n"
                    "sopi: xb -> xb, xa -> xc, xc -> xa\n"
                    "RIMU = {u3, u1, u2}\n"
                    "moli: xb -> u2, xa -> u2, xc -> u2\n"
                    "gavu: u2 -> u2, u1 -> u3, u3 -> u1\n"
                    "POSA = {w1, w2, w3}\n"
                    "febi: u1 -> w3, u2 -> w3, u3 -> w3\n"
                    "niru: w3 -> w3, w1 -> w2, w2 -> w1\n"
                    "daru: w1 -> s1, w2 -> s1, w3 -> s1")
    kan3 = ("VETU = {q1_1}\nzeku: n1 -> q1_1\nsopi: q1_1 -> q1_1\n"
            "RIMU = {q2_1}\nmoli: q1_1 -> q2_1\ngavu: q2_1 -> q2_1\n"
            "POSA = {q3_1}\nfebi: q2_1 -> q3_1\nniru: q3_1 -> q3_1\n"
            "daru: q3_1 -> s1")
    viol3 = ("VETU = {q1_1, q1_2, q1_3}\nzeku: n1 -> q1_1\n"
             "sopi: q1_1 -> q1_1, q1_2 -> q1_3, q1_3 -> q1_2\n"
             "RIMU = {q2_1, q2_2, q2_3}\n"
             "moli: q1_1 -> q2_2, q1_2 -> q2_2, q1_3 -> q2_2\n"
             "gavu: q2_1 -> q2_1, q2_2 -> q2_3, q2_3 -> q2_2\n"
             "POSA = {q3_1, q3_2, q3_3}\n"
             "febi: q2_1 -> q3_1, q2_2 -> q3_1, q2_3 -> q3_1\n"
             "niru: q3_1 -> q3_1, q3_2 -> q3_3, q3_3 -> q3_2\n"
             "daru: q3_1 -> s1, q3_2 -> s1, q3_3 -> s1")
    # ^ breaks R2.1: gavu moves the image of moli
    other3 = ("VETU = {q1_1, q1_2, q1_3}\nzeku: n1 -> q1_1\n"
              "sopi: q1_1 -> q1_1, q1_2 -> q1_3, q1_3 -> q1_2\n"
              "RIMU = {q2_1, q2_2, q2_3}\n"
              "moli: q1_1 -> q2_1, q1_2 -> q2_1, q1_3 -> q2_1\n"
              "gavu: q2_1 -> q2_1, q2_2 -> q2_3, q2_3 -> q2_2\n"
              "POSA = {q3_1}\n"
              "febi: q2_1 -> q3_1, q2_2 -> q3_1, q2_3 -> q3_1\n"
              "niru: q3_1 -> q3_1\n"
              "daru: q3_1 -> s1")
    # ^ rules hold; station 3 is singleton-with-identity, stations 1-2 not
    junk3 = "VETU is best left empty, I believe."
    cases += [(m3, adm3, 'ADM'), (m3, adm3_renamed, 'ADM'),
              (m3, kan3, 'KAN'), (m3, viol3, 'RULE_VIOL'),
              (m3, other3, 'VALID_OTHER'), (m3, junk3, 'INVALID')]

    ok = True
    for meta, text, want in cases:
        got = classify(meta, text)
        status = "ok" if got == want else "MISMATCH"
        if got != want:
            ok = False
        print(f"  [{status}] m={meta['m']} expected {want:12s} got {got}")
    print("grade_gen self-test:", "ALL PASS" if ok else "FAILURES ABOVE")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        sys.exit(0 if self_test() else 1)
    # grade a JSONL of {"meta": {...}, "variant": ..., "answer": ...} on stdin
    for line in sys.stdin:
        rec = json.loads(line)
        cls = classify(rec["meta"], rec["answer"])
        rec["class"] = cls
        rec["verdict"] = verdict(rec.get("variant", ""), cls)
        rec.pop("meta", None)
        print(json.dumps(rec))
