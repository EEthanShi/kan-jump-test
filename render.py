#!/usr/bin/env python3
"""render.py -- prompt rendering for generated jump instances.

render(instance, rendering, variant) -> prompt text, for
  variant in {calibration, jump, control}, rendering in {factory, library}.

Conventions follow code/pilot_v1/prompts_b/jump.txt:
  - cover stories with no filter-risky words (no signal/pipeline/hidden/
    implementation and similar);
  - nonce CVCV station and move names, freshly sampled per instance
    (deterministic per (m, ps, rendering, seed_tag));
  - answer format: per hidden station, its state-set line, its incoming-map
    line, its internal-move line, and (after the last station) the outgoing
    line, with per-station slot prefixes q{i}_1, q{i}_2, ...;
  - the three variants are format-matched: the same serialization with the
    same names, differing only inside the requirements block (2 lines per
    hidden station in every variant); calibration uses neutral formatting
    requirements, control uses the at-most-1-state requirement per station.
"""
import random

CONSONANTS = "bdfgjklmnprstvz"
VOWELS = "aiou"

# real-word / awkward CVCV strings to avoid (letters above only)
BLOCKLIST = {
    'baba', 'bada', 'bibi', 'bobo', 'bubu', 'dada', 'didi', 'dodo', 'dudu',
    'fifi', 'fufu', 'gaga', 'gala', 'gigi', 'gogo', 'gugu', 'guru', 'java',
    'jiji', 'jojo', 'judo', 'juju', 'kaka', 'kava', 'kiki', 'koko', 'kudu',
    'kuru', 'lama', 'lava', 'lila', 'lima', 'lobo', 'logo', 'lulu', 'mama',
    'mana', 'masa', 'mimi', 'mojo', 'mono', 'nada', 'nana', 'nina', 'nono',
    'papa', 'pipi', 'polo', 'popo', 'puma', 'rasa', 'riri', 'saga', 'sala',
    'sisi', 'sisu', 'solo', 'soso', 'sumo', 'susu', 'tata', 'titi', 'toto',
    'tuba', 'tuna', 'tutu', 'vava', 'visa', 'vita', 'vivo', 'zaza', 'zizi',
    'zulu', 'dojo', 'bono', 'sofa', 'silo', 'nova', 'zero', 'kilo', 'memo',
    'veto', 'boba', 'toga', 'tofu', 'bubo', 'kobo', 'sago', 'dado',
}

RISKY_WORDS = ('signal', 'pipeline', 'hidden', 'implementation', 'covert',
               'secret', 'cipher', 'payload', 'exploit', 'wiring',
               'engineering', 'cyber', 'attack')

RENDERINGS = ('factory', 'library')
VARIANTS = ('calibration', 'jump', 'control')

WORDS = {
    'factory': {
        'setting': 'a small toy sorting line',
        'mover': 'Toys', 'station': 'station', 'stations': 'stations',
        'unit': 'slot', 'units': 'slots', 'system': 'line',
        'internal': 'internal reshuffle',
    },
    'library': {
        'setting': 'a small book sorting row of carts',
        'mover': 'Books', 'station': 'cart', 'stations': 'carts',
        'unit': 'tray', 'units': 'trays', 'system': 'row',
        'internal': 'internal rearrangement',
    },
}

TIMES = {2: 'twice', 3: 'three times'}


def _sample_name(rng, used):
    while True:
        w = (rng.choice(CONSONANTS) + rng.choice(VOWELS)
             + rng.choice(CONSONANTS) + rng.choice(VOWELS))
        if w in BLOCKLIST or w in used:
            continue
        if any(w[:3] == u[:3] for u in used):     # keep names visually distinct
            continue
        used.add(w)
        return w


