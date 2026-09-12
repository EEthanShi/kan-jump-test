"""Figures and summary tables for the jump experiments.

Inputs (all optional; a figure is skipped when its data are absent):
  results/results_gen.jsonl            closed models via API (base family, factory + library)
  results_gpu/local_*.jsonl            open models, base family (9 instances, factory + library)
  results_gpu/scaled_*.jsonl           open models, scaled family A2 (dataset_scaled, factory)
  results_gpu/asym_*.jsonl             open models, asymmetric family A3 (dataset_asym)
  results_gpu/logprob_*.jsonl          teacher-forced log-probabilities under the ablated prompt
  dataset*/summary.json                chance levels and configuration of every instance
Outputs: figures/*.pdf|png and figures/summary_*.csv|md.
Figure types follow the field's conventions: per-model accuracy heatmaps with counts, scale
curves with Wilson intervals, paired default-versus-jump bars, stacked failure taxonomies,
accuracy against chance level, paired rendering scatter, and log-probability margins.
"""
import glob, json, math, os, re, sys
from collections import Counter
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import figstyle as fs
from figstyle import wilson, family_of, CLASS_COLOR as CLASS_COLORS, CLASS_LABEL, FAMILY_COLOR, FAMILY_LABEL, FAMILY_MARKER

fs.use_style()
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "figures"); os.makedirs(OUT, exist_ok=True)
RESULTS = "results_gpu" if os.path.isdir(os.path.join(HERE, "results_gpu")) else "results_open"
CLASSES = ["ADM", "KAN", "VALID_OTHER", "RULE_VIOL", "INVALID"]
SHORT = {"anthropic/claude-sonnet-5": "Claude Sonnet 5", "deepseek/deepseek-v4-pro-0813": "DeepSeek V4 Pro",
         "google/gemini-3.1-pro-preview": "Gemini 3.1 Pro", "openai/gpt-5.6-luna-pro": "GPT-5.6 Luna Pro",
         "Qwen/Qwen3-32B": "Qwen3 32B", "RedHatAI/Llama-3.3-70B-Instruct-FP8-dynamic": "Llama 3.3 70B",
         "Qwen/Qwen3-8B": "Qwen3 8B", "Qwen/Qwen3-14B": "Qwen3 14B", "RedHatAI/Qwen2.5-72B-Instruct-FP8-dynamic": "Qwen2.5 72B",
         "Qwen/Qwen3.6-27B": "Qwen3.6 27B", "google/gemma-4-31B-it": "Gemma 4 31B", "Qwen/Qwen3.6-35B-A3B": "Qwen3.6 35B-A3B",
         "google/gemma-4-26B-A4B-it": "Gemma 4 26B-A4B", "openai/gpt-oss-20b": "gpt-oss 20B", "Qwen/Qwen3.5-9B": "Qwen3.5 9B",
         "google/gemma-4-12B-it": "Gemma 4 12B", "Qwen/Qwen3.5-4B": "Qwen3.5 4B"}
PARAMS = {"Qwen/Qwen3-32B": 32, "RedHatAI/Llama-3.3-70B-Instruct-FP8-dynamic": 70, "Qwen/Qwen3-8B": 8, "Qwen/Qwen3-14B": 14,
          "RedHatAI/Qwen2.5-72B-Instruct-FP8-dynamic": 72, "Qwen/Qwen3.6-27B": 27, "google/gemma-4-31B-it": 31,
          "Qwen/Qwen3.6-35B-A3B": 35, "google/gemma-4-26B-A4B-it": 26, "openai/gpt-oss-20b": 20, "Qwen/Qwen3.5-9B": 9,
          "google/gemma-4-12B-it": 12, "Qwen/Qwen3.5-4B": 4}
CLOSED = set(k for k in SHORT if "/" in k and k.split("/")[0] in ("anthropic", "deepseek", "google", "openai") and "gemma" not in k and "oss" not in k)


def short(m): return SHORT.get(m, m.split("/")[-1])


def load_jsonl(paths):
    rows = []
    for p in paths:
        for line in open(p):
            line = line.strip()
            if line:
                r = json.loads(line); r["_file"] = os.path.basename(p); rows.append(r)
    return rows


