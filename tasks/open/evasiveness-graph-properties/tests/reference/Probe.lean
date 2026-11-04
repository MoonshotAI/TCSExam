/- Executable probes for the evasiveness task package (grader-side material,
never shipped to the agent). Run inside the built app context:

  lake env lean Probe.lean

E1/E2: hasEdgeProp on v=2 (bot/top). E3: same on v=3. E4: singleEdge has
exactly one edge. E5: the checkpoint-2 witness tree (depth 0) evaluates to
true on every input shown. E6: a leaf alone cannot decide hasEdgeProp on v=2
(it disagrees with the property on bot or on top) — the v=2 shadow of
checkpoint c1. E7: the all-no path machinery on an example tree.
-/

import Task.Basic

namespace Evasiveness

set_option maxRecDepth 4096

-- E1
example : hasEdgeProp 2 (⊥ : SimpleGraph (Fin 2)) = false := by decide
-- E2
example : hasEdgeProp 2 (⊤ : SimpleGraph (Fin 2)) = true := by decide
-- E3
example : hasEdgeProp 3 (⊥ : SimpleGraph (Fin 3)) = false := by decide
example : hasEdgeProp 3 (⊤ : SimpleGraph (Fin 3)) = true := by decide
example : (⊤ : SimpleGraph (Fin 3)).edgeFinset.card = 3 := by decide
-- E4
example : (singleEdge (0 : Fin 3) 1 (by decide)).edgeFinset.card = 1 := by decide
-- E5
example : (DTree.leaf true : DTree 3).eval (⊤ : SimpleGraph (Fin 3)) = true := by decide
example : (DTree.leaf true : DTree 3).eval (⊥ : SimpleGraph (Fin 3)) = true := by decide
example : (DTree.leaf true : DTree 3).depth = 0 := rfl
-- E6: a single leaf disagrees with hasEdgeProp on some input (v = 2)
example : (DTree.leaf true : DTree 2).eval (⊥ : SimpleGraph (Fin 2)) = true ∧
    hasEdgeProp 2 (⊥ : SimpleGraph (Fin 2)) = false := by decide
example : (DTree.leaf false : DTree 2).eval (⊤ : SimpleGraph (Fin 2)) = false ∧
    hasEdgeProp 2 (⊤ : SimpleGraph (Fin 2)) = true := by decide
-- E7: all-no path of an example tree (query 01, on "no" query 02)
example : noPathQueries (DTree.query s(0, 1) (DTree.leaf true)
    (DTree.query s(0, 2) (DTree.leaf true) (DTree.leaf false)) : DTree 3)
    = {s(0, 1), s(0, 2)} := by decide
example : noPathValue (DTree.query s(0, 1) (DTree.leaf true)
    (DTree.query s(0, 2) (DTree.leaf true) (DTree.leaf false)) : DTree 3) = false := by decide

end Evasiveness
