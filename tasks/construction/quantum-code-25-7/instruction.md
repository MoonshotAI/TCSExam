# Task: A quantum stabilizer code [[25,7]] — Open Construction

A **quantum error-correcting code** `[[n,k,d]]` encodes `k` logical qubits
into `n` physical qubits and corrects arbitrary errors on any
`⌊(d−1)/2⌋` positions; the larger the distance `d`, the better. In the
**stabilizer** formalism a code is presented by `n−k` independent,
pairwise-commuting **generators**, each an `n`-letter Pauli string over
`{I,X,Y,Z}` (phases dropped); the group `S` they generate is the
stabilizer.

**Distance semantics — read this twice.** The distance is the minimum
weight (number of non-`I` positions) of a Pauli operator that commutes
with every generator but is **not itself in `S`** — the minimum weight of
`N(S) ∖ S`, where `N(S)` is the normalizer. `S` may contain low-weight
elements (**degenerate** codes); the published record code for `[[25,7]]`
is degenerate — it has weight-1 elements inside `S`, so "the lightest
Pauli commuting with everything" reads `1` on it, while the correct
distance is `5`.

The accepted interval for `[[25,7]]` is `5 ≤ d ≤ 7`:

- **Record `d = 5`**: a cyclic `[[21,7,5]]` code over GF(4) extended by 4
  positions; machine-readable stabilizer matrix on the `n=25, k=7` detail
  page of Markus Grassl's quantum code table
  ([codetables.de/QECC](https://www.codetables.de/QECC/index.html)), the
  community reference table; the entry has stood since **2005-06-24**
  ().
- **Upper bound `d ≤ 7`**: the quantum linear-programming bound (weight
  enumerators plus Rains' shadow enumerators): E. M. Rains, *Quantum
  weight enumerators*, IEEE Transactions on Information Theory 44(6),
  1998; *Quantum shadow enumerators*, 45(7), 1999 — independently
  recomputed for this task (LP feasible at `d = 7`, infeasible at
  `d = 8`).

A certified `d = 6` beats a 21-year-old record (a literature-level new
lower bound); a certified `d = 7` meets the proven upper bound and
**closes** the parameter point.

## What's in `/app/Task/Basic.lean`

In `/app/Task/Basic.lean`, below the line `-- END OF FIXED PART`, prove
the claim `submission`:

```lean
theorem submission : ∃ gens : Fin 18 → Pauli25, IsStabilizer gens ∧ DistanceGE gens d
```

where **you choose the numeral `d`** — the larger the better. You may
change **only** the numeral in the claim statement; the claim body must
stay between its `-- CLAIM submission BEGIN/END` markers.

The fixed definition layer (do not modify; mathlib-free) gives you:

- `Pauli25` — a Pauli operator as two `BitVec 25` masks `(x|z)`
  (`I=(0,0)`, `X=(1,0)`, `Z=(0,1)`, `Y=(1,1)`; string position `i` is bit
  `i`);
- `IsStabilizer gens : Prop` — the 18 generators pairwise commute
  (symplectic) and have GF(2) rank exactly 18 (rank 18 ⇔ `k = 7`);
- `DistanceGE gens d : Prop` — every Pauli of weight `< d` that commutes
  with all 18 generators lies in the generated group `S` (the `N(S) ∖ S`
  semantics; exact, by exhaustive weight sweep).

Bring your own generators as data — typically an `Array Pauli25` of
`BitVec.ofNat 25` literals plus a lookup `Fin 18 → Pauli25` — and prove
the claim, e.g. `exact ⟨myGens, by native_decide, by native_decide⟩`.
**`native_decide` is allowed and is the intended certificate path**: the
judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`, alongside
the three standard axioms. The judge automatically lets `native_decide`'s
generated internal axioms (`._native.native_decide.ax_*`) through;
`native_decide` can be used directly.

**Cost of the check.** The distance sweep is exact but big: certifying
`d = 5` scans ~1.1 million candidates, `d = 6` ~14 million, `d = 7` ~143
million. Under `native_decide` (compiled to native code) the record tier
evaluates in seconds and the closure tier in minutes (measured on the
judge toolchain; see PROVENANCE.md); kernel `decide` does not scale here.

**Sanity anchors.**

- `/app/examples/example_trivial_d1.json` — the trivial example
  `[[25,7,1]]` (generators `Z₈…Z₂₅`, 7 qubits unencoded). Proving
  `IsStabilizer` and `DistanceGE · 1` for it exercises the whole pipeline
  (table representation, `native_decide`, and the claim interface).
- `/app/examples/example_random_d4.json` — a random stabilizer code with
  exact `d = 4`. Random blind search floors at `d ∈ {3, 4}` (24-sample
  calibration on the solver side); the interesting region is `d = 5`
  (the record), `d = 6` (a new result), `d = 7` (closure).
- The record generator matrix is **not** in the container — fetch it from
  codetables.de (see Background) or build your own (either ties the record;
  the goal is `d >= 6`). Hints:
  GF(4)-cyclic/constacyclic and BCH families, lengthening known good
  codes, CSS constructions from classical pairs, SAT/ILP/heuristic search
  over self-orthogonal subspaces.

## Rules

- Do not change any **code** above the line `-- END OF FIXED PART`; the
  verifier compares it (comments stripped, whitespace-normalized) against
  its reference. Comments and docstrings up there are free to edit — they
  do not affect judging.
- Keep the interface name `submission` and the pinned claim shape; the
  verifier parses `d` from the claim header and re-states your proven
  claim against the root `IsStabilizer` / `DistanceGE` as a consistency
  check.
- No `axiom` / `sorryAx` anywhere; no redefinition tricks: the tokens
  `notation`, `macro`, `syntax`, `elab`, `opaque`, `unsafe`, `extern`,
  `implemented_by`, `initialize` and the option `skipKernelTC` are
  forbidden everywhere in the file. `sorry` / `admit` only inside the
  claim body, and a body that still contains one is simply not scored.
- Every scored claim must depend only on the whitelisted axioms
  (`propext`, `Classical.choice`, `Quot.sound`, `Lean.ofReduceBool`,
  `Lean.trustCompiler`) — `#print axioms` is checked.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (distance 5) is the beginning of the work, not the end
of it — do not submit early with only a tied record. Stronger is
better, with no upper limit.

Work in this order:
1. **Anchor check.** Verify the frontier values in the Background
   against the linked sources — if an anchor looks stale or wrong, say
   so in your final summary rather than trusting it blindly.
2. **Bank a claim early, then keep improving.** Get one certified
   claim on the board (a sanity cell exercises the pipeline; a fetched
   published construction ties the record), then keep pushing:
   improve your construction, try a different method, or attack a
   harder cell. Every strictly stronger certified bound counts for
   more. Keep going as long as you can generate distinct ideas —
   do not stop at a fixed count.
3. **Use the internet.** Look up the literature (constructions,
   records, techniques) rather than trusting training memory. Certifying
   a published record ties it; going beyond it takes a strictly
   stronger object the literature does not have.

The floor rules never change: a scored claim must not contain `sorry`,
planted axioms or redefinition tricks are rejected. Never fabricate a
proof.

## Scoring

The verifier re-checks your Lean proof, parses `d` from the proven claim,
and independently evaluates it against the published literature frontier
(distance 5, the extended cyclic `[[21,7,5]]` code on Grassl's table,
standing since 2005). **A strictly stronger certified bound is
always better, and there is no upper limit** — the published record is
the bar to beat: a certified `d = 6` is a literature-level new lower
bound, and `d = 7` meets the proven upper bound and closes the parameter
point. A claim at `d ≥ 8` contradicts the proven linear-programming upper
bound.

## Environment

The project builds offline with `lake build Task` in `/app`.
Agent budget: 12 hours. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.
