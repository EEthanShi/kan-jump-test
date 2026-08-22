#!/usr/bin/env python3
"""engine.py -- certified jump-instance GENERATOR (family: pointed chain with
cyclic symmetries), per Definition v0.3.

Family parameters (m, p_1..p_m), m >= 1, p_i in {2, 3}:

  C : objects a, b_1..b_m, c; chain generators f_0: a->b_1,
      f_i: b_i->b_{i+1} (1<=i<m), f_m: b_m->c; one endomorphism t_i: b_i->b_i
      per hidden object with relations
        t_i o (incoming generator) = incoming,
        (outgoing generator) o t_i = outgoing,
        t_i^{p_i} = id.
      Hence Hom(b_i,b_i) = {id, t_i, .., t_i^{p_i-1}}, all hom-sets between
      distinct chain objects are singletons (the unique path, going forward).
      The composition table is built directly and verified (closure, typing,
      associativity, identity laws) -- no word problem is solved.
  C0: full subcategory on {a, c} (morphisms id_a, id_c, h = P_a_c).
  D : skeletal FinSet. F0(a) = F0(c) = [1], F0(h) unique.
  K : per hidden object i, K1_i: F(t_i) != id; K2_i: |F(b_i)| <= 1 + p_i.
  N : max_i(1 + p_i) + 1.

Everything is computed and certified by full enumeration; nothing is
hand-asserted. Generalizes code/jump_instance_v1/construct.py.
"""
from itertools import product, permutations
from math import factorial

# ------------------------------------------------- finite maps (skeletal FinSet)
def fs_id(n):
    return (n, n, tuple(range(n)))

def fs_comp(g, f):
    """g o f for f:(m,n,vals), g:(n,k,vals)."""
    assert f[1] == g[0]
    return (f[0], g[1], tuple(g[2][v] for v in f[2]))

def all_maps(m, n):
    return [(m, n, vals) for vals in product(range(n), repeat=m)]

def fs_pow(f, k):
    out = fs_id(f[0])
    for _ in range(k):
        out = fs_comp(f, out)
    return out

def p_roots(n, p):
    """All permutations s of [n] with s^p = id (cycle types 1 and p; p prime)."""
    out = []
    for vals in permutations(range(n)):
        f = (n, n, vals)
        if fs_pow(f, p) == fs_id(n):
            out.append(f)
    return out

def perm_inv(perm):
    inv = [0] * len(perm)
    for i, v in enumerate(perm):
        inv[v] = i
    return tuple(inv)

def orbits_of(t):
    """Orbits of a permutation t = (n, n, vals)."""
    n = t[0]
    seen = [False] * n
    obs = []
    for x in range(n):
        if not seen[x]:
            orb = []
            y = x
            while not seen[y]:
                seen[y] = True
                orb.append(y)
                y = t[2][y]
            obs.append(tuple(orb))
    return obs

# ----------------------------------------------------------- instance builder
def build_family(m, ps, N=None):
    """Build the (m, ps) instance: category tables, C0, F0, constraints, N.

    N defaults to max(1+p)+1; an override must still satisfy
    N >= max(1+p) so that Adm is contained in Ext_N (Assumption A5).
    """
    ps = tuple(ps)
    assert m >= 1 and len(ps) == m and all(p in (2, 3) for p in ps), (m, ps)
    chain = ['a'] + [f'b{i}' for i in range(1, m + 1)] + ['c']
    nch = len(chain)
    new_objects = chain[1:-1]

    info = {}   # name -> ('id', ci) | ('path', ci, cj) | ('t', i, k)
    mors = {}   # name -> (src, tgt)
    for ci, o in enumerate(chain):
        info[f'id_{o}'] = ('id', ci)
        mors[f'id_{o}'] = (o, o)
    for ci in range(nch):
        for cj in range(ci + 1, nch):
            nm = f'P_{chain[ci]}_{chain[cj]}'
            info[nm] = ('path', ci, cj)
            mors[nm] = (chain[ci], chain[cj])
    for i in range(1, m + 1):
        for k in range(1, ps[i - 1]):
            nm = f't{i}' if k == 1 else f't{i}^{k}'
            info[nm] = ('t', i, k)
            mors[nm] = (f'b{i}', f'b{i}')

    identity = {o: f'id_{o}' for o in chain}

    def tname(i, k):
        k %= ps[i - 1]
        if k == 0:
            return f'id_b{i}'
        return f't{i}' if k == 1 else f't{i}^{k}'

    comp = {}   # (g, f) -> g o f, for all composable pairs
    for f, (fs_, ft_) in mors.items():
        for g, (gs_, gt_) in mors.items():
            if ft_ != gs_:
                continue
            fi, gi = info[f], info[g]
            if fi[0] == 'id':
                r = g
            elif gi[0] == 'id':
                r = f
            elif fi[0] == 't' and gi[0] == 't':
                r = tname(fi[1], fi[2] + gi[2])
            elif fi[0] == 'path' and gi[0] == 't':
                r = f                       # t o (path into b_i) = path
            elif fi[0] == 't' and gi[0] == 'path':
                r = g                       # (path out of b_i) o t = path
            else:
                r = f'P_{chain[fi[1]]}_{chain[gi[2]]}'
            comp[(g, f)] = r

    h = f'P_a_{chain[-1]}'  # = 'P_a_c'
    if N is None:
        N = max(1 + p for p in ps) + 1
    assert N >= max(1 + p for p in ps), (N, ps)

    constraints = []
    for i in range(1, m + 1):
        pi = ps[i - 1]
        constraints.append({
            'name': f'K1_{i}', 'kind': 'K1', 'station': i,
            'text': f'F(t{i}) != id',
            'pred': (lambda F, i=i: F[f't{i}'] != fs_id(F[f'id_b{i}'][0])),
        })
        constraints.append({
            'name': f'K2_{i}', 'kind': 'K2', 'station': i, 'bound': 1 + pi,
            'text': f'|F(b{i})| <= {1 + pi}',
            'pred': (lambda F, i=i, b=1 + pi: F[f'id_b{i}'][0] <= b),
        })

    return {
        'kind': 'jump', 'm': m, 'ps': ps, 'N': N,
        'chain': chain, 'objects': list(chain), 'new_objects': new_objects,
        'mors': mors, 'info': info, 'identity': identity, 'comp': comp,
        'C0_objects': ['a', chain[-1]],
        'C0_mors': ['id_a', f'id_{chain[-1]}', h], 'h': h,
        'F0_obj': {'a': 1, chain[-1]: 1},
        'F0_mor': {'id_a': fs_id(1), f'id_{chain[-1]}': fs_id(1),
                   h: (1, 1, (0,))},
        'constraints': constraints,
    }

