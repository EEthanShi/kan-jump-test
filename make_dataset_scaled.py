"""Scaled dataset (A2): more certified configurations and several nonce vocabularies per configuration.

Certification is per (m, ps) and independent of the vocabulary, so each configuration is
certified once (enumeration for m <= 2 within the time budget, the family theorem otherwise)
and then rendered under K fresh nonce vocabularies (seed tags s1..sK). Instance ids are
<config>_s<k>; s1 reproduces the shipped dataset's vocabulary only for the original configs.
"""
import argparse, json, os, sys, time
import make_dataset as md

# engine.build_family implements primes 2 and 3 only (the family theorem is general; extending
# the certified code to larger primes is separate work), so new configurations stay inside {2,3}:
# the m=3 patterns not shipped, and four m=4 patterns, all certified by the family theorem.
NEW_CONFIGS_ENUM = []
NEW_CONFIGS_THM = [(3, (2, 2, 3)), (3, (2, 3, 2)), (3, (3, 2, 2)), (3, (3, 2, 3)), (3, (3, 3, 2)),
                   (4, (2, 2, 2, 2)), (4, (3, 3, 3, 3)), (4, (2, 3, 2, 3)), (4, (3, 2, 3, 2))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dataset_scaled")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--configs", default="all", help="all | orig | new | comma list like 1:2,2:3-5")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    md.GLOBAL_NAME_REGISTRY.clear()
    os.makedirs(a.out, exist_ok=True)
    jobs = []
    if a.configs in ("all", "orig"):
        jobs += [(m, ps, md.build_and_certify) for m, ps in md.CONFIGS]
        jobs += [(m, ps, md.build_and_certify_theorem) for m, ps in md.M3_CONFIGS]
    if a.configs in ("all", "new"):
        jobs += [(m, ps, md.build_and_certify) for m, ps in NEW_CONFIGS_ENUM]
        jobs += [(m, ps, md.build_and_certify_theorem) for m, ps in NEW_CONFIGS_THM]
    if ":" in a.configs:
        for item in a.configs.split(","):
            m, ps = item.split(":"); ps = tuple(int(x) for x in ps.split("-")); m = int(m)
            jobs.append((m, ps, md.build_and_certify if m <= 2 and max(ps) <= 3 else md.build_and_certify_theorem))
    summary = []
    for m, ps, builder in jobs:
        cid = md.inst_id(m, ps)
        t0 = time.time()
        inst, rep, crep, elapsed = builder(m, ps)
        ok = rep["certified"] and crep["certified"]
        print(f"[{'OK ' if ok else 'FAIL'}] {cid:10s} N={inst['N']} |Ext_N|={rep['ext_count']} |Adm|={rep['adm_count']} "
              f"chance={rep['chance']:.2e} mode={rep['certification_mode']} {elapsed:.0f}s")
        if not ok:
            summary.append({"id": cid, "skipped": True, "reason": "certification failed"}); continue
        for k in range(1, a.seeds + 1):
            md.GLOBAL_NAME_REGISTRY.clear()   # names need only be unique within one instance;
            md.SEED_TAG = f"s{k}"             # a dataset-wide registry exhausts the 3-letter prefix space
            iid = f"{cid}_s{k}"
            if not a.dry:
                md.make_instance_dir(inst, rep, crep, os.path.join(a.out, iid))
            summary.append({"id": iid, "config": cid, "seed_tag": md.SEED_TAG, "m": m, "ps": list(ps),
                            "N": inst["N"], "ext_count": rep["ext_count"], "adm_count": rep["adm_count"],
                            "chance": rep["chance"], "certification_mode": rep["certification_mode"],
                            "non_pinning_ok": rep["non_pinning_ok"]})
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    n_ok = sum(1 for s in summary if not s.get("skipped"))
    print(f"instances written: {n_ok}  (configs: {len(jobs)}, seeds/config: {a.seeds})")


if __name__ == "__main__":
    main()
