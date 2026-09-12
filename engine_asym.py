"""Asymmetric-data family (A3): a -f-> b -g-> c with marked involution t on the hidden b,
and end data of unequal size, F0(a) = [k], F0(c) = [l]. When k != l the two Kan extensions
differ: Lan(b) is a copy of the input [k], Ran(b) a copy of the output [l].
Self-contained brute-force certifier in the style of seed/construct.py (nothing hand-asserted).
"""
from itertools import product, permutations

C_OBJ = ['a', 'b', 'c']
C_MOR = {'ida': ('a', 'a'), 'idb': ('b', 'b'), 'idc': ('c', 'c'),
         'f': ('a', 'b'), 't': ('b', 'b'), 'g': ('b', 'c'), 'h': ('a', 'c')}
C_ID = {'a': 'ida', 'b': 'idb', 'c': 'idc'}
_COMP = {('t', 'f'): 'f', ('g', 'f'): 'h', ('t', 't'): 'idb', ('g', 't'): 'g'}
C0_OBJ, C0_MOR = ['a', 'c'], ['ida', 'idc', 'h']


def c_comp(m2, m1):
    s1, t1 = C_MOR[m1]; s2, t2 = C_MOR[m2]
    if t1 != s2: return None
    if m1 == C_ID[s1]: return m2
    if m2 == C_ID[t2]: return m1
    return _COMP[(m2, m1)]


def homC(x, y): return sorted(m for m, (s, t) in C_MOR.items() if s == x and t == y)
def fs_id(n): return (n, n, tuple(range(n)))
def fs_comp(g, f): assert f[1] == g[0]; return (f[0], g[1], tuple(g[2][v] for v in f[2]))
def all_maps(m, n): return [(m, n, v) for v in product(range(n), repeat=m)]


