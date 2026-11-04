# Task: The Matrix Multiplication Exponent ω = 2 — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is **ω = 2**: the exponent of square matrix multiplication
equals 2 — the central open problem of algebraic complexity (Strassen 1969
opened the subcubic regime; modern survey: Alman–Vassilevska Williams,
*A Refined Laser Method and Faster Matrix Multiplication*, SODA 2021).

The rank `R(T)` of a 3-tensor `T` is the
smallest number of rank-1 (simple) tensors summing to `T`; it is the
bilinear complexity of the associated bilinear map. Let `⟨m,n,p⟩` be the
matrix multiplication tensor — the structure tensor of multiplying an `m×n`
by an `n×p` matrix. The **exponent of matrix multiplication** is

    ω = inf { τ : ℝ | R(⟨n,n,n⟩) = O(n^τ) for some constant },

i.e. the infimum of all `τ` for which `R(⟨n,n,n⟩) ≤ C·n^τ` holds with some
constant `C`. The naive algorithm gives `ω ≤ 3`; Strassen's 1969
decomposition (`R(⟨2,2,2⟩) ≤ 7`) started a long descent whose current
frontier is `ω < 2.371177` (Dupont et al. 2026, arXiv:2608.16884;
previously 2.371339, Alman et al. 2025, and 2.371552,
Vassilevska Williams–Xu–Xu–Zhou 2024 before that). The only lower
bound on `ω` itself is the trivial `ω ≥ 2`, and barrier results
(Alman–Vassilevska Williams, FOCS 2018) show the current laser-method
framework cannot prove `ω = 2`. Whether `ω = 2` is **open**; a proof or a
super-quadratic lower bound would both be landmark results.

## What's in `/app/Task/Basic.lean`

The file (namespace `MatMulOmega`) has two zones:

- **Definition zone (do not modify).** 3-tensors as functions on multi-index
  triples (`Tensor3 F ι₁ ι₂ ι₃ := (ι₁ × ι₂ × ι₃) → F`); rank-1 tensors
  (`simpleTensor u v w`, `IsSimpleTensor`); **tensor rank** `tensorRank T`
  as the `sInf` of the set of decomposition lengths (`decompSet`), with the
  standard-basis expansion proved (`tensorRank_decomp_card`,
  `tensorRank_le_card`), rank-zero-iff-zero (`tensorRank_eq_zero`),
  rank-≤-1 for simple tensors (`tensorRank_le_one_of_isSimple`), and
  subadditivity (`tensorRank_add_le`). The **matrix multiplication tensor**
  `matMulTensor F m n p` with legs `Fin m × Fin n`, `Fin n × Fin p`,
  `Fin p × Fin m` (third leg in the `Tr(ABC)` convention), with a sanity
  lemma (`matMulTensor_contract`: contracting against `A`, `B` on the first
  two legs gives the entries of the matrix product `A * B`) and the **naive
  decomposition** (`tensorRank_matMulTensor_le`: `R(⟨m,n,p⟩) ≤ m·n·p`, and
  `one_le_tensorRank_matMulTensor`: `R(⟨n,n,n⟩) ≥ 1` for `n ≥ 1`). The
  exponent set `omegaSet F` and `matMulOmega F := sInf (omegaSet F)`, with
  the set proved **nonempty** (`omegaSet_nonempty`, via the naive cubic
  algorithm) and **bounded below by 0** (`omegaSet_nonneg_of_mem`,
  `omegaSet_bddBelow`) — so the `sInf` is a genuine infimum, not a Lean
  convention value. Convenience wrappers `matMulOmega_le_of_mem` (exhibit an
  algorithm with exponent `τ` to bound `ω ≤ τ`) and
  `le_matMulOmega_of_forall_le` (uniform lower bounds on achievable
  exponents bound `ω` from below). All API lemmas are fully proved; the base
  field for the conjecture is pinned to `ℚ`.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: `matMulOmega ℚ ≤ 2` (given the
     trivial lower bound `ω ≥ 2`, this is the statement `ω = 2`).
  2. `refuted` — its negation: `¬ matMulOmega ℚ ≤ 2` (a super-quadratic
     lower bound on `ω`; equally open).

