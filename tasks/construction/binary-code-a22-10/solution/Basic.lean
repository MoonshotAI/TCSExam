import Mathlib

set_option maxRecDepth 100000
set_option maxHeartbeats 0

-- Instance synthesis for `MinDist10Code` on a concrete code needs more
-- than the default `synthInstance.maxSize` (128): the zipped pair loop
-- nests `List` and `Nat` instance trees. 512 gives comfortable headroom
-- so that `decide` / `native_decide` work on `MinDist10Code S` directly.
set_option synthInstance.maxSize 512

/-!
# Binary codes of length 22 and minimum distance 10 — fixed definition layer

A **binary error-correcting code** of length 22 and minimum Hamming
distance 10 is a set `S` of 22-bit words such that every two distinct
codewords differ in at least 10 positions. The largest possible size is
`A(22,10)`, known only to lie in `64 ≤ A(22,10) ≤ 84` (see
`instruction.md` for references).

Words are functions `Fin 22 → Fin 2`; `hammingDist x y` (mathlib) counts
the coordinates on which `x` and `y` differ. A code is presented as a
**list** of words; `isMinDist10Code S` below checks computably that `S`
has minimum distance at least 10, and `MinDist10Code S` packages the
check as a proposition.

Everything from the top of this file down to the line
`-- END OF FIXED PART` is part of the problem statement. The judge checks
it verbatim; do not edit, move, or delete it. Your work (auxiliary
definitions, lemmas, and the proofs of the claims) goes below the mark.
-/

/-- `isMinDist10Code S` is the computable predicate "the list `S` of
22-bit words is a binary code of length 22 and minimum Hamming distance
10":

1. `S` is nonempty;
2. for every pair of positions `i ≠ j` in `S`, the words at those
   positions differ in at least 10 coordinates (`hammingDist x y ≥ 10`).

This matches the checker of the solver sibling task `binary-code-a22-10`
clause by clause:

- **duplicate words** need no clause of their own: two positions carrying
  the same word have Hamming distance `0 < 10`, so clause 2 already
  rejects every list with duplicates, exactly as the checker rejects
  them;
- clause 2 quantifies over **positions** (via `List.zipIdx`), so the
  diagonal cases `i = j` (where the distance would be 0) are excluded,
  while every pair of distinct positions is checked — the checker's
  pairwise `d < 10` rejection, read contrapositively;
- an **empty** list is rejected by clause 1, exactly as the checker
  requires a nonempty codeword list.

All clauses live inside a single computable `Bool` function, so `decide` /
`native_decide` check concrete codes directly and no per-clause
`Decidable` instance synthesis is involved. Quantifying over positions
with `Bool`-valued comparisons also keeps equality of words (`x = y` on
`Fin 22 → Fin 2`) out of the decision procedure entirely.

A computable `isMinDist10Code S = true` (packaged as `MinDist10Code S`)
together with `k ≤ S.length` certifies `A(22,10) ≥ k`; a proof that
`MinDist10Code S` implies `S.length ≤ m` for every `S` certifies
`A(22,10) ≤ m` (every valid list has pairwise distinct words, so its
length is the cardinality of its set of words). -/
def isMinDist10Code (S : List (Fin 22 → Fin 2)) : Bool :=
  decide (0 < S.length) &&
    S.zipIdx.all fun (x, i) =>
      S.zipIdx.all fun (y, j) =>
        i == j || decide (hammingDist x y ≥ 10)

/-- `MinDist10Code S` packages the computable predicate as the proposition
`isMinDist10Code S = true`.

Marked `@[reducible]` so that decidable instances for concrete codes are
found by typeclass resolution (`by native_decide` can check concrete
codes directly). -/
@[reducible]
def MinDist10Code (S : List (Fin 22 → Fin 2)) : Prop := isMinDist10Code S = true

-- END OF FIXED PART

/- Sanity oracle: the 48-word punctured Paley–Hadamard code (the rows of a
Hadamard matrix of order 24 from Paley's construction on GF(23), together
with their complements, punctured on the last two coordinates), the same
construction as the solver sibling's `examples/example_hadamard48.json`,
which passes the solver checker at score 0.408412. Codewords are stored as
the 22-bit integers of that file; the minimum-distance condition and the
length bound are proved by `native_decide` (allowed: the judge's axiom
whitelist includes `Lean.ofReduceBool` / `Lean.trustCompiler`). -/

/-- The 22-bit word whose `i`-th coordinate is bit `i` of `n`. -/
def wordOfNat (n : Nat) : Fin 22 → Fin 2 :=
  fun i => ⟨(n / 2^i.val) % 2, Nat.mod_lt _ (by decide)⟩

/-- The punctured Paley–Hadamard code: the 48 codewords of
`example_hadamard48.json` read as 22-bit integers. -/
def hadamardCode : List (Fin 22 → Fin 2) :=
  [    0, 125747, 170414, 251493, 340830, 502987, 659289, 681662,
    827637, 841666, 883752, 1005973, 1080013, 1258992, 1318579, 1363324,
    1467655, 1557144, 1655275, 1676319, 1683332, 1767506, 2011945, 2034278,
    2160025, 2182358, 2426797, 2510971, 2517984, 2539028, 2637159, 2726648,
    2830979, 2875724, 2935311, 3114290, 3188330, 3310551, 3352637, 3366666,
    3512641, 3535014, 3691316, 3853473, 3942810, 4023889, 4068556, 4194303
   ].map wordOfNat

theorem submission_lower :
    ∃ S : List (Fin 22 → Fin 2), MinDist10Code S ∧ 48 ≤ S.length :=
-- CLAIM submission_lower BEGIN
by
  exact ⟨hadamardCode, by native_decide, by native_decide⟩
-- CLAIM submission_lower END

theorem submission_upper :
    ∀ S : List (Fin 22 → Fin 2), MinDist10Code S → S.length ≤ 460 :=
-- CLAIM submission_upper BEGIN
by
  sorry
-- CLAIM submission_upper END