class Inst:
    def __init__(self, k, l, N, hval=0, extra_constraints=()):
        self.k, self.l, self.N = k, l, N
        self.F0_OBJ = {'a': k, 'c': l}
        self.F0_MOR = {'ida': fs_id(k), 'idc': fs_id(l), 'h': (k, l, tuple([hval] * k))}
        self.constraints = [
            ('K1: F(t) != id', lambda F: F['t'] != fs_id(F['idb'][0])),
            (f'K2: |F(b)| <= {N}', lambda F: F['idb'][0] <= N),
            ('K3: F(f) mono', lambda F: len(set(F['f'][2])) == F['f'][0]),
            ('K4: F(g) epi', lambda F: len(set(F['g'][2])) == F['g'][1]),
        ] + list(extra_constraints)

    # ---- functors on C extending F0
    def make_F(self, nb, Ff, Fg, Ft):
        return {'ida': fs_id(self.k), 'idb': fs_id(nb), 'idc': fs_id(self.l),
                'f': Ff, 'g': Fg, 't': Ft, 'h': self.F0_MOR['h']}

    def is_functor(self, F):
        sz = {'a': self.k, 'b': F['idb'][0], 'c': self.l}
        for m, (s, t) in C_MOR.items():
            if F[m][0] != sz[s] or F[m][1] != sz[t]: return False
        for m1 in C_MOR:
            for m2 in C_MOR:
                c = c_comp(m2, m1)
                if c is not None and fs_comp(F[m2], F[m1]) != F[c]: return False
        return True

    def enumerate_ext(self, cap):
        ext = []
        for nb in range(cap + 1):
            invols = [t for t in all_maps(nb, nb) if fs_comp(t, t) == fs_id(nb)]
            for Ff in all_maps(self.k, nb):
                if fs_comp(Ff, fs_id(self.k)) != Ff: continue
                for Ft in invols:
                    if fs_comp(Ft, Ff) != Ff: continue          # t o f = f
                    for Fg in all_maps(nb, self.l):
                        if fs_comp(Fg, Ft) != Fg: continue      # g o t = g
                        if fs_comp(Fg, Ff) != self.F0_MOR['h']: continue   # g o f = h
                        F = self.make_F(nb, Ff, Fg, Ft)
                        if self.is_functor(F): ext.append(F)
        return ext

    # ---- pointwise Kan extensions via comma formulas (generic in F0 sizes)
    def lan_strict(self):
        F0_OBJ, F0_MOR = self.F0_OBJ, self.F0_MOR
        data = {}
        for x in C_OBJ:
            objs = [(w, m) for w in C0_OBJ for m in homC(w, x)]
            elems = [(w, m, e) for (w, m) in objs for e in range(F0_OBJ[w])]
            parent = {el: el for el in elems}
            def find(z):
                while parent[z] != z: parent[z] = parent[parent[z]]; z = parent[z]
                return z
            for (w, m) in objs:
                for u in C0_MOR:
                    su, tu = C_MOR[u]
                    if tu == w:
                        mp = c_comp(m, u)
                        for e in range(F0_OBJ[su]):
                            r1, r2 = find((su, mp, e)), find((w, m, F0_MOR[u][2][e]))
                            if r1 != r2: parent[r1] = r2
            classes = sorted({find(el) for el in elems})
            data[x] = (elems, {el: classes.index(find(el)) for el in elems}, len(classes))
        mor = {}
        for al, (x, y) in C_MOR.items():
            elems_x, idx_x, nx = data[x]; _, idx_y, ny = data[y]
            vals = [None] * nx
            for (w, m, e) in elems_x: vals[idx_x[(w, m, e)]] = idx_y[(w, c_comp(al, m), e)]
            mor[al] = (nx, ny, tuple(vals))
        # strictify so that the unit at a, c is the identity
        relabel = {}
        for x in C_OBJ:
            if x in C0_OBJ:
                inv = [None] * data[x][2]
                for e in range(F0_OBJ[x]): inv[data[x][1][(x, C_ID[x], e)]] = e
                relabel[x] = inv
            else: relabel[x] = list(range(data[x][2]))
        return self._strictify(mor, relabel)

    def ran_strict(self):
        F0_OBJ, F0_MOR = self.F0_OBJ, self.F0_MOR
        data = {}
        for x in C_OBJ:
            objs = [(w, m) for w in C0_OBJ for m in homC(x, w)]
            fams = []
            for combo in product(*[range(F0_OBJ[w]) for (w, m) in objs]):
                e = dict(zip(objs, combo)); ok = True
                for (w, m) in objs:
                    for u in C0_MOR:
                        su, tu = C_MOR[u]
                        if su == w and F0_MOR[u][2][e[(w, m)]] != e[(tu, c_comp(u, m))]: ok = False
                if ok: fams.append(combo)
            data[x] = (objs, sorted(fams))
        mor = {}
        for al, (x, y) in C_MOR.items():
            objs_x, fams_x = data[x]; objs_y, fams_y = data[y]
            vals = [fams_y.index(tuple(dict(zip(objs_x, fam))[(w, c_comp(m, al))] for (w, m) in objs_y)) for fam in fams_x]
            mor[al] = (len(fams_x), len(fams_y), tuple(vals))
        relabel = {}
        for x in C_OBJ:
            if x in C0_OBJ:
                objs_w, fams_w = data[x]
                relabel[x] = [dict(zip(objs_w, fam))[(x, C_ID[x])] for fam in fams_w]
            else: relabel[x] = list(range(len(data[x][1])))
        return self._strictify(mor, relabel)

    @staticmethod
    def _strictify(mor, relabel):
        out = {}
        for m, (x, y) in C_MOR.items():
            nx, ny, vals = mor[m]
            inv_x = [None] * nx
            for i in range(nx): inv_x[relabel[x][i]] = i
            out[m] = (nx, ny, tuple(relabel[y][vals[inv_x[j]]] for j in range(nx)))
        return out

    # ---- gauge: natural isos restricting to the identity on C0 (permutations of F(b))
    def gauge_equiv(self, F, G):
        nb = F['idb'][0]
        if nb != G['idb'][0]: return False
        for perm in permutations(range(nb)):
            beta = (nb, nb, perm)
            eta = {'a': fs_id(self.k), 'b': beta, 'c': fs_id(self.l)}
            if all(fs_comp(eta[C_MOR[m][1]], F[m]) == fs_comp(G[m], eta[C_MOR[m][0]]) for m in C_MOR): return True
        return False

    def iso_classes(self, Fs):
        classes = []
        for F in Fs:
            for cl in classes:
                if self.gauge_equiv(F, cl[0]): cl.append(F); break
            else: classes.append([F])
        return classes

    def certify(self):
        Ext = self.enumerate_ext(self.N)
        Lan, Ran = self.lan_strict(), self.ran_strict()
        assert self.is_functor(Lan) and self.is_functor(Ran)
        assert Lan in Ext and Ran in Ext
        Adm = [F for F in Ext if all(p(F) for _, p in self.constraints)]
        viol = lambda F: [n for n, p in self.constraints if not p(F)]
        adm_cl = self.iso_classes(Adm)
        rep = {'k': self.k, 'l': self.l, 'N': self.N, 'ext_count': len(Ext), 'adm_count': len(Adm),
               'adm_classes': len(adm_cl), 'lan_size_b': Lan['idb'][0], 'ran_size_b': Ran['idb'][0],
               'lan_eq_ran': Lan == Ran, 'lan_violates': viol(Lan), 'ran_violates': viol(Ran),
               'chance': len(Adm) / len(Ext) if Ext else None,
               'J1_nonempty': len(Adm) > 0, 'J2_excludes_both': bool(viol(Lan)) and bool(viol(Ran)),
               'J3_identifiable': len(adm_cl) == 1}
        rep['certified'] = rep['J1_nonempty'] and rep['J2_excludes_both'] and rep['J3_identifiable']
        rep['_Lan'], rep['_Ran'], rep['_Adm'] = Lan, Ran, Adm
        return rep


def fmt_F(F):
    fm = lambda f: "{" + ",".join(f"{i}->{f[2][i]}" for i in range(f[0])) + "}"
    return f"F(b)=[{F['idb'][0]}] f={fm(F['f'])} t={fm(F['t'])} g={fm(F['g'])}"


if __name__ == "__main__":
    import sys, time
    for (k, l, N) in [(2, 1, 4), (3, 1, 5), (1, 2, 3), (1, 3, 5)]:
        t0 = time.time(); rep = Inst(k, l, N).certify()
        print(f"\n=== k={k} l={l} N={N}  ({time.time()-t0:.1f}s) ===")
        for key in ['ext_count', 'adm_count', 'adm_classes', 'lan_size_b', 'ran_size_b', 'lan_eq_ran',
                    'lan_violates', 'ran_violates', 'chance', 'certified']:
            print(f"  {key:16s} {rep[key]}")
        print("  Lan:", fmt_F(rep['_Lan'])); print("  Ran:", fmt_F(rep['_Ran']))
        for F in rep['_Adm'][:3]: print("  Adm:", fmt_F(F))