def load_all():
    try:
        import repair_cot
        repair_cot.main(glob.glob(os.path.join(HERE, RESULTS, "cot_*.jsonl")))
    except Exception as e:
        print(f"!! repair_cot: {type(e).__name__}: {e}")
    meta = {}
    for d in ("dataset", "dataset_scaled", "dataset_asym"):
        p = os.path.join(HERE, d, "summary.json")
        if os.path.exists(p):
            for s in json.load(open(p)):
                s["_family"] = {"dataset": "base", "dataset_scaled": "scaled", "dataset_asym": "asym"}[d]; meta[s["id"]] = s
    df = pd.DataFrame(load_jsonl(glob.glob(os.path.join(HERE, "results", "results_gen.jsonl"))
                                 + glob.glob(os.path.join(HERE, RESULTS, "local_*.jsonl"))
                                 + glob.glob(os.path.join(HERE, RESULTS, "cot_*.jsonl"))
                                 + glob.glob(os.path.join(HERE, RESULTS, "scaled_*.jsonl"))
                                 + glob.glob(os.path.join(HERE, RESULTS, "asym_*.jsonl"))))
    if df.empty: return df, pd.DataFrame(), meta
    df["family"] = df["instance"].map(lambda i: meta.get(i, {}).get("_family", "asym" if i.startswith("asym") else "base"))
    df["cot"] = df["cot"].fillna(False).astype(bool) if "cot" in df.columns else False
    df.loc[df["cot"], "family"] = "cot"
    df["config"] = df["instance"].map(lambda i: meta.get(i, {}).get("config", re.sub(r"_s\d+$", "", i)))
    df["m"] = df["instance"].map(lambda i: meta.get(i, {}).get("m", np.nan))
    df["chance"] = df["instance"].map(lambda i: meta.get(i, {}).get("chance", np.nan))
    df["model_s"] = df["model"].map(short); df["open"] = ~df["model"].isin(CLOSED)
    df["params"] = df["model"].map(PARAMS)
    df["temp"] = df.get("temperature", 0.0)
    lp = pd.DataFrame(load_jsonl(glob.glob(os.path.join(HERE, RESULTS, "logprob_*.jsonl"))))
    return df, lp, meta


def palette(models):
    """Colour by model family, with lightness varying inside a family so lines stay separable."""
    cols = {}
    for fam in ("closed", "reasoning", "plain"):
        ms = [m for m in models if family_of(m) == fam]
        base = matplotlib.colors.to_rgb(FAMILY_COLOR[fam])
        for i, m in enumerate(sorted(ms, key=lambda m: -PARAMS.get(m, 200))):
            t = 0.0 if len(ms) == 1 else 0.55 * i / (len(ms) - 1)
            cols[m] = tuple(c + (1 - c) * t for c in base)
    return cols


def model_order(df):
    """Closed models first, then open ones by size, so every figure lists models in one order."""
    ms = list(df["model"].unique())
    return sorted(ms, key=lambda m: ({"closed": 0, "reasoning": 1, "plain": 2}[family_of(m)], -PARAMS.get(m, 200), m))


def by_accuracy(df, models, variant="jump", cls="ADM"):
    return sorted(models, key=lambda m: -rate(df[(df.model == m) & (df.variant == variant)], cls)[0])


def rate(sub, cls):
    n = len(sub); k = int((sub["class"] == cls).sum()); p, lo, hi = wilson(k, n)
    if n: lo, hi = min(lo, p), max(hi, p)
    return (p, lo, hi, k, n)


# ---------------------------------------------------------------- tables
def summary_table(df):
    rows = []
    for fam in ["base", "cot", "scaled"]:
        d = df[df.family == fam]
        for m in model_order(d):
            dm = d[d.model == m]; cal = dm[dm.variant == "calibration"]; jmp = dm[dm.variant == "jump"]; ctl = dm[dm.variant == "control"]
            dc = rate(cal, "KAN"); kd = rate(jmp, "KAN"); acc = rate(jmp, "ADM"); cp = rate(ctl, "KAN")
            trunc = int((jmp["finish"] != "stop").sum()) if "finish" in jmp else 0
            rows.append({"family": fam, "model": short(m), "open": m not in CLOSED,
                         "DC": dc[0], "DC_lo": dc[1], "DC_hi": dc[2], "n_cal": dc[4],
                         "KD": kd[0], "KD_lo": kd[1], "KD_hi": kd[2], "KD_k": kd[3], "n_jump": kd[4],
                         "jump_acc": acc[0], "acc_lo": acc[1], "acc_hi": acc[2],
                         "control": cp[0], "n_ctrl": cp[4], "jump_truncated": trunc,
                         **{f"jump_{c}": int((jmp["class"] == c).sum()) for c in CLASSES}})
    t = pd.DataFrame(rows)
    if t.empty: return t
    t.to_csv(os.path.join(OUT, "summary_models.csv"), index=False)
    with open(os.path.join(OUT, "summary_models.md"), "w") as f:
        f.write("| family | model | DC (n) | KD (n) | jump acc [95% CI] | control (n) | jump classes ADM/KAN/VO/RV/INV |\n|---|---|---|---|---|---|---|\n")
        for _, r in t.iterrows():
            f.write(f"| {r.family} | {r.model} | {r.DC:.2f} ({r.n_cal}) | {r.KD_k}/{r.n_jump} | {r.jump_acc:.2f} [{r.acc_lo:.2f}, {r.acc_hi:.2f}] | {r.control:.2f} ({r.n_ctrl}) | "
                    f"{r.jump_ADM}/{r.jump_KAN}/{r.jump_VALID_OTHER}/{r.jump_RULE_VIOL}/{r.jump_INVALID} |\n")
    return t


