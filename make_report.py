"""Regenerate the open-model results document from the saved rows, without calling any model.

Reads results/ and results_gpu/ plus the dataset summaries, and writes results_gpu/RESULTS_open.md
together with the figures produced by viz.py. Every number in the document is computed here from
the raw rows, so the document can be rebuilt at any time from the saved data alone."""
import glob, json, os, collections
import numpy as np
import viz

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = "results_gpu" if os.path.isdir(os.path.join(HERE, "results_gpu")) else "results_open"
OUT = os.path.join(HERE, RESULTS, "RESULTS_open.md")
FAMILY_TITLE = {"base": "Base family (9 certified instances, m = 1..3)",
                "cot": "Scratchpad arm (same instances, reasoning permitted)",
                "scaled": "A2, scaled family (180 instances, 18 configurations)",
                "asym": "A3, asymmetric-data family (left and right Kan extensions differ)"}


def ci(k, n):
    p, lo, hi = viz.wilson(k, n)
    return f"{p:.2f} [{max(lo, 0):.2f}, {min(hi, 1):.2f}] ({k}/{n})" if n else "-"


def main():
    df, lp, meta = viz.load_all()
    if df.empty:
        print("no results"); return
    man = json.load(open(os.path.join(HERE, RESULTS, "MANIFEST.json"))) if os.path.exists(os.path.join(HERE, RESULTS, "MANIFEST.json")) else []
    L = []
    L.append("# Open-model results, rebuilt from saved rows\n")
    L.append(f"{len(df)} graded answers, {df.model.nunique()} models, families "
             f"{', '.join(f'{k} {v}' for k, v in sorted(collections.Counter(df.family).items()))}. "
             f"{len(man)} result files, {sum(m['rows'] for m in man)} rows, checksums in `results_gpu/MANIFEST.json`.\n")
    L.append("Rebuild with `python3 make_report.py`; no model is called and nothing is re-run.\n")

    for fam in ["base", "cot", "scaled", "asym"]:
        d = df[df.family == fam]
        if d.empty: continue
        L.append(f"\n## {FAMILY_TITLE[fam]}\n")
        if fam == "asym":
            L.append("| model | calibration Lan/Ran/other | jump admissible | jump falls back to a Kan extension | control Ran | control Lan |")
            L.append("|---|---|---|---|---|---|")
            for m in viz.model_order(d):
                dm = d[d.model == m]
                cal, jmp = dm[dm.variant == "calibration"], dm[dm.variant == "jump"]
                lan = int((cal["class"] == "LAN").sum()); ran = int((cal["class"] == "RAN").sum())
                L.append(f"| {viz.short(m)} | {lan}/{ran}/{len(cal) - lan - ran} | {ci(int((jmp['class'] == 'ADM').sum()), len(jmp))} "
                         f"| {int(jmp['class'].isin(['LAN', 'RAN']).sum())}/{len(jmp)} "
                         f"| {ci(int((dm[dm.variant == 'control_ran']['class'] == 'RAN').sum()), int((dm.variant == 'control_ran').sum()))} "
                         f"| {ci(int((dm[dm.variant == 'control_lan']['class'] == 'LAN').sum()), int((dm.variant == 'control_lan').sum()))} |")
            continue
        L.append("| model | open | DC, default under free choice | KD, default under falsifying constraints | jump accuracy | control | ADM/KAN/other/rule violation/unparsable | truncated |")
        L.append("|---|---|---|---|---|---|---|---|")
        for m in viz.model_order(d):
            dm = d[d.model == m]
            cal, jmp, ctl = dm[dm.variant == "calibration"], dm[dm.variant == "jump"], dm[dm.variant.str.startswith("control")]
            cls = collections.Counter(jmp["class"])
            trunc = int((jmp["finish"] != "stop").sum()) if "finish" in jmp else 0
            L.append(f"| {viz.short(m)} | {'yes' if m not in viz.CLOSED else 'no'} "
                     f"| {ci(int((cal['class'] == 'KAN').sum()), len(cal))} | {ci(int((jmp['class'] == 'KAN').sum()), len(jmp))} "
                     f"| {ci(int((jmp['class'] == 'ADM').sum()), len(jmp))} | {ci(int((ctl['class'] == 'KAN').sum()), len(ctl))} "
                     f"| {cls['ADM']}/{cls['KAN']}/{cls['VALID_OTHER']}/{cls['RULE_VIOL']}/{cls['INVALID']} | {trunc}/{len(jmp)} |")

    j = df[df.variant == "jump"]
    L.append(f"\n## Headline\n")
    L.append(f"- KD is {int((j['class'] == 'KAN').sum())} of {len(j)} jump answers over every model, family and arm.")
    for fam in ["base", "cot", "scaled"]:
        s = j[j.family == fam]
        if len(s): L.append(f"- {FAMILY_TITLE[fam].split('(')[0].strip()}: jump accuracy {ci(int((s['class'] == 'ADM').sum()), len(s))} pooled over models.")
    ch = df[(df.variant == "jump") & df.chance.notna()]
    if len(ch): L.append(f"- Chance level of the instances measured: {ch.chance.min():.1e} to {ch.chance.max():.2f}.")

    b = df[(df.family == "base") & (df.rendering == "factory")]; c = df[df.family == "cot"]
    if not c.empty:
        L.append("\n## Effect of a scratchpad\n")
        L.append("| model | jump accuracy, no explanation | jump accuracy, reasoning permitted | DC, no explanation | DC, reasoning permitted |")
        L.append("|---|---|---|---|---|")
        for m in [m for m in viz.model_order(c) if m in set(b.model)]:
            bb, cc = b[b.model == m], c[c.model == m]
            L.append(f"| {viz.short(m)} "
                     f"| {ci(int((bb[bb.variant == 'jump']['class'] == 'ADM').sum()), int((bb.variant == 'jump').sum()))} "
                     f"| {ci(int((cc[cc.variant == 'jump']['class'] == 'ADM').sum()), int((cc.variant == 'jump').sum()))} "
                     f"| {ci(int((bb[bb.variant == 'calibration']['class'] == 'KAN').sum()), int((bb.variant == 'calibration').sum()))} "
                     f"| {ci(int((cc[cc.variant == 'calibration']['class'] == 'KAN').sum()), int((cc.variant == 'calibration').sum()))} |")

    if not lp.empty:
        piv = lp.pivot_table(index=["model", "instance", "rendering"], columns="candidate", values="sum_logprob").reset_index()
        adm = next((x for x in piv.columns if "admissible" in str(x)), None)
        kan = [x for x in ("kan", "lan", "ran") if x in piv.columns]
        if adm and kan:
            piv["margin"] = piv[adm] - piv[kan].max(axis=1)
            L.append("\n## Teacher-forced preference under the unconstrained prompt\n")
            L.append("Log probability of the admissible answer minus that of the canonical one, in nats. Negative means the canonical answer is preferred.\n")
            L.append("| model | median margin | instances where the admissible answer wins |")
            L.append("|---|---|---|")
            for m in viz.model_order(piv):
                s = piv[piv.model == m].margin.dropna()
                L.append(f"| {viz.short(m)} | {np.median(s):.1f} | {int((s > 0).sum())}/{len(s)} |")

    L.append("\n## Reading and caveats\n")
    L.append("- Truncated answers are graded unparsable and never counted as a jump or as a default.")
    L.append("- The sampled arm inherits each model's own generation defaults, since the harness pins only the temperature; the greedy arm is unaffected.")
    L.append("- The scratchpad arm's design block is taken from the last segment holding a table, after an early extraction rule lost blocks written before the words FINAL DESIGN; `repair_cot.py` re-graded the affected rows from the stored raw text.")
    L.append("- Figures for every table above are in `figures/`, rebuilt by `python3 viz.py`.")
    open(OUT, "w").write("\n".join(L) + "\n")
    print(f"wrote {OUT} ({len(L)} lines)")


if __name__ == "__main__":
    main()
