import Lean
import Lean.Meta.Native

/- Trusted grading commands. This module is compiled before submitted sources. -/
namespace TCSExamVerifierAudit

private def audit (name : String) (allowNative : Bool) : Lean.Elab.Term.TermElabM Unit := do
  let target := name.toName
  let axioms ← Lean.collectAxioms target
  let mut verified : List String := []
  if allowNative then
    for ax in axioms do
      if ax.toString.contains "._native.native_decide.ax_" then
        let ci ← Lean.getConstInfo ax
        let type := ci.type
        unless type.isAppOfArity ``Eq 3 && type.getArg! 0 == Lean.mkConst ``Bool &&
            type.getArg! 2 == Lean.mkConst ``Bool.true do
          throwError "Invalid native proof axiom type"
        match ← Lean.Meta.nativeEqTrue `tcsexam_verify (type.getArg! 1) with
        | .notTrue => throwError "Native proof axiom evaluated to false"
        | .success _ => verified := ax.toString :: verified
  let report := Lean.Json.mkObj [
    ("declaration", Lean.toJson target.toString),
    ("axioms", Lean.toJson (axioms.toList.map Lean.Name.toString)),
    ("native_verified", Lean.toJson verified)]
  Lean.logInfo ("TCSEXAM_AXIOM_REPORT " ++ report.compress)
  if axioms.isEmpty then
    Lean.logInfo ("'" ++ target.toString ++ "' does not depend on any axioms")
  else
    Lean.logInfo ("'" ++ target.toString ++ "' depends on axioms: [" ++
      String.intercalate ", " (axioms.toList.map Lean.Name.toString) ++ "]")

elab "#tcsexam_audit " name:str : command =>
  Lean.Elab.Command.liftTermElabM (audit name.getString false)

elab "#tcsexam_audit_native " name:str : command =>
  Lean.Elab.Command.liftTermElabM (audit name.getString true)

end TCSExamVerifierAudit