# ---------------------------------------------------------------- figures
def _label_rows(ax, models, counts=None):
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels([short(m) for m in models])
    for t, m in zip(ax.get_yticklabels(), models):
        t.set_color(FAMILY_COLOR[family_of(m)])
    ax.invert_yaxis()
    ax.tick_params(axis="y", length=0)


def place_labels(ax, points, fontsize=5.6):
    """Greedy label placement in display space: try a few offsets per point and keep the first
    that clears the labels already placed, so no annotation covers another."""
    ax.figure.canvas.draw()
    dpi = ax.figure.dpi
    bb = ax.get_window_extent()
    inside = (bb.x0 + 1, bb.y0 + 1, bb.x1 - 1, bb.y1 - 1)   # labels stay within the panel
    boxes = []
    cands = [(sx * 5, sy * r) for r in (2, 9, 16, 24, 33, 43, 54, 66) for sx in (1, -1) for sy in (1, -1)]
    for x, y, text, col in points:
        px, py = ax.transData.transform((x, y))
        placed = False
        w = 0.52 * fontsize * len(text) * dpi / 72.0        # rough advance width of a serif face
        h = 1.25 * fontsize * dpi / 72.0
        for dx, dy in cands:
            ox, oy = px + dx * dpi / 72.0, py + dy * dpi / 72.0
            x0 = ox if dx > 0 else ox - w
            box = (x0, oy - h / 2, x0 + w, oy + h / 2)
            if not (inside[0] <= box[0] and box[2] <= inside[2] and inside[1] <= box[1] and box[3] <= inside[3]):
                continue
            if all(box[2] < b[0] or box[0] > b[2] or box[3] < b[1] or box[1] > b[3] for b in boxes):
                boxes.append(box)
                far = abs(dx) > 6 or abs(dy) > 10          # a displaced label needs a leader line
                ax.annotate(text, (x, y), textcoords="offset points", xytext=(dx, dy), fontsize=fontsize,
                            color=col, ha="left" if dx > 0 else "right", va="center", annotation_clip=False,
                            arrowprops=dict(arrowstyle="-", lw=0.35, color=col, shrinkA=0, shrinkB=3) if far else None)
                placed = True
                break
        if not placed:
            ax.annotate(text, (x, y), textcoords="offset points", xytext=(5, 2), fontsize=fontsize,
                        color=col, ha="left", va="center", annotation_clip=False)