def build_control(inst):
    """Control instance: same (C, C0, F0, N), constraints |F(b_i)| <= 1."""
    ctrl = dict(inst)
    ctrl['kind'] = 'control'
    ctrl['constraints'] = [{
        'name': f'C1_{i}', 'kind': 'CTRL', 'station': i, 'bound': 1,
        'text': f'|F(b{i})| <= 1',
        'pred': (lambda F, i=i: F[f'id_b{i}'][0] <= 1),
    } for i in range(1, inst['m'] + 1)]
    return ctrl

# ------------------------------------------------------ category verification
def c_comp(inst, g, f):
    return inst['comp'].get((g, f))

def homC(inst, x, y):
    return sorted(nm for nm, (s, t) in inst['mors'].items()
                  if s == x and t == y)

def verify_category(inst):
    mors, comp = inst['mors'], inst['comp']
    for f, (fs_, ft_) in mors.items():          # closure + typing
        for g, (gs_, gt_) in mors.items():
            if ft_ == gs_:
                r = comp[(g, f)]
                assert mors[r] == (fs_, gt_), (g, f, r)
            else:
                assert (g, f) not in comp
    for f in mors:                              # associativity
        for g in mors:
            gf = comp.get((g, f))
            if gf is None:
                continue
            for k in mors:
                kg = comp.get((k, g))
                if kg is None:
                    continue
                assert comp[(k, gf)] == comp[(kg, f)], (k, g, f)
    for o in inst['objects']:                   # identity laws
        for nm, (s, t) in mors.items():
            if s == o:
                assert comp[(nm, inst['identity'][o])] == nm
            if t == o:
                assert comp[(inst['identity'][o], nm)] == nm
    # hom-set structure sanity
    idx = {o: i for i, o in enumerate(inst['chain'])}
    for x in inst['objects']:
        for y in inst['objects']:
            hs = homC(inst, x, y)
            if x == y:
                exp = inst['ps'][idx[x] - 1] if x in inst['new_objects'] else 1
                assert len(hs) == exp, (x, hs)
            else:
                assert len(hs) == (1 if idx[x] < idx[y] else 0), (x, y, hs)
    return True

def verify_C0_full(inst):
    for x in inst['C0_objects']:
        for y in inst['C0_objects']:
            for nm in homC(inst, x, y):
                assert nm in inst['C0_mors'], nm
    for f in inst['C0_mors']:
        for g in inst['C0_mors']:
            r = c_comp(inst, g, f)
            if r is not None:
                assert r in inst['C0_mors']
    return True

def verify_F0(inst):
    F0 = inst['F0_mor']
    for f in inst['C0_mors']:
        for g in inst['C0_mors']:
            r = c_comp(inst, g, f)
            if r is not None:
                assert fs_comp(F0[g], F0[f]) == F0[r]
    for o in inst['C0_objects']:
        assert F0[inst['identity'][o]] == fs_id(inst['F0_obj'][o])
    return True

# --------------------------------------------------------- functors on C
def functor_from_generators(inst, sizes, gen_maps):
    """Full morphism table from generator values.
    sizes: {obj: int} incl. a, c; gen_maps: {'f0'..'fm', 't1'..'tm'}."""
    chain, m = inst['chain'], inst['m']
    F = {}
    for o in inst['objects']:
        F[f'id_{o}'] = fs_id(sizes[o])
    gen = {i: gen_maps[f'f{i}'] for i in range(m + 1)}
    for ci in range(len(chain)):
        cur = None
        for cj in range(ci + 1, len(chain)):
            cur = gen[cj - 1] if cur is None else fs_comp(gen[cj - 1], cur)
            F[f'P_{chain[ci]}_{chain[cj]}'] = cur
    for i in range(1, m + 1):
        t = gen_maps[f't{i}']
        cur = t
        for k in range(1, inst['ps'][i - 1]):
            F[f't{i}' if k == 1 else f't{i}^{k}'] = cur
            cur = fs_comp(t, cur)
    return F

