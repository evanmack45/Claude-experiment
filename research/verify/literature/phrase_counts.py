#!/usr/bin/env python3
"""Whitespace/ligature-insensitive phrase counts in the extracted source texts (verifier)."""
import re, os
H = os.path.dirname(os.path.abspath(__file__))
def norm(fn):
    s = open(os.path.join(H, 'data', fn), encoding='latin1').read()
    s = re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S) if fn.endswith('.html') else s
    s = re.sub(r'<[^>]+>', ' ', s) if fn.endswith('.html') else s
    return re.sub(r'[\s\-{}"\\]', '', s).lower()
def key(p): return re.sub(r'[\s\-{}"\\]', '', p).lower()
checks = {
 'math9501233.txt': ["Fundamental Theorem of Myrmecology (Bunimovich-Troubetzkoy): An ant's track is always unbounded",
                     "attribution given there is incorrect", "rst appeared in [3]", "after about 10,000 time-units",
                     "southwesterly", "even run-length property", "conjecture", "Cohen", "Kong"],
 'nlin0306022.txt': ["about 10,000 steps", "it is conjectured", "has no corners [19]", "The system is P-hard",
                     "rather weak notion of universality", "remains an open question", "P-complete"],
 '1986-langton.txt': ["which we will call a rant", "which we will call a vant", "Vants", "periodic, self-limited pathway",
                      "10,000", "highway"],
 'stewart_anty.txt': ["Cohen-Kong Theorem", "X.P.Kong and E.G.D.Cohen", "Kung", "precisely 104 steps", "H-cell",
                      "no bounded trajectory exists", "Mathematical Intelligencer 15 No. 2 (1993)"],
 'tokarz.html': ["Cohen-Kung", "Cohen-Kong", "9977"],
 'wiki_raw.txt': ["Cohen]]-Kong theorem", "no one has been able to prove"],
 'etse.html': ["has never been formally established", "S_{n,n}-1", "with an error of 1 for"],
 'glr_v1.txt': ["280,085,922", "100,365,745", "256100"],
}
for fn, phrases in checks.items():
    s = norm(fn)
    print('==', fn)
    for p in phrases:
        print('  [%3d] %r' % (s.count(key(p)), p))