def fig_instrument(df):
    """Default under free choice, default under falsifying constraints, and jump accuracy."""
    d = df[df.family.isin(["base", "scaled"])]
    if d.empty: return
    models = by_accuracy(d, model_order(d))
    fig, axes = plt.subplots(1, 2, figsize=(fs.TEXT_W, 0.20 * len(models) + 1.15),
                             gridspec_kw={"width_ratios": [2.5, 1], "wspace": 0.08})
    ax = axes[0]
    for i, m in enumerate(models):
        dm = d[d.model == m]
        dc = rate(dm[dm.variant == "calibration"], "KAN")
        ac = rate(dm[dm.variant == "jump"], "ADM")
        col = FAMILY_COLOR[family_of(m)]
        ax.plot([dc[0], ac[0]], [i, i], color=col, lw=0.8, alpha=0.45, zorder=1)
        ax.errorbar(dc[0], i, xerr=fs.err(*dc[:3]), fmt="o", mfc="white", mec=col, ecolor=col,
                    ms=4, mew=0.9, elinewidth=0.7, capsize=1.4, zorder=3)
        ax.errorbar(ac[0], i, xerr=fs.err(*ac[:3]), fmt="o", color=col, ecolor=col,
                    ms=4, elinewidth=0.7, capsize=1.4, zorder=3)
    fs.rate_axis(ax, "x", "rate")
    _label_rows(ax, models)
    ax.set_xlabel("rate")
    handles = [Line2D([], [], marker="o", color=fs.INK, mfc="white", mec=fs.INK, ls="none", ms=4, label="default under free choice"),
               Line2D([], [], marker="o", color=fs.INK, ls="none", ms=4, label="jump accuracy")]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 1.005), ncol=2)
    fs.panel_tag(ax, "a", dx=-0.30)

    ax = axes[1]
    bounds = []
    for i, m in enumerate(models):
        dm = d[(d.model == m) & (d.variant == "jump")]
        p, lo, hi, k, n = rate(dm, "KAN")
        bounds.append(hi)
        col = FAMILY_COLOR[family_of(m)]
        ax.barh(i, hi, height=0.5, color=col, alpha=0.30, edgecolor="none")
        ax.plot([p], [i], marker="|", color=col, ms=6, mew=1.0)
        ax.text(hi + 0.0015, i, f"{k}/{n}", va="center", ha="left", fontsize=6, color=fs.INK)
    top = max(bounds) * 1.45
    ax.set_xlim(0, top)
    ticks = [0, 0.02, 0.04, 0.06] if top > 0.05 else [0, 0.01, 0.02, 0.03]
    ax.set_xticks([t for t in ticks if t <= top])
    ax.set_xticklabels([("0" if t == 0 else f"{t:.2f}".lstrip("0")) for t in ticks if t <= top])
    fs.ygrid(ax, "x")
    ax.set_yticks(range(len(models))); ax.set_yticklabels([]); ax.invert_yaxis(); ax.tick_params(axis="y", length=0)
    ax.set_xlabel("default rate,\n95% upper bound")
    fs.panel_tag(ax, "b", dx=-0.06)
    fs.save(fig, OUT, "fig_instrument")


