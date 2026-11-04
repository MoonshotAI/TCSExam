/- Regression checks for the arc coverage and event classification of Dijkstra traces.
   For task authors; compile with `lake env lean /path/to/TraceSemantics.lean`. -/
import Task.Basic

open DijkstraUniversal DijkstraUniversal.Digraph

namespace DijkstraTraceRegression

/-- A complete three-vertex graph, including backward arcs. -/
abbrev graph : Digraph where
  n := 3
  arcs := {(0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1)}
  loopless := by decide
  src := 0
  reach := by
    intro v
    fin_cases v
    · exact ⟨[0], by decide, .singleton _, rfl, rfl⟩
    · exact ⟨[0, 1], by decide, .cons (by decide) (.singleton _), rfl, rfl⟩
    · exact ⟨[0, 2], by decide, .cons (by decide) (.singleton _), rfl, rfl⟩

def zeroWeight : graph.ArcLen := fun _ _ => 0

theorem zero_path (p : List (Fin graph.n)) : pathLen zeroWeight p = 0 := by
  induction p with
  | nil => rfl
  | cons a t ih =>
    cases t with
    | nil => rfl
    | cons b t => simpa [pathLen, zeroWeight] using ih

theorem zero_distance (v : Fin graph.n) : graph.trueDist zeroWeight v = 0 := by
  obtain ⟨p, _, hp⟩ := graph.exists_path_trueDist zeroWeight v
  rw [← hp, zero_path]

/-- The comparison at arc 1→2 fails (all distances are zero), but is recorded.
    Arcs 1→0, 2→0 and 2→1 are skipped after their heads have been scanned. -/
def completeBlocks : List (Fin graph.n × List (BlockEv graph.n)) :=
  [(0, [.ins 1, .ins 2]), (1, [.skip 0, .relax 2]), (2, [.skip 0, .skip 1])]