def make_naming(inst, rendering, seed_tag='v1', global_used=None):
    """Deterministic nonce naming for one (instance, rendering).

    global_used, if given, is a registry shared across instances so that
    nonce names are fresh dataset-wide, not only prompt-locally.
    """
    assert rendering in RENDERINGS
    m = inst['m']
    rng = random.Random(f"gen_v1|{inst['m']}|{inst['ps']}|{rendering}|{seed_tag}")
    used = set() if global_used is None else global_used
    stations = [_sample_name(rng, used).upper() for _ in range(m + 2)]
    chain_moves = [_sample_name(rng, used) for _ in range(m + 1)]
    endo_moves = [_sample_name(rng, used) for _ in range(m)]
    return {
        'rendering': rendering, 'seed_tag': seed_tag,
        'stations': stations,            # [IN, H1..Hm, OUT]
        'chain_moves': chain_moves,      # [a0..am]
        'endo_moves': endo_moves,        # [e1..em]
        'in_slot': 'n1', 'out_slot': 's1',
        'slot_prefixes': [f'q{i}_' for i in range(1, m + 1)],
    }


def _rules_block(inst, nm, W):
    m, ps = inst['m'], inst['ps']
    st, cm, em = nm['stations'], nm['chain_moves'], nm['endo_moves']
    lines = []
    for i in range(1, m + 1):
        H, e = st[i], em[i - 1]
        a_in, a_out = cm[i - 1], cm[i]
        lines.append(
            f'R{i}.1 Running "{a_in}" and then "{e}" lands on the same '
            f'{W["unit"]} as running "{a_in}" alone.')
        lines.append(
            f'     ("{e}" leaves every {W["unit"]} that "{a_in}" produces '
            f'unchanged.)')
        lines.append(
            f'R{i}.2 Running "{e}" and then "{a_out}" gives the same result '
            f'as running "{a_out}" alone.')
        lines.append(
            f'     ("{a_out}" cannot tell whether "{e}" was applied first.)')
        lines.append(
            f'R{i}.3 Running "{e}" {TIMES[ps[i - 1]]} in a row leaves every '
            f'{H} {W["unit"]} exactly where it started.')
    return '\n'.join(lines)


def _requirements_block(inst, nm, W, variant):
    """2 lines per hidden station in every variant (format-matched)."""
    m, ps = inst['m'], inst['ps']
    st, em = nm['stations'], nm['endo_moves']
    lines = []
    for i in range(1, m + 1):
        H, e, pre = st[i], em[i - 1], nm['slot_prefixes'][i - 1]
        neutral1 = (f'D{i}.1 List the {W["units"]} of {H} in increasing index '
                    f'order {pre}1, {pre}2, ... in its set line.')
        neutral2 = (f'D{i}.2 List the "{e}" table entries in {W["unit"]} order '
                    f'{pre}1, {pre}2, ..., one entry per {W["unit"]}.')
        if variant == 'jump':
            lines.append(f'D{i}.1 {H} must be a finite set with at most '
                         f'{1 + ps[i - 1]} {W["units"]}.')
            lines.append(f'D{i}.2 "{e}" must NOT be the do-nothing move (it '
                         f'must move at least one {H} {W["unit"]}).')
        elif variant == 'control':
            lines.append(f'D{i}.1 {H} must be a finite set with at most 1 '
                         f'{W["unit"]}.')
            lines.append(neutral2)
        elif variant == 'calibration':
            lines.append(neutral1)
            lines.append(neutral2)
        else:
            raise ValueError(variant)
    return '\n'.join(lines)


def _format_block(inst, nm, W):
    m = inst['m']
    st, cm, em = nm['stations'], nm['chain_moves'], nm['endo_moves']
    lines = []
    for i in range(1, m + 1):
        H, pre = st[i], nm['slot_prefixes'][i - 1]
        prev_slots = (nm['in_slot'] if i == 1
                      else f"{nm['slot_prefixes'][i - 2]}1")
        lines.append(f'{H} = {{{pre}1, ..., {pre}k}}')
        if i == 1:
            lines.append(f'{cm[0]}: {nm["in_slot"]} -> <{H} {W["unit"]}>')
        else:
            lines.append(f'{cm[i - 1]}: {prev_slots} -> <{H} {W["unit"]}>, '
                         f'... (one entry per {st[i - 1]} {W["unit"]})')
        lines.append(f'{em[i - 1]}: {pre}1 -> <{H} {W["unit"]}>, ..., '
                     f'{pre}k -> <{H} {W["unit"]}>')
    lastpre = nm['slot_prefixes'][m - 1]
    lines.append(f'{cm[m]}: {lastpre}1 -> <{st[m + 1]} {W["unit"]}>, ... '
                 f'(one entry per {st[m]} {W["unit"]})')
    return '\n'.join(lines)