def F_sizes(inst, F):
    return {o: F[f'id_{o}'][0] for o in inst['objects']}

def is_functor(inst, F):
    sz = F_sizes(inst, F)
    for nm, (s, t) in inst['mors'].items():
        if F[nm][0] != sz[s] or F[nm][1] != sz[t]:
            return False
    for o in inst['objects']:
        if F[inst['identity'][o]] != fs_id(sz[o]):
            return False
    for (g, f), r in inst['comp'].items():
        if fs_comp(F[g], F[f]) != F[r]:
            return False
    return True

def restricts_to_F0(inst, F):
    return all(F[nm] == inst['F0_mor'][nm] for nm in inst['C0_mors'])

def frz(F):
    return tuple(sorted(F.items()))

# ------------------------------------------------------- Ext_N enumeration
def enumerate_ext(inst, cap=None, full_check=True):
    """All strict extensions F of F0 with |F(b_i)| <= cap (default N).
    Constructive: enumerate generator values pruned by the relations
    (t_i^{p_i} = id, t_i o in = in, out o t_i = out), then build the full
    table; with full_check, every produced table is verified functorial
    against the whole composition table."""
    m, ps, N = inst['m'], inst['ps'], inst['N']
    if cap is None:
        cap = N
    roots_cache = {}

    def get_roots(n, p):
        if (n, p) not in roots_cache:
            roots_cache[(n, p)] = p_roots(n, p)
        return roots_cache[(n, p)]

    results = []

    def finish(sizes, gen_maps):
        nm_last = sizes[f'b{m}']
        gm = dict(gen_maps)
        gm[f'f{m}'] = (nm_last, 1, (0,) * nm_last)   # forced; out o t_m = out auto
        allsz = dict(sizes)
        allsz['a'] = 1
        allsz[inst['chain'][-1]] = 1
        F = functor_from_generators(inst, allsz, gm)
        if full_check:
            assert is_functor(inst, F), "constructed table not a functor"
            assert restricts_to_F0(inst, F)
        results.append(F)

    def rec(i, sizes, gen_maps, t_prev, prev_size):
        if i == m + 1:
            finish(sizes, gen_maps)
            return
        pi = ps[i - 1]
        for n in range(1, cap + 1):
            for t in get_roots(n, pi):
                fixed = [x for x in range(n) if t[2][x] == x]
                if not fixed:
                    continue        # incoming image must be fixed pointwise
                if i == 1:
                    incomings = [(1, n, (q,)) for q in fixed]
                else:
                    obs = orbits_of(t_prev)
                    incomings = []
                    for assign in product(fixed, repeat=len(obs)):
                        vals = [0] * prev_size
                        for orb, v in zip(obs, assign):
                            for x in orb:
                                vals[x] = v
                        incomings.append((prev_size, n, tuple(vals)))
                for inc in incomings:
                    gm = dict(gen_maps)
                    gm[f'f{i - 1}'] = inc
                    gm[f't{i}'] = t
                    sz = dict(sizes)
                    sz[f'b{i}'] = n
                    rec(i + 1, sz, gm, t, n)

    rec(1, {}, {}, None, 1)
    return results

def enumerate_ext_naive(inst, cap):
    """Independent unstructured enumeration (for cross-validation in tests):
    all generator assignments, filtered only by full functoriality."""
    m = inst['m']
    out = []
    for sizes_new in product(range(1, cap + 1), repeat=m):
        sizes = {'a': 1, inst['chain'][-1]: 1}
        for i in range(1, m + 1):
            sizes[f'b{i}'] = sizes_new[i - 1]
        chain_sz = [1] + list(sizes_new) + [1]
        gen_choices = [all_maps(chain_sz[i], chain_sz[i + 1])
                       for i in range(m + 1)]
        t_choices = [all_maps(sizes_new[i - 1], sizes_new[i - 1])
                     for i in range(1, m + 1)]
        for gens in product(*gen_choices):
            for ts in product(*t_choices):
                gm = {f'f{i}': gens[i] for i in range(m + 1)}
                ok = True
                for i in range(1, m + 1):
                    t = ts[i - 1]
                    if fs_pow(t, inst['ps'][i - 1]) != fs_id(t[0]):
                        ok = False
                        break
                    gm[f't{i}'] = t
                if not ok:
                    continue
                F = functor_from_generators(inst, sizes, gm)
                if is_functor(inst, F) and restricts_to_F0(inst, F):
                    out.append(F)
    return out