def completeTrace : DijkstraTrace graph zeroWeight where
  blocks := completeBlocks
  scan_nodup := by decide
  scan_len := by decide
  src_first := by decide
  arc_ok := by
    intro u evs hb e he
    simp only [completeBlocks, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hb
    rcases hb with ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ <;>
      simp only [List.mem_cons, List.not_mem_nil, or_false] at he <;>
      rcases he with rfl | rfl <;> decide
  block_nodup := by
    intro u evs hb
    simp only [completeBlocks, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hb
    rcases hb with ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ <;> decide
  arc_covered := by
    intro u evs hb v hv
    simp only [completeBlocks, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hb
    rcases hb with ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ <;>
      fin_cases v <;> simp_all [graph, BlockEv.v]
  ins_count := by decide
  ins_block_lt := by
    intro v u evs he hb
    simp only [completeBlocks, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hb
    rcases hb with ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ <;>
      fin_cases v <;> simp_all [completeBlocks]
  relax_valid := by
    intro u evs v he hb
    simp only [completeBlocks, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hb
    rcases hb with ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ <;>
      fin_cases v <;> simp_all [completeBlocks]
    exact ⟨0, [.ins 1, .ins 2], by simp, by simp, by decide⟩
  skip_valid := by
    intro u evs v he hb
    simp only [completeBlocks, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hb
    rcases hb with ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ <;>
      fin_cases v <;> simp_all [completeBlocks]
  scan_dist_order := by
    constructor
    · intro u v _
      rw [zero_distance, zero_distance]
    · decide

/-- Failed comparisons count; skipped arcs do not count as insertions. -/
example : completeTrace.relaxCount = 1 := by decide
example : completeTrace.insEvents = [.ins 1, .ins 2] := by decide
example : completeTrace.W 0 = 1 ∧ completeTrace.W 1 = 2 ∧ completeTrace.W 2 = 1 := by decide
example : completeTrace.compCost =
    (1 : ℝ) + ∑ v : Fin graph.n, (1 + Real.logb 2 (completeTrace.W v)) := by
  unfold DijkstraTrace.compCost
  rw [show completeTrace.relaxCount = 1 by decide]
  norm_num

/-- An insertion-only log omits backward arcs and the comparison 1→2. -/
def omittedBlocks : List (Fin graph.n × List (BlockEv graph.n)) :=
  [(0, [.ins 1, .ins 2]), (1, []), (2, [])]

/-- Insertion, scan and event-membership constraints alone permit that omission. -/
example :
    (omittedBlocks.map Prod.fst).Nodup ∧
    (omittedBlocks.map Prod.fst).length = graph.n ∧
    (omittedBlocks.map Prod.fst).head? = some graph.src ∧
    (∀ u evs, (u, evs) ∈ omittedBlocks → ∀ e ∈ evs, (u, e.v) ∈ graph.arcs) ∧
    (∀ u evs, (u, evs) ∈ omittedBlocks → (evs.map BlockEv.v).Nodup) ∧
    (∀ v : Fin graph.n,
      ((omittedBlocks.flatMap Prod.snd).filter (· == BlockEv.ins v)).length =
        if v = graph.src then 0 else 1) ∧
    (∀ v u evs, BlockEv.ins v ∈ evs → (u, evs) ∈ omittedBlocks →
      (omittedBlocks.map Prod.fst).idxOf u < (omittedBlocks.map Prod.fst).idxOf v) ∧
    (∀ u evs v, BlockEv.relax v ∈ evs → (u, evs) ∈ omittedBlocks →
      (∃ u' evs', BlockEv.ins v ∈ evs' ∧ (u', evs') ∈ omittedBlocks ∧
        (omittedBlocks.map Prod.fst).idxOf u' < (omittedBlocks.map Prod.fst).idxOf u) ∧
      (omittedBlocks.map Prod.fst).idxOf u < (omittedBlocks.map Prod.fst).idxOf v) ∧
    graph.IsTrueDistOrder zeroWeight
      (permOfList (omittedBlocks.map Prod.fst) (by decide) (by decide)) := by
  refine ⟨by decide, by decide, by decide, ?_, ?_, by decide, ?_, ?_, ?_⟩
  · intro u evs hb e he
    simp only [omittedBlocks, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hb
    rcases hb with ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩
    · simp only [List.mem_cons, List.not_mem_nil, or_false] at he
      rcases he with rfl | rfl <;> decide
    · simp at he
    · simp at he
  · intro u evs hb
    simp only [omittedBlocks, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hb
    rcases hb with ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ <;> decide
  · intro v u evs he hb
    simp only [omittedBlocks, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hb
    rcases hb with ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ <;>
      fin_cases v <;> simp_all [omittedBlocks]
  · intro u evs v he hb
    simp only [omittedBlocks, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hb
    rcases hb with ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ <;> simp_all
  · constructor
    · intro u v _
      rw [zero_distance, zero_distance]
    · decide

/-- The trace type cannot contain a log that omits the comparison arc. -/
example (tr : DijkstraTrace graph zeroWeight) : tr.blocks ≠ omittedBlocks := by
  intro h
  have covered := tr.arc_covered 1 [] (by rw [h]; simp [omittedBlocks]) 2 (by decide)
  simp at covered

/-- Omitting only the failed comparison is rejected even with all skips present. -/
example (tr : DijkstraTrace graph zeroWeight) : tr.blocks ≠
    [(0, [.ins 1, .ins 2]), (1, [.skip 0]), (2, [.skip 0, .skip 1])] := by
  intro h
  have covered := tr.arc_covered 1 [.skip 0] (by rw [h]; simp) 2 (by decide)
  simp [BlockEv.v] at covered

/-- Backward arcs must be covered even though they have no comparison cost. -/
example (tr : DijkstraTrace graph zeroWeight) : tr.blocks ≠
    [(0, [.ins 1, .ins 2]), (1, [.relax 2]), (2, [.skip 0, .skip 1])] := by
  intro h
  have covered := tr.arc_covered 1 [.relax 2] (by rw [h]; simp) 0 (by decide)
  simp [BlockEv.v] at covered

/-- A comparison cannot be hidden by marking a forward arc as skipped. -/
example (tr : DijkstraTrace graph zeroWeight) : tr.blocks ≠
    [(0, [.ins 1, .ins 2]), (1, [.skip 0, .skip 2]), (2, [.skip 0, .skip 1])] := by
  intro h
  have invalid := tr.skip_valid 1 [.skip 0, .skip 2] 2 (by simp) (by rw [h]; simp)
  rw [h] at invalid
  have impossible : ¬ (List.idxOf (2 : Fin 3) [0, 1, 2] < List.idxOf (1 : Fin 3) [0, 1, 2]) := by decide
  exact impossible invalid

#print axioms zero_path
#print axioms zero_distance
#print axioms completeTrace

end DijkstraTraceRegression
