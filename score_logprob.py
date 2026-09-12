"""Teacher-forced log-probabilities of candidate answers under the ablated (calibration) prompt.

For each instance and rendering, scores log P(answer | prompt) for the two candidate answers
stored in answer_key.json ('kan_answer' and 'example_admissible_answer') with the model run
offline through vLLM (prompt_logprobs). Thinking is disabled in the chat template where the
template supports it, so the number is the probability of answering immediately.
Output: one JSON line per (instance, rendering, candidate).
"""
import argparse, json, os, pathlib, sys, time

HERE = pathlib.Path(__file__).parent


def load_cases(instances, renderings, variant, dataset_dir="dataset"):
    cases = []
    for iid in instances:
        d = HERE / dataset_dir / iid
        key = json.loads((d / "answer_key.json").read_text())
        for rd in renderings:
            prompt = (d / f"prompt_{rd}_{variant}.txt").read_text()
            r = key["renderings"][rd]
            cands = {name[:-len("_answer")]: txt for name, txt in r.items() if name.endswith("_answer")}
            cases.append({"instance": iid, "rendering": rd, "prompt": prompt, "candidates": cands})
    return cases


def chat_prefix(tok, prompt):
    msgs = [{"role": "user", "content": prompt}]
    try:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
    except TypeError:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--instances", required=True)
    ap.add_argument("--renderings", default="factory,library")
    ap.add_argument("--variant", default="calibration")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gpu-util", type=float, default=0.90)
    ap.add_argument("--max-model-len", type=int, default=8192)
    ap.add_argument("--dry-run", action="store_true", help="print cases, load no model")
    ap.add_argument("--dataset-dir", default="dataset")
    a = ap.parse_args()
    cases = load_cases(a.instances.split(","), a.renderings.split(","), a.variant, a.dataset_dir)
    if a.dry_run:
        for c in cases:
            print(c["instance"], c["rendering"], "prompt_chars", len(c["prompt"]),
                  {k: len(v) for k, v in c["candidates"].items()})
        return
    from vllm import LLM, SamplingParams
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model)
    llm = LLM(model=a.model, gpu_memory_utilization=a.gpu_util, max_model_len=a.max_model_len,
              enforce_eager=True)
    sp = SamplingParams(max_tokens=1, prompt_logprobs=0, temperature=0.0)
    out = open(HERE / a.out, "a")
    for c in cases:
        prefix = chat_prefix(tok, c["prompt"])
        n_prefix = len(tok(prefix, add_special_tokens=False).input_ids)
        for name, cand in c["candidates"].items():
            full = prefix + cand
            res = llm.generate([full], sp)[0]
            plp = res.prompt_logprobs  # list aligned with prompt tokens; entry None for first
            toks = plp[n_prefix:]
            lps = []
            for entry in toks:
                if entry is None:
                    continue
                # entry: {token_id: Logprob}; with prompt_logprobs=0 it holds the actual token
                lps.append(max(v.logprob for v in entry.values()))
            rec = {"instance": c["instance"], "rendering": c["rendering"], "model": a.model,
                   "variant": a.variant, "candidate": name, "n_tokens": len(lps),
                   "sum_logprob": sum(lps), "mean_logprob": (sum(lps) / len(lps)) if lps else None,
                   "n_prefix_tokens": n_prefix, "boundary_note": "prefix length from separate tokenization; off by at most one token"}
            out.write(json.dumps(rec) + "\n"); out.flush()
            print(f"{c['instance']:8s} {c['rendering']:8s} {name:10s} tokens={len(lps):4d} sum={sum(lps):9.2f}")
    out.close()


if __name__ == "__main__":
    main()
