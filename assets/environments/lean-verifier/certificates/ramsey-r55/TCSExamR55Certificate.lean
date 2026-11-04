import Mathlib

/- SAT certificate reconstruction. Every generated theorem includes a proof
   checked by the Lean kernel. Compiled before submitted declarations. -/
namespace TCSExamR55Certificate

section
set_option maxRecDepth 100000
set_option maxHeartbeats 0
open Lean Meta Std
namespace FastCert
open Mathlib.Tactic.Sat

meta def fastStep (db : HashMap Nat Clause) (ns pf : Array Int)
    (ctx clause : Expr) : Except String Expr := Id.run do
  let mut f :=
    mkLambda `v default (mkConst ``Sat.Valuation) ∘
    mkLambda `hv default (mkApp2 (mkConst ``Sat.Valuation.satisfies_fmla) (mkBVar 0) ctx)
  let v depth := mkBVar (depth + 1)
  let hv depth := mkBVar depth
  let mut lams := #[]
  let mut clause := clause
  let mut depth := 0
  let mut lctx : HashMap Int Nat := {}
  for i in ns do
    let l := clause.appFn!.appArg!
    clause := clause.appArg!
    lams := lams.push (mkApp2 (mkConst ``Sat.Valuation.neg) (v depth) l)
    depth := depth.succ
    lctx := lctx.insert i depth
  f := f ∘ lams.foldr (mkLambda `h default)
  for step in pf do
    if step < 0 then return .error "RAT unsupported"
    let some cl := db[step.toNat]? | return .error "missing clause"
    let mut unit := none
    for i in cl.lits do
      unless lctx.contains i do
        if unit.isSome then return .error "not unit"
        depth := depth.succ
        unit := some i
    let mut pr := mkApp2 cl.proof (v depth) (hv depth)
    for i in cl.lits do
      pr := mkApp pr <| mkBVar (match lctx[i]? with | some k => depth-k | _ => 0)
    let some u := unit | return .ok <| f pr
    let lit := toExpr <| Sat.Literal.ofInt u
    let nlit := toExpr <| Sat.Literal.ofInt (-u)
    let d1 := depth-1
    let app := mkApp3 (mkConst ``Sat.Valuation.by_cases) (v d1) nlit <|
      mkLambda `h default (mkApp2 (mkConst ``Sat.Valuation.neg) (v d1) lit) pr
    let dom := mkApp2 (mkConst ``Sat.Valuation.neg) (v d1) nlit
    f := fun e => f <| mkApp app <| mkLambda `h default dom e
    lctx := lctx.insert (-u) depth
  return .error "no contradiction"

meta def reconstruct (cnf lrat : String) (name : Name) : MetaM Unit := do
  let .success _ (_, arr) := Parser.parseDimacs ⟨_, cnf.startPos⟩
    | throwError "cannot parse CNF"
  let .success _ steps := Parser.parseLRAT ⟨_, lrat.startPos⟩
    | throwError "cannot parse LRAT"
  if arr.isEmpty then throwError "empty input"
  let ctx' := buildConj arr 0 arr.size
  let ctxName := name ++ `formula
  addDecl <| .defnDecl {
    name := ctxName, levelParams := [], type := mkConst ``Sat.Fmla,
    value := ctx', hints := .regular 0, safety := .safe }
  let ctx := mkConst ctxName
  let p := mkApp (mkConst ``Sat.Fmla.subsumes_self) ctx
  let mut db := (buildClauses arr ctx 0 arr.size ctx' p default).2
  for (i, cl) in db.toArray do
    let lemmaName := name ++ Name.mkSimple s!"input{i}"
    addDecl <| .thmDecl {
      name := lemmaName, levelParams := [],
      type := mkApp2 (mkConst ``Sat.Fmla.proof) ctx cl.expr, value := cl.proof }
    db := db.insert i {cl with proof := mkConst lemmaName}
  let mut count := 0
  for step in steps do
    match step with
    | .del ids => db := ids.foldl (·.erase ·) db
    | .add i ns pf =>
      let e := buildClause ns
      let .ok proof := fastStep db ns pf ctx e
        | throwError "invalid LRAT proof step {i}"
      let lemmaName := if ns.isEmpty then name else name ++ Name.mkSimple s!"step{i}"
      addDecl <| .thmDecl {
        name := lemmaName, levelParams := [],
        type := mkApp2 (mkConst ``Sat.Fmla.proof) ctx e, value := proof }
      if ns.isEmpty then return
      db := db.insert i {lits := ns, expr := e, proof := mkConst lemmaName}
      count := count + 1
  throwError "missing empty clause"

open Lean.Elab
elab "r55_embedded " n:ident ppSpace "[" cnf:str,* "]" ppSpace "[" lrat:str,* "]" : command => do
  let name := (← getCurrNamespace) ++ n.getId
  Command.liftTermElabM do
    let cnf := String.intercalate "" (cnf.getElems.toList.map (·.getString))
    let lrat := String.intercalate "" (lrat.getElems.toList.map (·.getString))
    reconstruct cnf lrat name
end FastCert

end

end TCSExamR55Certificate
