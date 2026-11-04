# Independent Retranslation: A Second Lean Formulation of the Log-Rank Conjecture

This record independently formalizes the log-rank conjecture in Lean 4 from the literature statement, without consulting shipped `Task/Basic.lean`, then compares the two versions. It is the second of three fidelity records (independent retranslation).

- The retranslation was completed after the shipped version was finalized, using the literature and textbook background.

## Source statement

The standard form of the Lovász–Saks conjecture (FOCS 1988 / JCSS 1993), as stated in Lovett 2014 and related literature:

> There exists a universal constant `c` such that for every two-party Boolean
> function `f : X × Y → {0,1}`, the deterministic communication complexity
> satisfies `D(f) ≤ (log rank(M_f))^c`, where `M_f` is the communication
> matrix and the rank is over the reals.

Textbook definition (Kushilevitz–Nisan, §1): a protocol is a binary tree whose internal nodes belong to one party and branch on one bit of that party's input; leaves give the output. D(f) is the minimum depth of a protocol computing f.

## Independently written Lean draft

```lean
inductive Proto (X Y : Type) : Type
  | out : Bool → Proto X Y
  | askA : (X → Bool) → Proto X Y → Proto X Y → Proto X Y
  | askB : (Y → Bool) → Proto X Y → Proto X Y → Proto X Y
-- depth / eval / computes are recursive functions, same form as shipped (omitted)

def M (f : X → Y → Bool) : Matrix X Y ℝ := fun x y => if f x y then 1 else 0

def logRank : Prop :=
  ∃ c : ℝ, c > 0 ∧ ∀ {X Y : Type} [Fintype X] [Fintype Y] (f : X → Y → Bool),
    (D f : ℝ) ≤ (1 + Real.logb 2 (M f).rank) ^ c
```

## Component-by-component comparison with the shipped version

| Component | Retranslation draft | Shipped version | Finding |
|---|---|---|---|
| Protocol tree | Three-constructor inductive type; each node is labeled with its owner and queries an arbitrary Boolean function of one party's input | `Protocol`, isomorphic (`leaf`/`alice`/`bob`) | Match; this is the textbook protocol's natural inductive representation. |
| Communication matrix | Directly `fun x y => if f x y then 1 else 0 : Matrix X Y ℝ` | `commMatrix`, identical | Match |
| D | Minimum attainable depth (the retranslation also needs an `sInf`/minimum-value approach and proof that the set is nonempty) | `sInf` plus existence lemma `pinpoint` | Match. The trivial protocol establishing nonemptiness (enumerate X one by one) was independently identified as the simplest construction. |
| Quantifiers | There exists c > 0; universal over finite types | Same | Match |
| Premise `2 ≤ rank` | Omitted in the first retranslation; after checking the rank-1 degenerate function u∧v (log = 0, D = 2), confirmed that the premise must be added | Included | The shipped version is more precise; the independent cross-check found the same degenerate case. |
| `1 + log₂` | First draft used a pure power; testing EQ on one bit (rank 2, log = 1, D = 2) showed that the pure-power version must fail, so it was changed to `1 + log₂` | `1 + log₂` | Both independently found the same necessity by different routes. |
| Logarithm base | Base 2 | Base 2 | Match (bit units; a change of base is absorbed into a constant factor under a power, but formalization must choose one). |
| Real exponent | `Real.rpow` (c is real) | Same | Match (there is no reason to restrict c to an integer or natural number). |

## Differences and remaining scope

- The two omissions in the first draft (premise rank ≥ 2 and the `1 + log₂` form) were independently caught by testing degenerate instances, yielding the same final form as shipped. They were not copied: both passes independently found the same mathematical constraints. These are the main fidelity risks in this task; deviations 1/2 of `concept-ledger.md` contain the full arguments.
- There is no room for disagreement about the form of `refuted` (`¬ LogRankConjecture`).
- The three special cases (EQ₄, ip2, and the rank-1 family) were chosen by the problem authors and are outside the retranslation scope; their values are cross-checked against the independent Python implementation in `small-examples.md`.
