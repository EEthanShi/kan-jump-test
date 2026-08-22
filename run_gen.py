"""Run generated dataset instances against models via OpenRouter.

Smoke test (default):
  python3 run_gen.py --smoke      # 2 instances x 2 models x 6 calls = 24 calls
Full run (only with explicit flag):
  python3 run_gen.py --instances m1_p2,m1_p3,m2_p22,m2_p32,m2_p33 \
      --models <ids> --n-jump 8 --n-cal 5 --n-ctrl 3

Reads the key from the OPENROUTER_API_KEY environment variable (or ./.env). Results appended to results_gen.jsonl
(resumable on (instance, rendering, model, variant, sample)).
"""

import argparse
import json
import os
import pathlib
import time
import urllib.error
import urllib.request

import grade_gen

HERE = pathlib.Path(__file__).parent

SMOKE_MODELS = ["deepseek/deepseek-v4-pro-0813", "google/gemini-3.1-pro-preview"]
SMOKE_INSTANCES = ["m1_p3", "m2_p22"]


def load_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("set OPENROUTER_API_KEY (env var or .env file)")


def ask(key, model, prompt, temperature):
    payload = {"model": model,
               "messages": [{"role": "user", "content": prompt}],
               "temperature": temperature, "max_tokens": 12000}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", data=data,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                out = json.loads(r.read())
            ch = out["choices"][0]
            return (ch["message"].get("content") or "",
                    ch.get("finish_reason"), ch.get("native_finish_reason"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503):
                time.sleep(10 * (2 ** attempt))
                continue
            raise
    raise last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--instances", default=None)
    ap.add_argument("--models", default=None)
    ap.add_argument("--rendering", default="factory")
    ap.add_argument("--n-jump", type=int, default=3)
    ap.add_argument("--n-cal", type=int, default=2)
    ap.add_argument("--n-ctrl", type=int, default=1)
    ap.add_argument("--results", default="results_gen.jsonl")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    results_path = HERE / args.results
    if args.report:
        report(results_path)
        return

    if args.smoke:
        instances, models = SMOKE_INSTANCES, SMOKE_MODELS
    else:
        assert args.instances and args.models, "--instances and --models required"
        instances = args.instances.split(",")
        models = args.models.split(",")

    key = load_key()
    done = set()
    if results_path.exists():
        for line in results_path.read_text().splitlines():
            r = json.loads(line)
            done.add((r["instance"], r["rendering"], r["model"],
                      r["variant"], r["sample"]))

    plan = []
    for iid in instances:
        for model in models:
            for variant, n in (("jump", args.n_jump),
                               ("calibration", args.n_cal),
                               ("control", args.n_ctrl)):
                for i in range(n):
                    t = 0.0 if i == 0 else 0.7
                    plan.append((iid, model, variant, i, t))
    print(f"{len(plan)} calls planned")

    with results_path.open("a") as f:
        for iid, model, variant, i, t in plan:
            if (iid, args.rendering, model, variant, i) in done:
                continue
            idir = HERE / "dataset" / iid
            prompt = (idir / f"prompt_{args.rendering}_{variant}.txt").read_text()
            gm = json.loads((idir / "answer_key.json").read_text())[
                "renderings"][args.rendering]["grade_meta"]
            try:
                answer, fin, nfin = ask(key, model, prompt, t)
            except Exception as e:
                print(f"[error] {iid}/{model}/{variant}#{i}: {e}")
                time.sleep(5)
                continue
            cls = grade_gen.classify(gm, answer)
            rec = {"instance": iid, "rendering": args.rendering,
                   "model": model, "variant": variant, "sample": i,
                   "temperature": t, "finish": fin, "native_finish": nfin,
                   "answer": answer, "class": cls}
            f.write(json.dumps(rec) + "\n")
            f.flush()
            print(f"{iid:8s} {model.split('/')[1][:22]:22s} "
                  f"{variant:11s} #{i} -> {cls}")
            time.sleep(1.0)


def report(results_path):
    rows = [json.loads(l) for l in results_path.read_text().splitlines()]
    keys = sorted({(r["instance"], r["model"]) for r in rows})
    print(f"{'instance':9s} {'model':24s} {'DC':>5s} {'KD':>5s} "
          f"{'jumpOK':>7s} {'ctrlOK':>7s} {'inv':>5s} {'trunc':>5s}")
    for iid, m in keys:
        rs = [r for r in rows if r["instance"] == iid and r["model"] == m]
        cal = [r for r in rs if r["variant"] == "calibration"]
        jmp = [r for r in rs if r["variant"] == "jump"]
        ctl = [r for r in rs if r["variant"] == "control"]
        frac = lambda xs, c: (sum(r["class"] == c for r in xs) / len(xs)) if xs else 0
        inv = sum(r["class"] == "INVALID" for r in rs) / len(rs) if rs else 0
        trunc = sum(r.get("finish") == "length" for r in rs) / len(rs) if rs else 0
        print(f"{iid:9s} {m.split('/')[1][:24]:24s} "
              f"{frac(cal,'KAN'):5.2f} {frac(jmp,'KAN'):5.2f} "
              f"{frac(jmp,'ADM'):7.2f} {frac(ctl,'KAN'):7.2f} {inv:5.2f} {trunc:5.2f}")

    # ---- pooled aggregates with the paper's definitions ----
    def is_trunc(r): return r.get("finish") == "length"
    def is_empty(r): return not (r.get("answer") or "").strip()
    jmp = [r for r in rows if r["variant"] == "jump"]
    cal = [r for r in rows if r["variant"] == "calibration"]
    ctl = [r for r in rows if r["variant"] == "control"]
    n = lambda xs, c: sum(r["class"] == c for r in xs)
    cal_cond = [r for r in cal if not is_trunc(r) and not is_empty(r)]
    cal_nolen = [r for r in cal if not is_trunc(r)]
    greedy = [r for r in jmp if r["temperature"] == 0.0]
    sampled = [r for r in jmp if r["temperature"] > 0]
    print("\n== pooled aggregates (paper definitions) ==")
    print(f"KD (jump answers equal to the Kan default): {n(jmp,'KAN')}/{len(jmp)}")
    print(f"jump accuracy (ADM): {n(jmp,'ADM')}/{len(jmp)}  "
          f"greedy {n(greedy,'ADM')}/{len(greedy)}  sampled {n(sampled,'ADM')}/{len(sampled)}")
    print(f"DC | neither truncated nor empty: {n(cal_cond,'KAN')}/{len(cal_cond)}   "
          f"DC | not truncated: {n(cal_nolen,'KAN')}/{len(cal_nolen)}   "
          f"DC unconditional: {n(cal,'KAN')}/{len(cal)}")
    print(f"controls (KAN): {n(ctl,'KAN')}/{len(ctl)}")
    fails = [r for r in jmp if r["class"] != "ADM"]
    print(f"jump failures: {len(fails)} = {sum(is_trunc(r) for r in fails)} truncated + "
          f"{sum((not is_trunc(r)) and is_empty(r) for r in fails)} empty + "
          f"{n(fails,'RULE_VIOL')} rule violations + {n(fails,'VALID_OTHER')} valid-but-inadmissible "
          f"(+ {sum(r['class']=='INVALID' and not is_trunc(r) and not is_empty(r) for r in fails)} other invalid)")
    for rd in sorted({r["rendering"] for r in rows}):
        if rd == "factory": continue
        for iid in sorted({r["instance"] for r in rows if r["rendering"] == rd}):
            xs = [r for r in jmp if r["rendering"] == rd and r["instance"] == iid]
            print(f"wording arm {rd} {iid}: jump ADM {n(xs,'ADM')}/{len(xs)}")


if __name__ == "__main__":
    main()
