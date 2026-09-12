"""Prompts for the asymmetric-data family (A3), mirroring render.py's wording and format so
that prompts are comparable with the pointed-chain family. One hidden station; k input units,
l output units; the observation sends every input unit to the first output unit.
Variants: calibration, jump, control_ran (pins the output copy), control_lan (pins the input copy).
Every variant carries four D-lines so prompt shape is matched across arms.
"""
import render
from render import WORDS, RISKY_WORDS, TIMES

VARIANTS = ('calibration', 'jump', 'control_ran', 'control_lan')


def make_naming(k, l, rendering, seed_tag='v1', global_used=None):
    pseudo = {'m': 1, 'ps': (2,)}
    nm = render.make_naming(pseudo, rendering, seed_tag=f'asym{k}x{l}_{seed_tag}', global_used=global_used)
    nm['in_slots'] = [f'n{i + 1}' for i in range(k)]
    nm['out_slots'] = [f's{j + 1}' for j in range(l)]
    nm['k'], nm['l'] = k, l
    return nm


def _rules(nm, W):
    H, e = nm['stations'][1], nm['endo_moves'][0]
    a_in, a_out = nm['chain_moves'][0], nm['chain_moves'][1]
    return '\n'.join([
        f'R1.1 Running "{a_in}" and then "{e}" lands on the same {W["unit"]} as running "{a_in}" alone.',
        f'     ("{e}" leaves every {W["unit"]} that "{a_in}" produces unchanged.)',
        f'R1.2 Running "{e}" and then "{a_out}" gives the same result as running "{a_out}" alone.',
        f'     ("{a_out}" cannot tell whether "{e}" was applied first.)',
        f'R1.3 Running "{e}" {TIMES[2]} in a row leaves every {H} {W["unit"]} exactly where it started.'])


def _requirements(nm, W, variant, N):
    st, e, pre = nm['stations'], nm['endo_moves'][0], 'q1_'
    H, IN, OUT = st[1], st[0], st[2]
    a_in, a_out = nm['chain_moves'][0], nm['chain_moves'][1]
    k, l = nm['k'], nm['l']
    size = lambda n: f'D1.1 {H} must be a finite set with at most {n} {W["units"] if n != 1 else W["unit"]}.'
    neutral = [f'D1.1 List the {W["units"]} of {H} in increasing index order {pre}1, {pre}2, ... in its set line.',
               f'D1.2 List the "{e}" table entries in {W["unit"]} order {pre}1, {pre}2, ..., one entry per {W["unit"]}.',
               f'D1.3 List the "{a_in}" table entries in {IN} {W["unit"]} order {", ".join(nm["in_slots"])}.',
               f'D1.4 List the "{a_out}" table entries in {H} {W["unit"]} order {pre}1, {pre}2, ...']
    nontriv = f'D1.2 "{e}" must NOT be the do-nothing move (it must move at least one {H} {W["unit"]}).'
    mono = f'D1.3 "{a_in}" must carry different {IN} {W["units"]} to different {H} {W["units"]}.'
    epi = f'D1.4 Every {OUT} {W["unit"]} must be reached by "{a_out}" from at least one {H} {W["unit"]}.'
    if variant == 'jump':
        return '\n'.join([size(N), nontriv, mono, epi])
    if variant == 'control_ran':
        return '\n'.join([size(l), neutral[1], neutral[2], epi])
    if variant == 'control_lan':
        return '\n'.join([size(k), neutral[1], mono, neutral[3]])
    if variant == 'calibration':
        return '\n'.join(neutral)
    raise ValueError(variant)


def _format(nm, W):
    st, cm, e, pre = nm['stations'], nm['chain_moves'], nm['endo_moves'][0], 'q1_'
    H = st[1]
    return '\n'.join([
        f'{H} = {{{pre}1, ..., {pre}k}}',
        f'{cm[0]}: ' + ', '.join(f'{s} -> <{H} {W["unit"]}>' for s in nm['in_slots']),
        f'{e}: {pre}1 -> <{H} {W["unit"]}>, ..., {pre}k -> <{H} {W["unit"]}>',
        f'{cm[1]}: {pre}1 -> <{st[2]} {W["unit"]}>, ... (one entry per {H} {W["unit"]})'])


