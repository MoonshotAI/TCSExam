# Task: The extremal function ex(n, {C3, C4}) — Open Construction

A Lean 4 project lives in `/app`. `Task/Basic.lean` contains a
definition layer and a claim slot (`submission_lower`) — prove the
strongest claim you can. The verifier independently evaluates your best
proven claim against the published literature frontier when the budget
ends; stronger is better, with no upper limit.

The extremal function `ex(n, {C3, C4})` is the largest number of edges in
a graph on `n` vertices containing **no triangle (`C3`) and no 4-cycle
(`C4`)** — equivalently, a graph of girth (shortest cycle length) at least
5. It is a classic Erdős extremal problem; even the asymptotic leading
constant is open.

The function is known exactly only up to `n = 53` (Afzaly–McKay,
*Extremal graphs and Turan numbers* data page,
<https://users.cecs.anu.edu.au/~bdm/data/extremal.html>). For every
`n ≥ 54` only construction records exist, with no upper-bound proofs. The
standing records were computed by J. Goedgebeur, J. Jooken, G. Joret and
J. Van den Eede, *New lower bounds for the extremal number of cycles*,
2025 ([arXiv:2508.05562](https://arxiv.org/abs/2508.05562); to appear in
Experimental Mathematics) with roughly 380 CPU-days of local search; the
record graphs are published at
<https://github.com/AGT-Kulak/searchMaxSizeMinGirth>.

This task fixes the main order **`n = 124`**, where the published record
is **629 edges** (the previous record was 611; the smallest `(10,5)`-graph
has 620 edges and was long believed optimal — the 2025 record shows the
winning constructions are not regular). A Lean-certified graph with 630
edges or more is a literature-level new result: it improves the best known
lower bound on `ex(124, {C3,C4})`.

This task is unrelated to the Ramsey-style tasks in the library
(`ramsey-r3-10` and friends): there the number of *vertices* is the
objective and large *independent sets* are what you avoid; here the order
is fixed at 124, *4-cycles* are what you avoid, and the *edge count* is
the objective. The only superficial overlap is "no triangles".

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** The fixed definition layer gives
  you:

  - `Gph n` — a graph on `n` vertices as an adjacency function
    `adj : Nat → Nat → Bool` (data only, no proof fields);
  - `ofEdges n es` — builds a `Gph n` from an edge list
    `es : List (Nat × Nat)` (symmetric closure);
  - `WellFormed n g : Bool` — the adjacency is symmetric and loopless;
  - `edgeCount n g : Nat` — the number of edges (pairs `i < j`);
  - `NoC3 n g : Bool` — no triangle (no triple with all three adjacencies);
  - `NoC4 n g : Bool` — no 4-cycle, as pure counting: any two distinct
    vertices have at most one common neighbour;
  - `C3C4Free n g : Bool` — `NoC3 && NoC4` (girth at least 5).
- **Claim slot.** Below the line `-- END OF FIXED PART`, prove the claim
  `submission_lower`:

  ```lean
  theorem submission_lower : ∃ g : Gph 124,
      WellFormed 124 g = true ∧ C3C4Free 124 g = true ∧ edgeCount 124 g ≥ m
  ```

  where **you choose the numeral `m`** — the larger the better. You may
  change **only** that numeral in the claim statement (the three `124`s are
  fixed); the claim body must stay between its
  `-- CLAIM submission_lower BEGIN/END` markers.

  Everything is a computable `Bool` predicate over concrete data, so a
  certificate is just a witness edge list plus evaluation:

  ```lean
  def myEdges : List (Nat × Nat) := [(0, 82), (0, 84), "..."]

  theorem submission_lower : ∃ g : Gph 124,
      WellFormed 124 g = true ∧ C3C4Free 124 g = true ∧ edgeCount 124 g ≥ m := by
  -- CLAIM submission_lower BEGIN
    exact ⟨ofEdges 124 myEdges, by native_decide, by native_decide, by native_decide⟩
  -- CLAIM submission_lower END
  ```

  **`native_decide` is allowed and is the intended certificate path**: the
  judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler` alongside
  the three standard axioms. The judge automatically lets `native_decide`'s
  generated internal axioms (`._native.native_decide.ax_*`) through;
  `native_decide` can be used directly. At the record region (`m ≈ 630`) the three
  evaluations take seconds; there is no need for clever proof engineering.

  Bringing the graph as data is your
  job — fetch a published one from the literature or search with any
  auxiliary code you like (see Notes), then convert
  the result (the same JSON edge-list format as the solver sibling task;
  `/app/examples/json_to_lean.py` turns such a JSON file into a Lean
  literal).

**Sanity anchors.**

- `/app/examples/example_n124_greedy.json` — a valid 483-edge girth-5
  graph on 124 vertices. Convert it with
  `json_to_lean.py` and prove the claim at `m = 483` to exercise the whole
  pipeline: witness representation, `native_decide`, and the claim interface.
- `/app/examples/example_petersen_n10.json` — the Petersen graph (10
  vertices, 15 edges, girth 5). Tiny sanity anchor for the constraint
  logic (it is not the task's order: the claim fixes `n = 124`).

## Rules

1. Do not change any **code** above the line `-- END OF FIXED PART`; the
   verifier compares it (comments stripped, whitespace-normalized)
   against its reference. Comments and docstrings up there are free to
   edit — they do not affect judging.
2. In the claim statement you may change **only the numeral `m`**
   (`1 ≤ m ≤ 7626`); the claim body must stay between its markers.
3. No `sorry` / `admit` outside the claim body; a body that still
   contains one is simply not scored. No `axiom` / `sorryAx` anywhere.
4. The whole file must compile, and the scored claim must depend only on
   the whitelisted axioms (`propext`, `Classical.choice`, `Quot.sound`,
   `Lean.ofReduceBool`, `Lean.trustCompiler`) — `#print axioms` is
   checked by the verifier.
5. Do not close `namespace ExC3C4`. Auxiliary definitions and lemmas are
   free.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (629 edges) is the beginning of the work, not the end
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
   harder cell. Every strictly stronger certified bound counts for more.
   Keep going as long as you can generate distinct ideas —
   do not stop at a fixed count.
3. **Use the internet.** Look up the literature (constructions,
   records, techniques) rather than trusting training memory. Certifying
   a published record ties it; going beyond it takes a strictly stronger
   object the literature does not have.

The floor rules never change: a scored claim must not contain `sorry`,
planted axioms or redefinition tricks are rejected. Never fabricate a
proof.

## Scoring

The verifier re-checks your Lean proof, parses `m` from the proven claim,
and independently evaluates it against the published literature frontier
(629 edges for `n = 124`). **A strictly stronger certified bound is
always better, and there is no upper limit** — the published record is
the bar to beat, and beating it (any `m ≥ 630`) is a literature-level
new result.

## Environment

The project builds offline with `lake build Task` in `/app`; no mathlib
(the fixed layer is self-contained). Agent budget: 12 hours. The
container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- The final compile-plus-evaluate check takes seconds at the record scale.
- The solver sibling task `ex-c3c4-maxedges` documents the search side of
  this problem (the greedy construction, published records on four orders,
  constraint-checking code). Its notes apply verbatim: known near-record
  constructions are highly structured but **not** regular — the 2025
  records break the `(k,5)`-graph pattern with a few vertices of degree
  `k±1` around a mostly-regular core, found by up/down local search.
  Writing your own search code (simulated annealing on the C3/C4
  violation count, local swaps from a structured seed) and certifying its
  output here is the intended workflow.
- The 629-edge record graph is published in the AGT-Kulak repository; it
  is not in this container; fetching it is allowed. Reproducing a
  published construction (fetched or from memory) only ties the record;
  going beyond starts at 630.