# --------------------------- pointwise Lan/Ran via comma-category formulas
def lan_pointwise(inst):
    F0_obj, F0_mor = inst['F0_obj'], inst['F0_mor']
    data = {}
    for x in inst['objects']:
        objs = [(w, v) for w in inst['C0_objects'] for v in homC(inst, w, x)]
        elems = [(w, v, e) for (w, v) in objs for e in range(F0_obj[w])]
        parent = {el: el for el in elems}

        def find(z):
            while parent[z] != z:
                parent[z] = parent[parent[z]]
                z = parent[z]
            return z

        def union(z1, z2):
            r1, r2 = find(z1), find(z2)
            if r1 != r2:
                parent[r1] = r2

        for (w, v) in objs:      # comma morphism u:(w',v')->(w,v), v o u = v'
            for u in inst['C0_mors']:
                su, tu = inst['mors'][u]
                if tu == w:
                    vp = c_comp(inst, v, u)
                    assert (su, vp) in objs
                    for e in range(F0_obj[su]):
                        union((su, vp, e), (w, v, F0_mor[u][2][e]))
        classes = sorted({find(el) for el in elems})
        idx = {el: classes.index(find(el)) for el in elems}
        data[x] = (objs, elems, idx, len(classes))

    lan_mor = {}
    for alpha, (x, y) in inst['mors'].items():
        _, elems_x, idx_x, nx = data[x]
        _, _, idx_y, ny = data[y]
        vals = [None] * nx
        for (w, v, e) in elems_x:
            tgt = idx_y[(w, c_comp(inst, alpha, v), e)]
            i = idx_x[(w, v, e)]
            if vals[i] is None:
                vals[i] = tgt
            else:
                assert vals[i] == tgt, "Lan not well-defined"
        lan_mor[alpha] = (nx, ny, tuple(vals))

    unit = {}
    for w in inst['C0_objects']:
        _, _, idx, nw = data[w]
        u = tuple(idx[(w, inst['identity'][w], e)] for e in range(F0_obj[w]))
        assert sorted(u) == list(range(nw)), "unit not bijective (K not ff?)"
        unit[w] = u
    return data, lan_mor, unit

def ran_pointwise(inst):
    F0_obj, F0_mor = inst['F0_obj'], inst['F0_mor']
    data = {}
    for x in inst['objects']:
        objs = [(w, v) for w in inst['C0_objects'] for v in homC(inst, x, w)]
        fams = []
        for combo in product(*[range(F0_obj[w]) for (w, v) in objs]):
            e = dict(zip(objs, combo))
            ok = True
            for (w, v) in objs:
                for u in inst['C0_mors']:
                    su, tu = inst['mors'][u]
                    if su == w:
                        v2 = c_comp(inst, u, v)
                        if F0_mor[u][2][e[(w, v)]] != e[(tu, v2)]:
                            ok = False
            if ok:
                fams.append(combo)
        data[x] = (objs, sorted(fams))

    ran_mor = {}
    for alpha, (x, y) in inst['mors'].items():
        objs_x, fams_x = data[x]
        objs_y, fams_y = data[y]
        vals = []
        for fam in fams_x:
            e = dict(zip(objs_x, fam))
            img = tuple(e[(w, c_comp(inst, v, alpha))] for (w, v) in objs_y)
            vals.append(fams_y.index(img))
        ran_mor[alpha] = (len(fams_x), len(fams_y), tuple(vals))

    counit = {}
    for w in inst['C0_objects']:
        objs_w, fams_w = data[w]
        cu = tuple(dict(zip(objs_w, fam))[(w, inst['identity'][w])]
                   for fam in fams_w)
        assert sorted(cu) == list(range(F0_obj[w])), "counit not bijective"
        counit[w] = cu
    return data, ran_mor, counit

def _strictify(inst, mor_dict, sizes, relabel):
    out = {}
    for nm, (x, y) in inst['mors'].items():
        nx, ny, vals = mor_dict[nm]
        inv_x = [None] * nx
        for i in range(nx):
            inv_x[relabel[x][i]] = i
        out[nm] = (nx, ny, tuple(relabel[y][vals[inv_x[j]]] for j in range(nx)))
    return out

def lan_strict(inst):
    data, lan_mor, unit = lan_pointwise(inst)
    sizes = {x: data[x][3] for x in inst['objects']}
    relabel = {}
    for x in inst['objects']:
        if x in inst['C0_objects']:
            inv = [None] * sizes[x]
            for e in range(inst['F0_obj'][x]):
                inv[unit[x][e]] = e
            relabel[x] = inv
        else:
            relabel[x] = list(range(sizes[x]))
    return _strictify(inst, lan_mor, sizes, relabel), sizes

def ran_strict(inst):
    data, ran_mor, counit = ran_pointwise(inst)
    sizes = {x: len(data[x][1]) for x in inst['objects']}
    relabel = {}
    for x in inst['objects']:
        if x in inst['C0_objects']:
            relabel[x] = list(counit[x])
        else:
            relabel[x] = list(range(sizes[x]))
    return _strictify(inst, ran_mor, sizes, relabel), sizes

