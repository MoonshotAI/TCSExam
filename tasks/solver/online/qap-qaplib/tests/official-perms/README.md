# QAPLIB Optimal Permutations for Oracle Validation

This directory stores known-optimal permutations for all 136 official QAPLIB instances: 134 listed on the official site, plus exhaustive witnesses for `tai10a` and `tai10b`. Every permutation uses a 1-based forward encoding: token `i` is the location assigned to facility `i`. Recomputing it on the official instance reproduces the listed `K` exactly.

These permutations supply oracle inputs for the structure-preserving transformation of the judged set. Running `tests/transform.py bake-oracle` applies p'(π(i)) = σ(p(i)) and writes the replay package to `solution/precomputed/`. The environment-side `.sln` files under `environment/app/solutions` were removed as part of the lookup-table-memorization fix; the data remain available on the official site. This directory is now the repository's only copy of the listed permutations.

`manifest.json` maps the SHA-256 of each official instance’s token stream to `{instance, perm, K, interpretation}`. `interpretation` records encoding quirks in the official `.sln` files: `tai40a` is 0-based, while `tai60a` and `tai80a` use inverse permutations. All `.perm` files here have already been converted to forward 1-based form; the original quirks remain for reference.
