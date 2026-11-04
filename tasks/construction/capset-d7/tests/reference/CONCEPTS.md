# Concept crosswalk: capset-d7-lean (Lean identifiers ↔ literature definitions)

This document maps from each concept in this task's definition layer to the corresponding literature definition, for authors to check fidelity.

## Point space

- Lean: `Fin 7 → ZMod 3` (7 coordinates, each in `ZMod 3`; mathlib's `ZMod 3` is the field Z/3Z)
- Literature: the point set of affine geometry AG(7, 3), namely the 7-dimensional vector space F₃⁷ over the three-element field, with 3⁷ = 2187 points (the “n-attribute SET game” in OEIS A090245 is this object)

## IsCap (`environment/app/Task/Basic.lean`)

- Lean: `∀ x ∈ S, ∀ y ∈ S, x ≠ y → - (x + y) ∉ S`
- Literature: a cap set (cap) is a subset of F₃ⁿ containing no three distinct collinear points (Ellenberg–Gijswijt 2017; Tao 2009 gives the equivalent phrase “no three points on a line” in the note for OEIS A090245)
- Equivalence in each coordinate over F₃:
  1. The line through distinct points x and y is exactly `{x, y, −(x+y)}`: its third point is the midpoint of x and y, since `(x+y)/2 = −(x+y)` (`2 = −1` and `2⁻¹ = 2` in F₃).
  2. `−(x+y) = x` iff `y = x` (adding x+y to both sides gives `−(x+y)=x ⟺ 2x+y=0 ⟺ y=−2x=x`). Thus, when x ≠ y, the third point differs from both.
  3. Therefore, “the midpoint of every pair of distinct points lies outside the set” iff “the set contains no three distinct collinear points,” which is the standard cap-set definition.
- The set condition is equivalent to requiring that −x−y lies outside the set for every distinct pair x,y in the set.

## Statement templates

- Construction direction: `∃ S : Finset (Fin 7 → ZMod 3), IsCap S ∧ S.card ≥ k` — there is a cap of size at least k, giving the lower bound a(7) ≥ k.
- Upper-bound direction: `¬ ∃ S : Finset (Fin 7 → ZMod 3), IsCap S ∧ S.card ≥ k` — there is no cap of size at least k, giving the upper bound a(7) < k.
- Milestone anchors: construction of 128 (`{0,1}⁷` cube, trivial baseline) → 236 (public record, commonly attributed to Edel 2004) → ≥237 marked `record_broken`; upper bound 2188 (trivial bound from the 2187-point full space) → 289 (Thackeray 2022, arXiv:2206.09804) → ≤288 marked `record_broken`.

## Sanity construction

- `cube = Finset.univ.image (fun v : Fin 7 → Fin 2 => fun i => ((v i).val : ZMod 3))`, namely `{0,1}⁷`.
- It is a cap: for distinct x,y ∈ `{0,1}⁷`, some coordinate differs; in that coordinate xᵢ+yᵢ = 1, so the midpoint coordinate −1 = 2 is outside `{0,1}`. Its size is 2⁷ = 128.
- Lean proof route: `native_decide` (finite decidability; `Lean.ofReduceBool` is on the allowlist).

## Open checks

- None. The semantics of both directions in the definition layer were checked against the Solver checker and the equivalence above. The original source for the value 236 (Edel 2004) was not checked directly; the Solver version's wording “usually attributed to” is retained.