def render_asym(k, l, N, rendering, variant, naming=None, seed_tag='v1'):
    assert variant in VARIANTS
    nm = naming or make_naming(k, l, rendering, seed_tag)
    W = WORDS[rendering]
    st, cm, e = nm['stations'], nm['chain_moves'], nm['endo_moves'][0]
    units = lambda n: W['units'] if n != 1 else W['unit']
    obs = ', '.join(f'{s} to {nm["out_slots"][0]}' for s in nm['in_slots'])
    text = f"""You are completing the design of {W['setting']} with 3 {W['stations']}.

The {W['stations']} are: {', '.join(st)}. {W['mover']} move {' -> '.join(st)}.
There are 3 moving steps:
- "{cm[0]}" carries each {st[0]} {W["unit"]} to a {st[1]} {W["unit"]}.
- "{e}" is an {W["internal"]} of {st[1]}: it carries each {st[1]} {W["unit"]} to a {st[1]} {W["unit"]}.
- "{cm[1]}" carries each {st[1]} {W["unit"]} to a {st[2]} {W["unit"]}.

The {W['system']}'s operating rules. These must hold exactly, {W['unit']} by {W['unit']}:
{_rules(nm, W)}

Recorded observations (fixed; your design must reproduce them exactly):
- {st[0]} has exactly {k} {units(k)}, called {', '.join(nm['in_slots'])}.
- {st[2]} has exactly {l} {units(l)}, called {', '.join(nm['out_slots'])}.
- The observed end-to-end behavior of the {W['system']} sends {obs}.

Requirements for the middle {W['station']} ({st[1]}):
{_requirements(nm, W, variant, N)}

Your task: give one complete concrete design of the middle {W['station']}.

Answer format bound: designs with up to {N} {W['units']} in the middle {W['station']}
are well-formed answers (the requirements above may restrict this further).

Answer in exactly this format (listing every {W['unit']} and every table entry;
use {W['unit']} names q1_1, q1_2, ... for the middle {W['station']}):

{_format(nm, W)}

Every rule and requirement above must hold exactly for your tables. Do not
explain; output only the lines in the format above.
"""
    for w in RISKY_WORDS:
        assert w not in text.lower(), f'risky word {w!r}'
    return text, nm


def answer_text(nm, F):
    """Serialize an engine_asym functor F (keys f, t, g as (m, n, vals))."""
    H, cm, e = nm['stations'][1], nm['chain_moves'], nm['endo_moves'][0]
    n = F['idb'][0]; slots = [f'q1_{j + 1}' for j in range(n)]
    return '\n'.join([
        f"{H} = {{{', '.join(slots)}}}",
        f"{cm[0]}: " + ', '.join(f'{s} -> {slots[F["f"][2][i]]}' for i, s in enumerate(nm['in_slots'])),
        f"{e}: " + ', '.join(f'{slots[j]} -> {slots[F["t"][2][j]]}' for j in range(n)),
        f"{cm[1]}: " + ', '.join(f'{slots[j]} -> {nm["out_slots"][F["g"][2][j]]}' for j in range(n))])


if __name__ == '__main__':
    import engine_asym as ea
    for (k, l, N) in [(2, 1, 4), (1, 2, 3)]:
        nm = make_naming(k, l, 'factory')
        for v in VARIANTS:
            t, _ = render_asym(k, l, N, 'factory', v, nm)
        rep = ea.Inst(k, l, N).certify()
        print(f'--- ({k},{l},{N}) prompts OK; Lan answer:'); print(answer_text(nm, rep['_Lan']))
        print('Ran answer:'); print(answer_text(nm, rep['_Ran']))
        print('one admissible answer:'); print(answer_text(nm, rep['_Adm'][0]))
    print('\n===== 完整 jump prompt 示例 (2,1) ====='); print(render_asym(2, 1, 4, 'factory', 'jump', make_naming(2, 1, 'factory'))[0])