# ----------------------------------------------------------------- gauge
def apply_gauge(inst, F, sigma):
    """sigma: {new_obj: permutation tuple}; identity on C0. Conjugation."""
    inv = {o: perm_inv(s) for o, s in sigma.items()}
    out = {}
    for nm, (x, y) in inst['mors'].items():
        nx, ny, vals = F[nm]
        new_vals = []
        for j in range(nx):
            src = inv[x][j] if x in inv else j
            v = vals[src]
            new_vals.append(sigma[y][v] if y in sigma else v)
        out[nm] = (nx, ny, tuple(new_vals))
    return out

def gauge_group_elems(inst, F):
    """All gauge tuples for F: product of Sym(|F(b_i)|), identity on C0."""
    new = inst['new_objects']
    per = [list(permutations(range(F[f'id_{o}'][0]))) for o in new]
    for combo in product(*per):
        yield dict(zip(new, combo))

def gauge_orbit(inst, F):
    return {frz(apply_gauge(inst, F, s)) for s in gauge_group_elems(inst, F)}

# --------------------------------------- structural characterization of Adm
def adm_structure_ok(inst, F):
    """Verify the analyzed structure of an admissible extension, gauge-free:
    per station i: |F(b_i)| = 1+p_i; F(t_i) has exactly one fixed point and
    one p_i-cycle; the incoming map is constant onto the fixed point; the
    outgoing map is constant on t_i-orbits (with image the next fixed point,
    checked at the next station)."""
    chain, m, ps = inst['chain'], inst['m'], inst['ps']
    for i in range(1, m + 1):
        pi = ps[i - 1]
        n = F[f'id_b{i}'][0]
        if n != 1 + pi:
            return False
        t = F[f't{i}']
        fixed = [x for x in range(n) if t[2][x] == x]
        if len(fixed) != 1:
            return False
        obs = [o for o in orbits_of(t) if len(o) > 1]
        if len(obs) != 1 or len(obs[0]) != pi:
            return False
        inc = F[f'P_{chain[i - 1]}_{chain[i]}']
        if set(inc[2]) != {fixed[0]}:
            return False
        out = F[f'P_{chain[i]}_{chain[i + 1]}']
        for orb in orbits_of(t):
            if len({out[2][x] for x in orb}) != 1:
                return False
    return True

# ------------------------------------------------------------- certification
def compute_adm(inst, ext):
    preds = [(c['name'], c['pred']) for c in inst['constraints']]
    return [F for F in ext if all(p(F) for _, p in preds)]

def certify(inst, ext=None, non_pinning_floor=0.10):
    """Full certification of a jump instance. Returns a report dict."""
    rep = {'m': inst['m'], 'ps': list(inst['ps']), 'N': inst['N'],
           'certification_mode': 'enumeration'}
    rep['category_ok'] = verify_category(inst)
    rep['c0_full_ok'] = verify_C0_full(inst)
    rep['f0_ok'] = verify_F0(inst)

    if ext is None:
        ext = enumerate_ext(inst)
    rep['ext_count'] = len(ext)
    ext_frz = {frz(F) for F in ext}
    assert len(ext_frz) == len(ext), "duplicate extensions"

    Lan, lan_sizes = lan_strict(inst)
    Ran, ran_sizes = ran_strict(inst)
    assert is_functor(inst, Lan) and restricts_to_F0(inst, Lan)
    assert is_functor(inst, Ran) and restricts_to_F0(inst, Ran)
    rep['lan_sizes'] = {o: lan_sizes[o] for o in inst['new_objects']}
    rep['ran_sizes'] = {o: ran_sizes[o] for o in inst['new_objects']}
    rep['lan_eq_ran'] = (Lan == Ran)
    rep['kan_trivial'] = all(
        lan_sizes[o] == 1 and ran_sizes[o] == 1 for o in inst['new_objects'])
    rep['lan_in_ext'] = frz(Lan) in ext_frz
    rep['ran_in_ext'] = frz(Ran) in ext_frz

    Adm = compute_adm(inst, ext)
    rep['adm_count'] = len(Adm)
    rep['chance'] = len(Adm) / len(ext) if ext else 0.0
    rep['adm_count_formula'] = 1
    for p in inst['ps']:
        rep['adm_count_formula'] *= (1 + p) * factorial(p - 1)
    rep['adm_count_matches_formula'] = (len(Adm) == rep['adm_count_formula'])

    rep['J1'] = len(Adm) > 0

    kan_frz = {frz(Lan), frz(Ran)}
    strict_disjoint = not any(frz(F) in kan_frz for F in Adm)
    kan_comp = set()
    for Kx in (Lan, Ran):
        kan_comp |= gauge_orbit(inst, Kx)
    comp_disjoint = not any(frz(F) in kan_comp for F in Adm)
    rep['J2'] = strict_disjoint and comp_disjoint
    rep['kan_violations'] = {
        'Lan*': [c['name'] for c in inst['constraints'] if not c['pred'](Lan)],
        'Ran*': [c['name'] for c in inst['constraints'] if not c['pred'](Ran)],
    }
    rep['J2_each_kan_violates'] = all(
        len(v) > 0 for v in rep['kan_violations'].values())

    adm_frz = {frz(F) for F in Adm}
    rep['J3'] = bool(Adm) and (gauge_orbit(inst, Adm[0]) == adm_frz)

    rep['J4'] = all(
        any(homC(inst, w, o) for w in inst['C0_objects'])
        for o in inst['new_objects'])
    rep['J4_strong'] = all(
        len(homC(inst, 'a', o)) > 0 for o in inst['new_objects'])

    rep['adm_structure_ok'] = all(adm_structure_ok(inst, F) for F in Adm)
    # A5 (entailment of the size bound by K): every hidden object carries an
    # explicit cardinality cap 1+p_i in K2_i, and the cap must not exceed N;
    # this is a genuine check on (K, N), not a tautology over Ext_N.
    rep['bound_entailed'] = all(1 + p <= inst['N'] for p in inst['ps']) and all(
        F[f'id_b{i}'][0] <= inst['N']
        for F in Adm for i in range(1, inst['m'] + 1))

    non_pin = {}
    for c in inst['constraints']:
        alive = sum(1 for F in ext if c['pred'](F))
        non_pin[c['name']] = {'alive': alive,
                              'fraction': alive / len(ext)}
    rep['non_pinning'] = non_pin
    rep['non_pinning_floor'] = non_pinning_floor
    rep['non_pinning_ok'] = all(
        v['fraction'] >= non_pinning_floor for v in non_pin.values())

    # 'certified' = the (J1)-(J4) certification plus table/Kan/structure
    # checks. The non-pinning statistic is reported as its own flag
    # (non_pinning_ok), matching the dataset summary's separate column.
    rep['certified'] = all([
        rep['category_ok'], rep['c0_full_ok'], rep['f0_ok'],
        rep['lan_in_ext'], rep['ran_in_ext'], rep['kan_trivial'],
        rep['J1'], rep['J2'], rep['J2_each_kan_violates'], rep['J3'],
        rep['J4'], rep['J4_strong'], rep['adm_structure_ok'],
        rep['adm_count_matches_formula'], rep['bound_entailed'],
    ])
    rep['_adm_rep'] = Adm[0] if Adm else None        # not JSON-serialized
    rep['_lan'] = Lan
    rep['_ran'] = Ran
    return rep

