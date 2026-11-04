import Lean

/- Compiled before the submission, so its declarations cannot change this check. -/
namespace GG26ProofShape

private partial def dependencies (root : Lean.Name) (wanted : String)
    (seen : Lean.NameSet := {}) : Lean.MetaM (Lean.NameSet × Array Lean.Name) := do
  if seen.contains root then return (seen, #[])
  let mut seen := seen.insert root
  let leaf := (root.toString.splitOn ".").getLast!
  let mut found := if leaf == wanted then #[root] else #[]
  let info ← Lean.getConstInfo root
  let mut names := info.type.getUsedConstants
  let value := match info with
    | .defnInfo v => some v.value
    | .thmInfo v => some v.value
    | .opaqueInfo v => some v.value
    | _ => none
  if let some value := value then names := names ++ value.getUsedConstants
  let environment ← Lean.getEnv
  for name in names do
    -- Imported libraries cannot contain an agent-written helper.
    if (environment.getModuleIdxFor? name).isNone then
      let (visited, foundNames) ← dependencies name wanted seen
      seen := visited
      found := found ++ foundNames
  return (seen, found)

private def rejects (type : Lean.Expr) : Lean.MetaM Bool :=
  Lean.Meta.forallTelescope type fun parameters conclusion => do
    let mut explicitProp := false
    for parameter in parameters do
      let declaration ← parameter.fvarId!.getDecl
      if declaration.binderInfo == .default then
        if ← Lean.Meta.isProp declaration.type then
          explicitProp := true
    let conclusion ← Lean.Meta.whnf conclusion
    pure (conclusion.isConstOf ``False && !explicitProp)

private def report (name main : String) : Lean.Elab.Term.TermElabM Unit := do
  let (_, declarations) ← dependencies main.toName name
  let mut reject := false
  for declaration in declarations do
    if ← rejects (← Lean.getConstInfo declaration).type then reject := true
  Lean.logInfo ("TCSEXAM_GG26_SHAPE " ++ (Lean.Json.mkObj [
    ("declaration", Lean.toJson name), ("reject", Lean.toJson reject),
    ("resolved", Lean.toJson (declarations.map Lean.Name.toString))]).compress)

elab "#tcsexam_gg26_shape " name:str main:str : command =>
  Lean.Elab.Command.liftTermElabM (report name.getString main.getString)

end GG26ProofShape
