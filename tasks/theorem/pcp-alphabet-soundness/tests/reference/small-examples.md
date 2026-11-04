# Executable small examples — MZ24 inner PCP composition core

This record documents the third of three fidelity checks: running of running or proving the shipped definitions on small instances; companion code is `Examples.lean` (in the same directory; executed at step 3 of the verify pipeline; the remote build log reports success).
- Setup: field `ZMod 2` (denoted F₂ below), ambient dimension 2 and 3. The shipped `grass`/`zoom`/`zoomProb` definitions use classical Fintype instances and are noncomputable, so the small examples use two tracks: **shadow computation** (a computable shadow model represented by finite sets of vectors, run with `native_decide`) and **official checks** (proofs written directly against the shipped definitions)

## I. Shadow computation (`native_decide`; all pass)

The shadow model represents subspaces as finite sets of vectors (closure over F₂ is decidable) and checks, item by item, the combinatorial counts implied by the shipped definitions. Run record: step 3 of the verify pipeline (`lake env lean /verify/Examples.lean`; the remote builder log says `VERIFY examples: ok`).

| ID | Claim | Result |
|---|---|---|
| A1 | Number of 1-dimensional subspaces of F₂³ = 7; number of 2-dimensional subspaces = 7 (Gaussian binomial coefficients [3 choose 1]₂ = [3 choose 2]₂ = 7) | Cardinalities of `shadowGrass 3 1/3 2` both compute to 7 ✓ |
| A2 | Number of 1-dimensional subspaces of F₂² = 3 (same value as official check E6) | Computes to 3 ✓ |
| A3 | `zoom` counts: Zoom₁[⊥,⊤] (F₂³) = 7; Zoom₂[⊥,⊤] = 7; in a 2-dimensional W, Zoom₁[⊥,W] = 3 and Zoom₂[⊥,W] = 1 | All match ✓ |
| A4 | Number of linear functions = q^ℓ (alphabet of subspace encodings): 2 for a line, 4 for a plane, 8 for the full space F₂³ | All match ✓ |
| A5 | Set of random pairs in the inclusion test, (ℓ₁,ℓ₂) = (2,1) in F₂³: 7 planes × 3 lines per plane = 21 pairs | Computes to 21 ✓ |
| A6 | **Core count for claim c2**: for each test pair (L₁,L₂), exactly 4 shadow linear-map pairs (g₁,g₂) are accepted, where g₁\|_{L₂} = g₂; this is half of the 8 total pairs (q^{−ℓ₂} = 1/2). It holds for all 21 pairs | Computes to 4 = 8/2 for each pair ✓ |
| A7 | Honest-table behavior in the shadow model: the two restriction tables of a global linear function f agree on all 21 pairs (the computational form of completeness) | All accepted ✓ |

A6 is the small-instance check for test point c2 (the random-table barrier): the key step in the proof of c2 is that the acceptance fraction at every (L₁,L₂) is exactly 1/q^{ℓ₂} (the restriction map Hom(L₁,F) → Hom(L₂,F) is surjective with uniform fibers, each of size q^{ℓ₁−ℓ₂} = 2). Exhaustive enumeration confirms the value here.

## II. Official checks (proofs against shipped definitions; all pass)

| ID | Claim | Form |
|---|---|---|
| E1 | ⊤ ∈ `grass F2 2 2` (the full space is a 2-dimensional member) | Proof (`finrank_top` + `finrank_fintype_fun_eq_card`) |
| E2 | ⊥ ∈ `grass F2 2 0` and ⊥ ∉ `grass F2 2 1` | Proof (`finrank_bot`) |
| E3 | ⊤ ∈ `zoom F2 2 2 ⊥ ⊤` | Proof |
| E4 | Shipped agreement predicate holds for an honest table: `agreeOnZoom (globalTab f) (f.comp W.subtype) L` (`L ≤ W`) | Proof (definition-level `rfl`) |
| E5 | Shipped acceptance condition for the inclusion test holds for honest tables: `incAccepts (globalTab f) (globalTab f) p` | Proof (definition-level `rfl`) |
| E6 | **Official-to-shadow bridge**: `(grass F2 2 1).card = 3`—the shipped Grassmann domain has exactly 3 members at (n,ℓ) = (2,1), q = 2, matching the shadow value A2 | Proof (exhaustively span the three nonzero vectors + every 1-dimensional subspace is spanned by its nonzero vector + the three spans are pairwise distinct) |

E6 is a focused check of the definition layer: if `grass` were mistakenly defined using codimension ℓ, or if the carrier convention were misaligned, this cardinality proof would fail.

## III. Relation to the scoring path

Small examples illustrate finite cases and do not contribute to the task score.
