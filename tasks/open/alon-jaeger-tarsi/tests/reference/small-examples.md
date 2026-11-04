# Executable Small Examples: Numerical Enumeration for Alon–Jaeger–Tarsi Special Cases

A small pure-Python enumeration checks the numerical facts behind the task's three special-case checkpoints. Actual output is recorded below.

- Script: `tests/reference/enumerate_small.py` (standard library only; runs in seconds).
- Raw output: `enumerate_small.out` ().

## Enumeration method

For a prime p and dimension n, enumerate all p^(n²) n×n matrices over F_p and retain those with nonzero determinant modulo p. For each nonsingular matrix, search for a vector x with every coordinate nonzero such that A·x also has every coordinate nonzero (each coordinate of x ranges over 1..p−1, giving (p−1)^n candidates). This corresponds exactly to `HasAJTVector` and `A.det ≠ 0` on the Lean side.

## Numerical results

Each row gives one (p,n) case. “Has an AJT vector” counts nonsingular matrices for which a valid x exists. The conclusion states whether every nonsingular matrix in that case has an AJT vector.

| p | n | Total matrices | Nonsingular | Has an AJT vector | Conclusion |
|---|---|---|---|---|---|
| 2 | 2 | 16 | 6 | 2 | False: 4 of the 6 nonsingular matrices are counterexamples (first is `[[0,1],[1,1]]`). |
| 3 | 1 | 3 | 2 | 2 | True (first branch of checkpoint `ajt_p3_small`). |
| 3 | 2 | 81 | 48 | 40 | False: 8 of the 48 are counterexamples; first is `[[1,1],[1,2]]` (second branch of `ajt_p3_small`, which asserts a counterexample exists). |
| 5 | 2 | 625 | 480 | 480 | True (checkpoint `ajt_p5_n2`). |

## Cross-checks

- **Count of nonsingular matrices:** agrees with |GL_n(F_p)| = (pⁿ−1)(pⁿ−p). For n = 2 this is (p²−1)(p²−p), giving 6 at p = 2, 48 at p = 3, and 480 at p = 5; each matches the enumeration.
- **Hand check of the first counterexample at p = 3:** A = `[[1,1],[1,2]]` (note that 2 = −1 mod 3). The only vectors in F₃² with both coordinates nonzero are (1,1), (1,2), (2,1), and (2,2). Their images under A are (2,0), (0,2), (0,1), and (1,0), each with a zero coordinate. The four lines through the origin x₁=0, x₂=0, x₁+x₂=0, and x₁−x₂=0 cover F₃²: there are p+1 = 4 lines, each with 2 nonzero points plus the origin, for all 9 points. Thus every x fails.
- **Counting argument for p = 5, n = 2** (theoretical explanation of the enumeration): the equations x₁=0, x₂=0 and the two rows of A each determine a line through the origin. There are at most 4 distinct lines, covering at most 4·(p−1)+1 points. At p = 5 this is 17 < 25 = p², so some point lies outside their union. The same argument proves the result for every p ≥ 5 when n = 2. At p = 3, 4·2+1 = 9 = p², exactly covering all points, as above.
- **n = 1 (checkpoint `ajt_n1`) needs no enumeration:** a nonsingular 1×1 matrix has a nonzero entry, so x = (1) works for every prime p. The Lean proof is general and does not use `decide`.

## Correspondence with the Lean statements

- `ajt_p3_small` is “all matrices satisfy the claim at p = 3, n = 1” ∧ “there is a counterexample at p = 3, n = 2”; the second and third rows support the two branches, respectively. The conjunction is decidable on the Lean side (`decide`; the probe passed).
- `ajt_p5_n2` is the universal claim in the fourth row; it is decidable (`decide`). In the probe, default recursion depth was insufficient; after `set_option maxRecDepth 16384 in`, the kernel decided it in about 18 seconds.
- `ajt_n1`: a general proof; the probe passed using `Matrix.det_fin_one` and `Fin.sum_univ_one`.
- The p = 2 row is background only (the other side of the conjectured threshold q ≥ 4); it is not a checkpoint.