def certify_control(ctrl, ext=None):
    """Certify Adm(control) = [Lan*] plus (J1),(J3),(J4)."""
    assert ctrl['kind'] == 'control'
    rep = {'m': ctrl['m'], 'ps': list(ctrl['ps']), 'N': ctrl['N'],
           'certification_mode': 'enumeration'}
    if ext is None:
        ext = enumerate_ext(ctrl)
    Adm = compute_adm(ctrl, ext)
    Lan, _ = lan_strict(ctrl)
    Ran, _ = ran_strict(ctrl)
    adm_frz = {frz(F) for F in Adm}
    lan_component = gauge_orbit(ctrl, Lan)
    rep['adm_count'] = len(Adm)
    rep['J1'] = len(Adm) > 0
    rep['adm_equals_lan_component'] = (adm_frz == lan_component)
    rep['lan_eq_ran'] = (Lan == Ran)
    rep['J3'] = bool(Adm) and (gauge_orbit(ctrl, Adm[0]) == adm_frz)
    rep['J4_strong'] = all(
        len(homC(ctrl, 'a', o)) > 0 for o in ctrl['new_objects'])
    rep['certified'] = all([rep['J1'], rep['adm_equals_lan_component'],
                            rep['J3'], rep['J4_strong']])
    rep['_kan'] = Lan
    return rep

# ------------------- THEOREM-CERTIFIED path (family theorem F1-F10) --------
# The pointed-chain family theorem (formalization/13-family-theorem-verified.md
# and 13b-family-theorem-proof-full.md, independently verified) supplies the
# full v0.3 certificate uniformly in (m, ps, N): Adm is a single gauge orbit
# of size prod_i (1+p_i)(p_i-1)! with the F6(b) structure, Lan* = Ran* = the
# trivial all-singleton extension T violating exactly {K1_i}, (J1)-(J4) hold,
# and Proposition F7 gives |Ext_N| in closed form. The functions below turn
# that theorem into a certification route that never enumerates Ext_N;
# everything still checkable in polynomial time on the tables (Corollary
# F8(i)) is checked directly rather than trusted.

def w_root_count(p, n, k):
    """Number of tau: [n] -> [n] with tau^p = id and exactly k fixed points
    (p prime): n!/(k! p^j j!) with j = (n-k)/p when p | n-k, else 0
    (Proposition F7)."""
    if k < 0 or k > n or (n - k) % p != 0:
        return 0
    j = (n - k) // p
    return factorial(n) // (factorial(k) * (p ** j) * factorial(j))

