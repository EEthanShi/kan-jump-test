"""Search the asymmetric family for further certified configurations.

A configuration (k, l, N) is certified when the left and right Kan extensions differ, exactly one
admissible class survives the constraints, and that class is neither Kan extension. Enumeration
grows fast in N, so each candidate gets a wall-clock budget and the search reports what it proved
inside it."""
import argparse, json, os, signal, time
import engine_asym as ea

CANDIDATES = [(2, 1, 4), (3, 1, 5), (1, 2, 3),          # already in the dataset
              (2, 1, 5), (4, 1, 6), (1, 2, 4), (2, 2, 4), (2, 2, 5), (3, 2, 5), (1, 3, 4), (5, 1, 7)]


class Timeout(Exception):
    pass


def _alarm(sig, frame):
    raise Timeout()


def try_config(k, l, N, budget):
    signal.signal(signal.SIGALRM, _alarm); signal.alarm(budget)
    t0 = time.time()
    try:
        rep = ea.Inst(k, l, N).certify()
        out = {"k": k, "l": l, "N": N, "certified": bool(rep["certified"]), "ext_count": rep["ext_count"],
               "adm_count": rep["adm_count"], "adm_classes": rep["adm_classes"], "chance": rep["chance"],
               "lan_size": rep["_Lan"]["idb"][0], "ran_size": rep["_Ran"]["idb"][0],
               "seconds": round(time.time() - t0, 1)}
    except Timeout:
        out = {"k": k, "l": l, "N": N, "certified": None, "note": f"budget {budget}s exhausted"}
    finally:
        signal.alarm(0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=900, help="seconds per configuration")
    ap.add_argument("--out", default="formalization_asym_search.json")
    a = ap.parse_args()
    rows = []
    for (k, l, N) in CANDIDATES:
        r = try_config(k, l, N, a.budget); rows.append(r)
        mark = {True: "certified", False: "not certified", None: "unfinished"}[r["certified"]]
        extra = "" if r["certified"] is None else f" |Ext|={r['ext_count']} adm={r['adm_count']} in {r['adm_classes']} class(es) chance={r['chance']:.3g} Lan={r['lan_size']} Ran={r['ran_size']} {r['seconds']}s"
        print(f"({k},{l},{N}) {mark}{extra}", flush=True)
        json.dump(rows, open(a.out, "w"), indent=1)
    ok = [r for r in rows if r["certified"]]
    print(f"\n{len(ok)} certified of {len(rows)} tried; written to {a.out}")


if __name__ == "__main__":
    main()