def fig_difficulty(df):
    """Jump accuracy against the certified chance level, one panel per model."""
    d = df[(df.variant == "jump") & df.family.isin(["base", "scaled"]) & (df.rendering == "factory")]
    if d.empty: return
    models = model_order(d)
    curves = {}
    for m in models:
        pts = []
        for cfg, s_ in d[d.model == m].groupby("config"):
            p, lo, hi, k, n = rate(s_, "ADM")
            pts.append((-math.log10(s_.chance.iloc[0]), p, p - lo, hi - p))
        pts.sort()
        curves[m] = tuple(map(np.array, zip(*pts)))
    ncol = 5
    nrow = int(math.ceil(len(models) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(fs.TEXT_W, 1.15 * nrow + 0.35),
                             sharex=True, sharey=True, gridspec_kw={"wspace": 0.12, "hspace": 0.30})
    axes = np.atleast_2d(axes)
    for k_, m in enumerate(models):
        ax = axes[k_ // ncol][k_ % ncol]
        for other in models:
            if other == m: continue
            x, y, _, _ = curves[other]
            ax.plot(x, y, color="#DCDCDC", lw=0.5, zorder=1)
        x, y, e0, e1 = curves[m]
        col = FAMILY_COLOR[family_of(m)]
        ax.errorbar(x, y, yerr=[np.maximum(e0, 0), np.maximum(e1, 0)], color=col,
                    marker=FAMILY_MARKER[family_of(m)], ms=2.2, lw=1.0, elinewidth=0.45, capsize=0, zorder=3)
        ax.set_title(short(m), fontsize=6.2, color=col, pad=2, loc="left")
        ax.set_xlim(0.5, 9.8); ax.set_xticks([2, 5, 8])
        ax.set_ylim(-0.03, 1.05); ax.set_yticks([0, 0.5, 1.0]); ax.set_yticklabels(["0", ".5", "1"])
        fs.ygrid(ax)
    for k_ in range(len(models), nrow * ncol):
        axes[k_ // ncol][k_ % ncol].axis("off")
    for r in range(nrow):
        axes[r][0].set_ylabel("jump accuracy")
    fig.supxlabel(r"difficulty of the instance,  $-\log_{10}$ chance level", fontsize=8, y=0.02)
    fs.save(fig, OUT, "fig_difficulty")


def fig_size(df):
    """Pooled jump accuracy against parameter count, open models only."""
    d = df[(df.variant == "jump") & df.family.isin(["base", "scaled"]) & df.params.notna()]
    if d.empty: return
    fig, ax = plt.subplots(figsize=(fs.HALF_W, fs.HALF_W * 0.80))
    pts = []
    for m in model_order(d):
        dm = d[d.model == m]
        p, lo, hi, k, n = rate(dm, "ADM")
        fam = family_of(m); col = FAMILY_COLOR[fam]
        ax.errorbar(PARAMS[m], p, yerr=fs.err(p, lo, hi), fmt=FAMILY_MARKER[fam], color=col,
                    ms=4, elinewidth=0.7, capsize=1.4, zorder=3)
        pts.append((PARAMS[m], p, m, col))
    place_labels(ax, [(x, y, short(m), col) for x, y, m, col in sorted(pts, key=lambda t: -t[1])])
    ax.set_xscale("log"); ax.set_xlim(3, 160)
    ax.set_xticks([4, 10, 30, 70]); ax.set_xticklabels(["4", "10", "30", "70"])
    ax.set_xlabel("parameters (B)")
    fs.rate_axis(ax, "y", "pooled jump accuracy")
    ax.set_ylim(-0.06, 1.06)
    fs.family_legend(ax, [f for f in ("reasoning", "plain") if any(family_of(m) == f for m in d.model.unique())],
                     loc="upper left", bbox_to_anchor=(-0.02, 1.16), ncol=2)
    fs.save(fig, OUT, "fig_size")


def fig_taxonomy(df, fam="scaled"):
    """What the jump answers are, by difficulty."""
    d = df[(df.family == fam) & (df.variant == "jump")]
    if d.empty: return
    ms_all = sorted(d.m.dropna().unique())
    models = by_accuracy(d, model_order(d))
    fig, axes = plt.subplots(1, len(ms_all), figsize=(fs.TEXT_W, 0.16 * len(models) + 1.15),
                             sharey=True, gridspec_kw={"wspace": 0.07})
    axes = np.atleast_1d(axes)
    for ax, mm in zip(axes, ms_all):
        left = np.zeros(len(models))
        for c in CLASSES:
            vals = np.array([((d.model == m) & (d.m == mm) & (d["class"] == c)).sum()
                             / max(1, ((d.model == m) & (d.m == mm)).sum()) for m in models])
            ax.barh(range(len(models)), vals, left=left, height=0.68, color=CLASS_COLORS[c],
                    edgecolor="white", linewidth=0.3)
            left += vals
        n_cell = int((d.m == ms_all[0]).sum() / max(1, len(models)))
        ax.set_title(f"$m={int(mm)}$", pad=3)
        ax.set_xlim(0, 1); ax.set_xticks([0, 0.5, 1]); ax.set_xticklabels(["0", ".5", "1"])
        ax.tick_params(axis="y", length=0)
    fig.supxlabel("share of jump answers", fontsize=8, y=0.005)
    _label_rows(axes[0], models)
    fs.class_legend(axes[0], CLASSES, ncol=5, loc="lower left", bbox_to_anchor=(0.0, 1.10))
    fs.save(fig, OUT, f"fig_taxonomy_{fam}")


def fig_scratchpad(df):
    """The same models with and without room to reason before answering."""
    b = df[(df.family == "base") & (df.rendering == "factory")]
    c = df[df.family == "cot"]
    if c.empty: return
    models = [m for m in model_order(c) if m in set(b.model)]
    fig, axes = plt.subplots(1, 2, figsize=(fs.TEXT_W * 0.82, 2.3), sharey=True, gridspec_kw={"wspace": 0.35})
    for ax, (variant, cls, name) in zip(axes, [("jump", "ADM", "jump accuracy"),
                                               ("calibration", "KAN", "default under free choice")]):
        ends = []
        for m in models:
            p0 = rate(b[(b.model == m) & (b.variant == variant)], cls)
            p1 = rate(c[(c.model == m) & (c.variant == variant)], cls)
            col = FAMILY_COLOR[family_of(m)]
            ax.plot([0, 1], [p0[0], p1[0]], color=col, lw=1.0, marker="o", ms=3, alpha=0.9)
            ends.append([p1[0], m, col])
        ends.sort()
        gap = 0.055                                   # keep end labels from overlapping
        for i in range(1, len(ends)):
            if ends[i][0] - ends[i - 1][0] < gap:
                ends[i][0] = ends[i - 1][0] + gap
        over = ends[-1][0] - 1.0                      # keep the stack clear of the panel title
        if over > 0:
            for e in ends:
                e[0] -= over
        for y, m, col in ends:
            ax.annotate(short(m), (1.06, y), textcoords="offset points", xytext=(0, 0),
                        fontsize=5.8, color=col, va="center", ha="left", annotation_clip=False)
        ax.set_xlim(-0.12, 1.55); ax.set_xticks([0, 1])
        ax.set_xticklabels(["no\nexplanation", "reasoning\npermitted"])
        ax.set_title(name, pad=3)
        fs.rate_axis(ax, "y")
        ax.tick_params(axis="x", length=0)
    axes[0].set_ylabel("rate")
    fs.save(fig, OUT, "fig_scratchpad")


def fig_heatmap(df):
    """Every certified instance of the base family, by model."""
    d = df[(df.family == "base") & (df.rendering == "factory")]
    if d.empty: return
    models = by_accuracy(d, model_order(d))
    insts = sorted(d.instance.unique(), key=lambda i: (d[d.instance == i].chance.iloc[0], i), reverse=True)
    fig, axes = plt.subplots(1, 2, figsize=(fs.TEXT_W, 0.22 * len(models) + 1.25), sharey=True,
                             gridspec_kw={"wspace": 0.06})
    for ax, (variant, cls, name, cmap) in zip(axes, [("jump", "ADM", "jump arm: admissible", "Greens"),
                                                     ("calibration", "KAN", "calibration arm: canonical", "Oranges")]):
        M = np.full((len(models), len(insts)), np.nan); N = np.zeros_like(M, dtype=int)
        for i, m in enumerate(models):
            for j, it in enumerate(insts):
                s = d[(d.model == m) & (d.instance == it) & (d.variant == variant)]
                if len(s): M[i, j] = (s["class"] == cls).mean(); N[i, j] = len(s)
        ax.imshow(M, vmin=0, vmax=1, cmap=cmap, aspect="auto", interpolation="nearest")
        for i in range(len(models)):
            for j in range(len(insts)):
                if N[i, j]:
                    ax.text(j, i, f"{M[i, j]:.2f}".lstrip("0"), ha="center", va="center", fontsize=5.6,
                            color="white" if M[i, j] > 0.62 else fs.INK)
        ax.set_xticks(range(len(insts)))
        labels = []
        for it in insts:
            ch = d[d.instance == it].chance.iloc[0]
            mm = int(d[d.instance == it].m.iloc[0])
            ps = it.split("_p")[-1]
            labels.append(f"$m{{=}}{mm}$, $p{{=}}{ps}$\n{ch:.0e}".replace("e-0", "e-"))
        ax.set_xticklabels(labels, rotation=90, fontsize=5.4)
        ax.set_xlabel("instance and chance level")
        ax.set_title(name, pad=3)
        ax.set_xticks(np.arange(-0.5, len(insts), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(models), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=0.6)
        ax.tick_params(which="minor", length=0)
    axes[0].set_yticks(range(len(models)))
    axes[0].set_yticklabels([short(m) for m in models])
    for t, m in zip(axes[0].get_yticklabels(), models):
        t.set_color(FAMILY_COLOR[family_of(m)])
    axes[0].tick_params(axis="y", length=0)
    fs.save(fig, OUT, "fig_heatmap")


def fig_logprob(lp):
    """Teacher-forced preference between the admissible answer and the canonical one."""
    if lp.empty: return
    piv = lp.pivot_table(index=["model", "instance", "rendering"], columns="candidate", values="sum_logprob").reset_index()
    adm = next((c for c in piv.columns if "admissible" in str(c)), None)
    kan = [c for c in ("kan", "lan", "ran") if c in piv.columns]
    if adm is None or not kan: return
    piv["margin"] = piv[adm] - piv[kan].max(axis=1)
    models = sorted(piv.model.unique(), key=lambda m: np.median(piv[piv.model == m].margin))
    fig, ax = plt.subplots(figsize=(fs.TEXT_W * 0.74, 0.20 * len(models) + 0.95))
    allv = piv.margin.dropna().values
    lo_lim = float(np.percentile(allv, 2)) - 6
    hi_lim = max(6.0, float(allv.max()) + 3)
    for i, m in enumerate(models):
        v = piv[piv.model == m].margin.dropna().values
        col = FAMILY_COLOR[family_of(m)]
        inside = v[v >= lo_lim]
        ax.scatter(inside, np.full(len(inside), i) + np.linspace(-0.17, 0.17, len(inside)), s=5,
                   color=col, alpha=0.55, linewidths=0, zorder=3)
        below = int((v < lo_lim).sum())
        if below:
            ax.plot([lo_lim + 0.6], [i], marker="<", ms=3, color=col, zorder=4)
            ax.annotate(f"{below}", (lo_lim + 1.6, i), fontsize=5.6, color=col, va="center", ha="left")
        med = np.median(v)
        ax.plot([max(med, lo_lim)], [i], marker="|", ms=11, mew=1.4, color=col, zorder=4)
        ax.annotate(f"{int((v > 0).sum())}/{len(v)}", (1.015, i), xycoords=("axes fraction", "data"),
                    fontsize=6, va="center", ha="left", color=fs.INK, annotation_clip=False)
    ax.axvline(0, color=fs.INK, lw=0.7, ls=(0, (2, 2)), zorder=2)
    ax.set_xlim(lo_lim, hi_lim)
    _label_rows(ax, models)
    ax.set_xlabel(r"$\log P(\mathrm{admissible}) - \log P(\mathrm{canonical})$   (nats, no constraints)")
    ax.annotate("admissible\nanswer wins", (1.015, -0.9), xycoords=("axes fraction", "data"), fontsize=6,
                va="center", ha="left", color=fs.INK, annotation_clip=False)
    fs.ygrid(ax, "x")
    fs.save(fig, OUT, "fig_logprob")


def fig_rendering(df):
    """The same instances under two cover stories."""
    d = df[(df.family == "base") & (df.variant.isin(["jump", "calibration"]))]
    both = d.groupby(["model", "instance", "variant"]).rendering.nunique()
    both = both[both == 2].reset_index()
    if both.empty: return
    fig, axes = plt.subplots(1, 2, figsize=(fs.TEXT_W * 0.78, 2.2), gridspec_kw={"wspace": 0.30})
    for ax, (variant, cls, name) in zip(axes, [("jump", "ADM", "jump accuracy"),
                                               ("calibration", "KAN", "default under free choice")]):
        for m in model_order(d):
            counts = Counter()
            for it in both[(both.model == m) & (both.variant == variant)].instance:
                s_ = d[(d.model == m) & (d.instance == it) & (d.variant == variant)]
                counts[(round(float((s_[s_.rendering == "factory"]["class"] == cls).mean()), 3),
                        round(float((s_[s_.rendering == "library"]["class"] == cls).mean()), 3))] += 1
            if counts:
                xy = np.array(list(counts.keys())); w = np.array(list(counts.values()))
                fam = family_of(m)
                ax.scatter(xy[:, 0], xy[:, 1], s=9 + 7 * w, color=FAMILY_COLOR[fam],
                           marker=FAMILY_MARKER[fam], alpha=0.65, linewidths=0, zorder=3)
        ax.plot([0, 1], [0, 1], color=fs.RULE, lw=0.7, ls=(0, (2, 2)), zorder=0)
        ax.set_aspect("equal")
        fs.rate_axis(ax, "x", "factory story"); fs.rate_axis(ax, "y", "library story")
        ax.set_title(name, pad=3)
    fs.family_legend(axes[0], loc="upper left", bbox_to_anchor=(0.0, -0.22), ncol=3)
    axes[1].annotate("marker area grows with the number of instances at that point",
                     (0.5, -0.28), xycoords="axes fraction", fontsize=5.8, ha="center", color=fs.INK)
    fs.save(fig, OUT, "fig_rendering")


def fig_asym(df):
    """The asymmetric family, where the left and right Kan extensions differ."""
    d = df[df.family == "asym"]
    if d.empty: return
    models = by_accuracy(d, model_order(d))
    fig, axes = plt.subplots(1, 3, figsize=(fs.TEXT_W, 0.18 * len(models) + 1.35),
                             sharey=True, gridspec_kw={"wspace": 0.08, "width_ratios": [1, 1, 1]})
    order_cal = ["LAN", "RAN", "ADM", "VALID_OTHER", "RULE_VIOL", "INVALID"]
    order_jmp = ["ADM", "LAN", "RAN", "VALID_OTHER", "RULE_VIOL", "INVALID"]
    for ax, (variant, order, name) in zip(axes[:2], [("calibration", order_cal, "calibration"),
                                                     ("jump", order_jmp, "jump")]):
        left = np.zeros(len(models))
        for c in order:
            vals = np.array([((d.model == m) & (d.variant == variant) & (d["class"] == c)).sum()
                             / max(1, ((d.model == m) & (d.variant == variant)).sum()) for m in models])
            ax.barh(range(len(models)), vals, left=left, height=0.68, color=CLASS_COLORS[c],
                    edgecolor="white", linewidth=0.3)
            left += vals
        ax.set_xlim(0, 1); ax.set_xticks([0, 0.5, 1]); ax.set_xticklabels(["0", ".5", "1"])
        ax.set_xlabel("share of answers"); ax.set_title(name, pad=3, loc="left"); ax.tick_params(axis="y", length=0)
    ax = axes[2]
    for i, m in enumerate(models):
        dm = d[d.model == m]
        r = rate(dm[dm.variant == "control_ran"], "RAN"); l = rate(dm[dm.variant == "control_lan"], "LAN")
        ax.errorbar(l[0], i - 0.16, xerr=fs.err(*l[:3]), fmt="o", color=CLASS_COLORS["LAN"], ms=3.2,
                    elinewidth=0.6, capsize=1.2)
        ax.errorbar(r[0], i + 0.16, xerr=fs.err(*r[:3]), fmt="s", color=CLASS_COLORS["RAN"], ms=3.2,
                    elinewidth=0.6, capsize=1.2)
    fs.rate_axis(ax, "x", "control pass rate")
    ax.set_xlim(-0.04, 1.06)
    ax.set_title("controls", pad=3); ax.tick_params(axis="y", length=0)
    ax.legend(handles=[Line2D([], [], marker="o", ls="none", color=CLASS_COLORS["LAN"], ms=3.2, label="left Kan asked"),
                       Line2D([], [], marker="s", ls="none", color=CLASS_COLORS["RAN"], ms=3.2, label="right Kan asked")],
              loc="upper left", bbox_to_anchor=(0.0, -0.30), ncol=2)
    _label_rows(axes[0], models)
    fs.class_legend(axes[0], ["ADM", "LAN", "RAN", "VALID_OTHER", "RULE_VIOL", "INVALID"], ncol=6,
                    loc="lower left", bbox_to_anchor=(0.0, 1.09))
    fs.save(fig, OUT, "fig_asym")
    rows = []
    for m in models:
        dm = d[d.model == m]
        rows.append({"model": short(m),
                     **{f"cal_{c}": int(((dm.variant == "calibration") & (dm["class"] == c)).sum()) for c in order_cal},
                     "n_cal": int((dm.variant == "calibration").sum()),
                     **{f"jump_{c}": int(((dm.variant == "jump") & (dm["class"] == c)).sum()) for c in order_jmp},
                     "n_jump": int((dm.variant == "jump").sum()),
                     "ctrl_ran_pass": rate(dm[dm.variant == "control_ran"], "RAN")[0],
                     "ctrl_lan_pass": rate(dm[dm.variant == "control_lan"], "LAN")[0]})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "summary_asym.csv"), index=False)


def main():
    df, lp, meta = load_all()
    if df.empty: print("no results found"); return
    print(f"{len(df)} graded rows, {df.model.nunique()} models, families {dict(Counter(df.family))}, logprob rows {len(lp)}")
    t = summary_table(df)
    if not t.empty:
        print(t[["family", "model", "DC", "n_cal", "KD_k", "n_jump", "jump_acc", "control"]].to_string(index=False))
    for fn in (fig_instrument, fig_difficulty, fig_size, fig_scratchpad, fig_heatmap, fig_rendering, fig_asym):
        try: fn(df)
        except Exception as e: print(f"!! {fn.__name__}: {type(e).__name__}: {e}")
    for fam in ("base", "cot", "scaled"):
        try: fig_taxonomy(df, fam)
        except Exception as e: print(f"!! fig_taxonomy {fam}: {type(e).__name__}: {e}")
    try: fig_logprob(lp)
    except Exception as e: print(f"!! fig_logprob: {type(e).__name__}: {e}")
    print("figures:", sorted(f for f in os.listdir(OUT) if f.endswith(".png")))


if __name__ == "__main__":
    main()