def ext_count_closed_form(m, ps, N, station_filter=None):
    """|Ext_N(F0)| for the (m, ps) family instance by Proposition F7's
    transfer recursion, ported from the independent verifier's validated
    implementation (verify_scratch/theory_family/attack_family.py, which
    matched brute enumeration on thirteen configurations).

    station_filter, if given, maps a station index i (1-based) to a predicate
    on (n_i, k_i) restricting the station's states; this computes restricted
    counts such as the per-constraint alive counts:
      K1_i alive  <->  tau_i != id      <->  k_i < n_i,
      K2_i alive  <->  n_i <= 1 + p_i.
    """
    ps = tuple(ps)
    assert m >= 1 and len(ps) == m
    sf = station_filter or {}

    def allowed(i, n, k):
        f = sf.get(i)
        return f(n, k) if f else True

    R = {}
    for n in range(1, N + 1):
        for k in range(0, n + 1):
            if not allowed(1, n, k):
                continue
            v = w_root_count(ps[0], n, k) * k        # k choices of phi_0
            if v:
                R[(n, k)] = v
    for i in range(2, m + 1):
        p_prev, p_cur = ps[i - 2], ps[i - 1]
        R2 = {}
        for n2 in range(1, N + 1):
            for k2 in range(0, n2 + 1):
                if not allowed(i, n2, k2):
                    continue
                wv = w_root_count(p_cur, n2, k2)
                if wv == 0:
                    continue
                # phi_{i-1} is constant on the orb(tau_{i-1}) orbits, into
                # Fix(tau_i): k2^(k + (n-k)/p_prev) choices.
                s = sum(rv * (k2 ** (k + (n - k) // p_prev))
                        for (n, k), rv in R.items())
                if s:
                    R2[(n2, k2)] = wv * s
        R = R2
    return sum(R.values())

def alive_counts_closed_form(m, ps, N):
    """Closed-form per-constraint alive counts |{F in Ext_N : c(F)}|, via the
    same transfer recursion with station i's weight restricted to the
    constraint's condition (K1_i: tau_i != id, i.e. k < n; K2_i:
    n <= 1 + p_i)."""
    ps = tuple(ps)
    out = {}
    for i in range(1, m + 1):
        out[f'K1_{i}'] = ext_count_closed_form(
            m, ps, N, {i: (lambda n, k: k < n)})
        out[f'K2_{i}'] = ext_count_closed_form(
            m, ps, N, {i: (lambda n, k, b=1 + ps[i - 1]: n <= b)})
    return out

def adm_count_theorem(ps):
    """|Adm| = prod_i (1+p_i)(p_i-1)!  (Theorem F6(c))."""
    out = 1
    for p in ps:
        out *= (1 + p) * factorial(p - 1)
    return out

def trivial_extension(inst):
    """The all-singleton extension T = Lan* = Ran* of Theorem F6(d)."""
    return {nm: (1, 1, (0,)) for nm in inst['mors']}

def build_planted(inst):
    """The planted admissible witness F* of Theorem F6(a): at each station i,
    |F(b_i)| = 1 + p_i, state 0 the unique fixed point of F(t_i) (which
    cycles the remaining p_i states), incoming map constant onto 0. The
    returned table is verified: functorial, restricts to F0, has the F6(b)
    structure, and satisfies every constraint."""
    m, ps, chain = inst['m'], inst['ps'], inst['chain']
    sizes = {'a': 1, chain[-1]: 1}
    gen_maps = {}
    prev = 1
    for i in range(1, m + 1):
        p = ps[i - 1]
        n = 1 + p
        sizes[f'b{i}'] = n
        gen_maps[f'f{i - 1}'] = (prev, n, (0,) * prev)
        gen_maps[f't{i}'] = (n, n, tuple([0] + list(range(2, p + 1)) + [1]))
        prev = n
    gen_maps[f'f{m}'] = (prev, 1, (0,) * prev)
    F = functor_from_generators(inst, sizes, gen_maps)
    assert is_functor(inst, F), "planted witness not a functor"
    assert restricts_to_F0(inst, F)
    assert adm_structure_ok(inst, F)
    return F

def certify_by_theorem(inst, non_pinning_floor=0.10):
    """THEOREM-CERTIFIED report for a family instance: same report shape as
    certify(), with certification_mode='theorem', and with ext_count,
    adm_count, chance and the non-pinning fractions computed by the F7
    closed form instead of enumeration. Ext_N is never enumerated.

    Fields taken from the verified theorem rather than recomputed: J3 (Adm is
    a single gauge orbit, F6(c)), adm_count (F6(c)), ext_count and the alive
    counts (F7), and the universally quantified halves of J2 and
    adm_structure_ok (F6(b), F6(d)). Everything polynomial in the table size
    is still checked directly: the category/C0/F0 axioms, the Kan pair
    (computed by the comma formulas and checked equal to the trivial T), T's
    exact violation set, membership of T in Ext_N, the planted admissible
    witness with its structure and constraint satisfaction, (J4), and the
    A5 bound entailment."""
    assert inst['kind'] == 'jump'
    m, ps, N = inst['m'], inst['ps'], inst['N']
    rep = {'m': m, 'ps': list(ps), 'N': N,
           'certification_mode': 'theorem'}
    rep['category_ok'] = verify_category(inst)
    rep['c0_full_ok'] = verify_C0_full(inst)
    rep['f0_ok'] = verify_F0(inst)

    rep['ext_count'] = ext_count_closed_form(m, ps, N)

    Lan, lan_sizes = lan_strict(inst)
    Ran, ran_sizes = ran_strict(inst)
    assert is_functor(inst, Lan) and restricts_to_F0(inst, Lan)
    assert is_functor(inst, Ran) and restricts_to_F0(inst, Ran)
    T = trivial_extension(inst)
    assert Lan == T and Ran == T, "Kan pair differs from the theorem's T"
    rep['lan_sizes'] = {o: lan_sizes[o] for o in inst['new_objects']}
    rep['ran_sizes'] = {o: ran_sizes[o] for o in inst['new_objects']}
    rep['lan_eq_ran'] = (Lan == Ran)
    rep['kan_trivial'] = all(
        lan_sizes[o] == 1 and ran_sizes[o] == 1 for o in inst['new_objects'])
    # T is itself a strict extension with singleton sizes <= N (checked
    # above: functorial + restricts to F0), hence lies in Ext_N.
    rep['lan_in_ext'] = all(Lan[f'id_{o}'][0] <= N for o in inst['objects'])
    rep['ran_in_ext'] = all(Ran[f'id_{o}'][0] <= N for o in inst['objects'])

    rep['adm_count'] = adm_count_theorem(ps)
    rep['chance'] = rep['adm_count'] / rep['ext_count']
    rep['adm_count_formula'] = adm_count_theorem(ps)
    rep['adm_count_matches_formula'] = True     # F6(c) is the formula

    planted = build_planted(inst)               # verified in build_planted
    rep['J1'] = all(c['pred'](planted) for c in inst['constraints'])

    rep['kan_violations'] = {
        'Lan*': [c['name'] for c in inst['constraints'] if not c['pred'](Lan)],
        'Ran*': [c['name'] for c in inst['constraints'] if not c['pred'](Ran)],
    }
    rep['J2_each_kan_violates'] = all(
        len(v) > 0 for v in rep['kan_violations'].values())
    # Set-theoretic disjointness (F6(d)): every admissible F has
    # |F(b_i)| = 1 + p_i >= 3 while T is all-singleton.
    rep['J2'] = rep['J2_each_kan_violates'] and all(1 + p > 1 for p in ps)

    rep['J3'] = True        # F6(c): Adm is a single gauge orbit
    rep['J4'] = all(
        any(homC(inst, w, o) for w in inst['C0_objects'])
        for o in inst['new_objects'])
    rep['J4_strong'] = all(
        len(homC(inst, 'a', o)) > 0 for o in inst['new_objects'])

    # F6(b) gives the structure for every admissible F; checked directly on
    # the planted representative.
    rep['adm_structure_ok'] = adm_structure_ok(inst, planted)
    rep['bound_entailed'] = all(1 + p <= N for p in ps)

    alive = alive_counts_closed_form(m, ps, N)
    non_pin = {name: {'alive': a, 'fraction': a / rep['ext_count']}
               for name, a in alive.items()}
    rep['non_pinning'] = non_pin
    rep['non_pinning_floor'] = non_pinning_floor
    rep['non_pinning_ok'] = all(
        v['fraction'] >= non_pinning_floor for v in non_pin.values())

    rep['certified'] = all([
        rep['category_ok'], rep['c0_full_ok'], rep['f0_ok'],
        rep['lan_in_ext'], rep['ran_in_ext'], rep['kan_trivial'],
        rep['J1'], rep['J2'], rep['J2_each_kan_violates'], rep['J3'],
        rep['J4'], rep['J4_strong'], rep['adm_structure_ok'],
        rep['adm_count_matches_formula'], rep['bound_entailed'],
    ])
    rep['_adm_rep'] = planted
    rep['_lan'] = Lan
    rep['_ran'] = Ran
    return rep

def certify_control_by_theorem(ctrl):
    """Control certification without enumeration. The control constraints
    force |F(b_i)| = 1 at every station (n_i >= 1 by Lemma F5, n_i <= 1 by
    C1_i), and every generator value into or out of a singleton is the
    unique constant map, so Adm(control) = {T} exactly, with T the trivial
    all-singleton extension = Lan* = Ran* (F6(d)); its gauge orbit is {T}
    since every Sym(1) is trivial. Same report shape as certify_control()."""
    assert ctrl['kind'] == 'control'
    rep = {'m': ctrl['m'], 'ps': list(ctrl['ps']), 'N': ctrl['N'],
           'certification_mode': 'theorem'}
    Lan, _ = lan_strict(ctrl)
    Ran, _ = ran_strict(ctrl)
    T = trivial_extension(ctrl)
    assert Lan == T and Ran == T, "control Kan pair differs from T"
    assert is_functor(ctrl, T) and restricts_to_F0(ctrl, T)
    assert all(c['pred'](T) for c in ctrl['constraints'])
    rep['adm_count'] = 1                        # forced-table argument above
    rep['J1'] = True
    rep['adm_equals_lan_component'] = (
        gauge_orbit(ctrl, T) == {frz(T)})       # trivial gauge group on T
    rep['lan_eq_ran'] = (Lan == Ran)
    rep['J3'] = True                            # Adm = {T}, one orbit
    rep['J4_strong'] = all(
        len(homC(ctrl, 'a', o)) > 0 for o in ctrl['new_objects'])
    rep['certified'] = all([rep['J1'], rep['adm_equals_lan_component'],
                            rep['J3'], rep['J4_strong']])
    rep['_kan'] = Lan
    return rep