## Rules

- Do not modify anything above the line `-- END OF FIXED PART`, the
  theorem statements, or the `-- CHECKPOINT ...` marker lines, and keep
  the two slots in their original order. The verifier compares the fixed
  part textually against a reference copy; any change scores 0.
- You may add your own auxiliary definitions and lemmas below the
  `-- END OF FIXED PART` line, outside the checkpoint slots, or in new
  files under `/app/Task/`.
- No new `axiom` declarations and no `native_decide`; the verifier
  rejects these lexically. Forbidden tokens anywhere in the file
  (comments are stripped before the scan): `axiom`, `sorryAx`,
  `native_decide`, `admitGoal`, `byAsSorry`, `skipKernelTC`,
  `implemented_by`. No `notation` / `macro` / `syntax` / `elab` /
  `macro_rules` / `initialize` declarations in the writable zone either;
  they are rejected as semantic-layer rewriting.
- `sorry`/`admit` left in a slot scores 0 for that slot. A `sorry` in
  your own auxiliary lemmas is not scanned for, but if a checked proof
  depends on it, the `#print axioms` check fails (`sorryAx` is never
  allowed) and the slot scores 0. A proof that discharges a slot from a
  helper-layer `False` is flagged as ex-falso and scores 0.

## How to work

You have a 12-hour budget and are expected to use it. Reaching "this looks
unprovable" is the beginning of the work, not the end of it. Do not submit
early with only a conclusion.

Work in this order:
1. **Fidelity check.** Verify the formalized statement matches your
   understanding of the literature (quantifiers, constants, degenerate
   cases). Look for exploitable gaps first — if the statement is trivially
   true/false as written, that is itself a finding worth reporting.
2. **Keep pushing approaches.** For each idea, actually push it forward in
   Lean: write lemmas, try compiling, record exactly where it breaks.
   After each failed approach, write down: what you tried, where it got
   stuck, and what mathematical tool is missing. Then look for the next
   angle. Keep going as long as you can generate distinct ideas — do not
   stop at a fixed count. Move to the research-note phase only when you
   are genuinely out of new angles or the budget is nearly exhausted.
3. **Side products that are always worth doing.** Auxiliary lemmas around
   the definition layer, formalizing known special cases from the
   literature, searching for counterexamples on small instances (kernel
   `decide` where feasible), and barrier analysis (why do known methods
   fail here?).
4. **Research note and artifacts before you finish.** Save your research
   note to `/logs/artifacts/` as a Markdown file: the approaches you
   tried and why each failed, what you verified along the way, and what
   would be needed to go further. Copy all exploration products to
   `/logs/artifacts/` as well, wherever you kept them during the work:
   Lean files with auxiliary lemmas and partial developments (for
   example `/app/scratch/`, an exploration section of `Task/Basic.lean`,
   or standalone files), search and experiment scripts, and computation
   logs. These artifacts are part of the deliverable. An empty
   submission (both slots left as `sorry` and no documented
   exploration) counts as unfinished.

You have **internet access** in this environment: use it. Look up the
current literature frontier on your problem (arXiv, Wikipedia, dblp,
Semantic Scholar), check whether known results or counterexamples exist
that bear on your statement, and cite what you actually consulted in your
research note. Do not trust your training memory for the state of the art —
verify it online.

The floor rules never change: `sorry` scores 0, planted axioms score 0,
ex-falso tricks score 0 and get flagged. Never fabricate a proof.

## Scoring

- Each slot is graded in isolation: the other slot is removed on the
  grader side, never injected as an axiom, so a proof of one slot never
  sees its contradictory twin (and can never exploit it).
- All-or-nothing per slot: the score is **1.0** if the project compiles
  with a slot proved (no `sorry`) using only the standard axioms
  (`propext`, `Classical.choice`, `Quot.sound`), and **0** otherwise.
  There is no partial credit: if neither slot passes, the score is 0.

## Environment

The project builds offline against the mathlib checkout at
`/opt/lean-lib/mathlib4`; use `lake build Task` in `/app` to check.