def render(inst, rendering, variant, naming=None, seed_tag='v1'):
    """Render one prompt. Returns (text, naming)."""
    assert variant in VARIANTS
    if naming is None:
        naming = make_naming(inst, rendering, seed_tag)
    nm, W = naming, WORDS[rendering]
    m, N = inst['m'], inst['N']
    st, cm = nm['stations'], nm['chain_moves']
    hidden = st[1:-1]

    arrow_chain = ' -> '.join(st)
    move_lines = []
    for i in range(m + 1):
        move_lines.append(f'- "{cm[i]}" carries each {st[i]} {W["unit"]} to a '
                          f'{st[i + 1]} {W["unit"]}.')
        if i < m:
            e = nm['endo_moves'][i]
            move_lines.append(
                f'- "{e}" is an {W["internal"]} of {st[i + 1]}: it carries '
                f'each {st[i + 1]} {W["unit"]} to a {st[i + 1]} {W["unit"]}.')

    middle_word = ('the middle ' + (W['station'] if m == 1 else W['stations']))
    hidden_list = ', '.join(hidden)

    text = f"""You are completing the design of {W['setting']} with {m + 2} {W['stations']}.

The {W['stations']} are: {', '.join(st)}. {W['mover']} move {arrow_chain}.
There are {2 * m + 1} moving steps:
{chr(10).join(move_lines)}

The {W['system']}'s operating rules. These must hold exactly, {W['unit']} by {W['unit']}:
{_rules_block(inst, nm, W)}

Recorded observations (fixed; your design must reproduce them exactly):
- {st[0]} has exactly one {W['unit']}, called {nm['in_slot']}.
- {st[-1]} has exactly one {W['unit']}, called {nm['out_slot']}.
- The observed end-to-end behavior of the {W['system']} sends {nm['in_slot']} to {nm['out_slot']}.

Requirements for {middle_word} ({hidden_list}):
{_requirements_block(inst, nm, W, variant)}

Your task: give one complete concrete design of {middle_word}.

Answer format bound: designs with up to {N} {W['units']} per middle {W['station']}
are well-formed answers (the requirements above may restrict this further).

Answer in exactly this format (listing every {W['unit']} and every table entry;
for {W['station']} number i in the row, use {W['unit']} names qi_1, qi_2, ...):

{_format_block(inst, nm, W)}

Every rule and requirement above must hold exactly for your tables. Do not
explain; output only the lines in the format above.
"""
    for w in RISKY_WORDS:
        assert w not in text.lower(), f"risky word {w!r} in prompt"
    return text, naming


# ------------------------------------------------- answer text from a functor
def answer_text(inst, naming, F):
    """Serialize an extension F in the required answer format (used for
    answer keys and grader round-trips)."""
    m, chain = inst['m'], inst['chain']
    nm = naming
    lines = []
    for i in range(1, m + 1):
        pre = nm['slot_prefixes'][i - 1]
        n = F[f'id_b{i}'][0]
        slots = [f'{pre}{j + 1}' for j in range(n)]
        lines.append(f"{nm['stations'][i]} = {{{', '.join(slots)}}}")
        inc = F[f'P_{chain[i - 1]}_{chain[i]}']
        if i == 1:
            src = [nm['in_slot']]
        else:
            ppre = nm['slot_prefixes'][i - 2]
            src = [f'{ppre}{j + 1}' for j in range(inc[0])]
        lines.append(f"{nm['chain_moves'][i - 1]}: "
                     + ', '.join(f'{s} -> {slots[inc[2][j]]}'
                                 for j, s in enumerate(src)))
        t = F[f't{i}']
        lines.append(f"{nm['endo_moves'][i - 1]}: "
                     + ', '.join(f'{slots[j]} -> {slots[t[2][j]]}'
                                 for j in range(n)))
    out = F[f'P_{chain[m]}_{chain[m + 1]}']
    lastpre = nm['slot_prefixes'][m - 1]
    lines.append(f"{nm['chain_moves'][m]}: "
                 + ', '.join(f'{lastpre}{j + 1} -> {nm["out_slot"]}'
                             for j in range(out[0])))
    return '\n'.join(lines)
