# Task: The cage problem — Open Construction

A Lean 4 project lives in `/app`. `Task/Basic.lean` contains a
definition layer and a claim slot (`submission_lower`) — prove the
strongest claim you can. The verifier independently evaluates your best
proven claim against the fixed scoring references when the budget
ends; stronger is better, with no upper limit — smaller is better here (you certify an order bound `N`).

The **girth** of a graph is the length of its shortest cycle. A
**(k,g)-cage** is a smallest `k`-regular graph of girth `g`, and its order
is the cage number `n(k,g)`. Exact cage numbers are known only in a
handful of cases; the world keeps open intervals between proved lower
bounds and the best known constructions. This task asks for a
machine-checked certificate of the construction side: a nonempty `k`-regular graph
of girth at least `g` on at most `N` vertices, proving `n(k,g) <= N` in
Lean 4.

The task cells (only girth `>= g` is required — by Sachs's theorem a
minimum-order `k`-regular graph of girth `>= g` automatically has girth
exactly `g`):

| cell (k,g) | lower bound | fixed scoring reference | reference source |
|---|---|---|---|
| (3,13) | 202 | 272 | Hoare's Cayley graph of AGL(1,17), reported in Biggs 1989 |
| (4,10) | 243 | 320 | Exoo, Goedgebeur, Jooken, Stubbe, Van den Eede 2026 |
| (3,16) | 512 | 936 | Exoo et al. 2026 (same paper) |
| (4,11) | 486 | 713 | Exoo et al. 2026 (same paper) |
| (3,17) | 768 | 2048 | Exoo et al. 2026 (same paper) |
| (3,5) (sanity, closed cell) | 10 | 10 | the Petersen graph |

- **(3,13) = [202, 272]** is the famous cell: the lower bound is a
  computer proof (McKay–Myrvold–Nadon, *Proceedings of the 9th
  ACM-SIAM Symposium on Discrete Algorithms (SODA 1998)*, 188–191);
  the record is the
  cubic Cayley graph of the affine group `AGL(1,17)` (order 272 = 17·16),
  reported in N. L. Biggs, *Cubic graphs with large girth*, Annals of the
  New York Academy of Sciences 555 (1989), 56–62, unmoved for 37 years
  and singled out as open problem #5 of the Dynamic Cage Survey
  (Exoo–Jajcay, Electronic Journal of Combinatorics, DS16, 2013). Royle
  proved (2001) that no smaller (3,13) graph is a Cayley graph.
- The other four records were set in G. Exoo, J. Goedgebeur, J. Jooken,
  A. Stubbe, J. Van den Eede, *New small regular graphs of given girth:
  the cage problem and beyond*, Electronic Journal of Combinatorics 33(3),
  2026
  ([arXiv:2511.07247v2](https://arxiv.org/abs/2511.07247v2)), replacing
  records that had stood about 22 years. The lower bounds are Moore-bound
  refinements (Feit–Higman 1964; Biggs–Ito; parity).
- **Authoritative tracking**: the House of Graphs
  [cages page](https://houseofgraphs.org/meta-directory/cages) lists current constructions. The scoring references above remain fixed.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** The fixed definition layer gives
  you:

  - `CageGraph` — a finite simple graph on `n` vertices, adjacency as a
    Nat-indexed `Bool` function;
  - `WellFormed G : Prop` — the graph has at least one vertex, and its
    adjacency is symmetric and irreflexive on the vertex range (computable);
  - `IsKRegular G k : Prop` — every vertex has exactly `k` neighbors
    (computable);
  - `GirthGE G g : Prop` — the girth is at least `g`: per-root BFS to
    depth `(g-1)/2` flags any cycle shorter than `g` (computable).
- **Claim slot.** Below the line `-- END OF FIXED PART`, prove the claim
  `submission_lower`:

  ```lean
  theorem submission_lower : ∃ G : CageGraph, WellFormed G ∧ IsKRegular G k ∧
      GirthGE G g ∧ G.n ≤ N := by
  ```

  where **you choose the numerals `k`, `g` and `N`** — the cell you target
  and the claimed order bound; smaller `N` is better. You may change
  **only** the three numerals in the claim statement; the claim body must
  stay between its `-- CLAIM submission_lower BEGIN/END` markers. The
  task cells are `(3,13)`, `(4,10)`, `(3,16)`, `(4,11)` and `(3,17)`; the
  closed cell `(3,5)` serves as the sanity check.

  Bring your own graph as data — typically a `CageGraph` defined by a rule
  (group multiplication, congruences, a lift), not a giant literal table —
  and prove the claim, e.g.
  `exact ⟨myGraph, by native_decide, by native_decide, by native_decide, by decide⟩`.
  **`native_decide` is allowed and is the intended certificate path**: the
  judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`, alongside
  the three standard axioms. The judge automatically lets `native_decide`'s
  generated internal axioms (`._native.native_decide.ax_*`) through;
  `native_decide` can be used directly. At the record scales (`N <= 2048`) the BFS
  predicate evaluates under `native_decide` in seconds.

**Sanity anchors.**

- `/app/examples/petersen_snippet.lean.txt` — the Petersen graph as a
  worked `CageGraph` witness (the (3,5)-cage, the sanity cell).
  Proving the claim for it exercises the whole pipeline: fixed layer,
  graph representation, `native_decide`, and the claim interface.

## Rules

- Do not change any **code** above the line `-- END OF FIXED PART`; the
  verifier compares it (comments stripped, whitespace-normalized) against
  its reference. Comments and docstrings up there are free to edit — they
  do not affect judging.
- Keep the interface name `submission_lower` and the pinned claim shape;
  the verifier parses `k`, `g` and `N` from the claim header.
- No `axiom` / `sorryAx` anywhere; `sorry` / `admit` only inside the
  claim body, and a body that still contains one is simply not scored.
  Every scored claim must depend only on the whitelisted axioms
  (`propext`, `Classical.choice`, `Quot.sound`, `Lean.ofReduceBool`,
  `Lean.trustCompiler`) — `#print axioms` is checked.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (the per-cell records in the Background table) is the beginning of the work, not the end
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

The verifier re-checks your Lean proof, parses `(k, g, N)` from the
proven claim, and independently evaluates `N` against the published
literature frontier (the record column of the Background table: 272 for
(3,13), 320 for (4,10), 936 for (3,16), 713 for (4,11), 2048 for (3,17)).
**A strictly stronger certified bound is always better, and there
is no upper limit** — the record of your chosen cell is the bar to beat,
and beating it (any `N` below the record) is a literature-level new
result; for (3,13) it ends a 37-year standstill. Reaching a cell's lower
bound would prove `n(k,g) = N` exactly and close the cell; a claim below
the lower bound contradicts a published theorem.

## Environment

The project builds offline with `lake build Task` in `/app`.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- The record constructions are highly structured: the (3,13) record is a
  Cayley graph of `AGL(1,17)` (the 272 affine maps `x -> a*x + b` over
  the 17-element field, adjacent by a fixed 3-element connection set),
  and the 2026 records are lifts (voltage-graph covers) over small
  groups, bipartite for even girth. Rule-defined witnesses keep both the
  file small and `native_decide` fast.
- The final check itself is seconds at these scales. A certified
  published record only ties it; aim beyond.
