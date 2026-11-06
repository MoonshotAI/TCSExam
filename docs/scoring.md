Score formulas, input formats and aggregation for TCSExam.
For researchers computing task scores and the combined Index.

# Score calculation

[English](scoring.md) | [简体中文](scoring.zh-CN.md)

TCSExam reports four track scores and their weighted Index. The task checker's
original reward is retained in the evaluation output. The Index uses complete
proof indicators for the two proof tracks, fixed-reference relative scores for
Solver, and original rewards for constructions.

## The four track scores

Read each row for the value to put in the attempt table.

| Track | Value used by the Index | Range |
|---|---|---|
| Theorem proving | Complete proof accepted by the checker: 1; otherwise 0 | 0–1 |
| Solver engineering | Instance outcomes compared with the fixed references supplied in the [Full](../src/tcsexam/references/paper-k3-fixed-260925-full.json) and [Lite](../src/tcsexam/references/paper-k3-fixed-260925-lite.json) JSON files | 0–1 |
| Constructions | Original task reward, including above-reference credit | Nonnegative; may exceed 1 |
| Open conjectures | Complete proof or refutation accepted: 1; otherwise 0 | 0–1 |

The fixed reference contains the frozen K3 instance outcomes used to define
Solver's relative score. Its version and values stay fixed when evaluating
additional models. Full uses reference ID
`paper-k3-fixed-260925-public-disjoint-261105`; Lite uses
`paper-k3-fixed-260925`. The five Lite tasks have exactly the same reference
values in both files.

Full uses [final selection `public-disjoint-final-261105`](../assets/data/solver/final-evaluation-selection.json).
MaxSAT has 200 final instances, of which 177 enter the relative score;
Radiation has 36 final instances, all of which enter the relative score.
These final sets exclude instances shared with their public development sets.
The retained instance names, reference values and scoring formula stay fixed.
Keep the selection ID and the `reference_id` returned by `solver-score` with
reported results. Historical platform rewards remain associated with their
original instance sets; recomputed results identify the selected set.

The original checker output can contain partial theorem credit or intermediate
open-conjecture results. Convert these to 0 unless the checker accepted a
complete proof or resolution. Construction formulas remain unchanged.

The Index is `30P + 30S + 30C + 10O`, where the letters are the theorem, Solver,
construction and open-conjecture track means. Its metric identifier is
`tcsexam-index-original-30303010-v0.1`. Report Index points together with all
four track means. Because construction rewards can exceed 1, the Index can
exceed 100.

## Average in this order

1. Average the adopted repetitions of each task.
2. Average task means equally within each track.
3. Multiply track means by 30, 30, 30 and 10 and add them.

A task repeated three times receives the same track weight as a task repeated
once. Missing tasks or planned repetitions produce an incomplete result with a
null Index. Track weights stay fixed. An otherwise complete result containing
provisional attempts is labelled provisional. Report Full and Lite separately,
and separate online and offline Solver protocols within each suite.

## Fixed-reference Solver calculation

For each reference instance, let `mu` be the mean of its fixed reference values
and `s` their sample standard deviation. Set
`scale = max(s, 0.02 * abs(mu), 1e-9)`. For a valid candidate value `A`:

- maximization: `z = (A - mu) / scale`;
- minimization: `z = (mu - A) / scale`;
- instance score: `Phi(z)`, the standard normal cumulative distribution function.

Average the eligible instance scores to obtain the task score. A valid value
equal to `mu` receives 0.5. A solver-level invalid submission, timeout or crash
receives 0 for that instance. Missing results and infrastructure failures require
repairing the judging input before scoring; they are incomplete observations.

The Full reference includes 1,838 eligible instances; 32 additional instances
had fewer than two usable reference outcomes and are listed in
`unscored_reference_instances`. Keep their observed outcomes in the result
records. The scorer reports records outside the eligible set as
`unscored_instances` and leaves them out of the mean. This fixed-reference
metric is separate from baseline and known-best-value denominators in original
checker rewards.

Each reference task declares `kind: "objective"` for objective values or
`kind: "solve"` for solved indicators, plus its direction and reference values.
For `solve`, the same formula uses 1 for solved and 0 for unsolved. Every
reference instance needs at least two usable values. Custom references must
supply these fields and both scale floors; version a changed reference
separately.

## From instance records to a task score

Save the final judge's instance outcomes as a JSON list. Objective records use
`instance`, `status` and `A`; solve-rate records can use a Boolean `solved`
instead of `A`. Use `status: "ok"` only for a valid evaluated outcome. A completed
solver failure uses the corresponding failure status, such as `timeout`,
`invalid` or `certificate_failed`.

For example, a two-instance maximization calculation could have these records:

```json
[
  {"instance": "example-1", "status": "ok", "A": 12},
  {"instance": "example-2", "status": "timeout"}
]
```

If the first instance's reference values are `[10, 12, 14]`, its `mu` is 12,
`scale` is 2 and score is 0.5. The timeout scores 0, giving a task mean of 0.25.
These names and numbers illustrate the formula. For an evaluation, use the
actual task's complete final records and the selected fixed reference:

```bash
tcsexam solver-score --task maxcut-mqlib \
  --records my-final-instance-records.json --reference lite \
  --output build/maxcut-relative.json
```

The output contains `relative_score`, per-instance scores, unscored instance
names and `reference_id`. Put `relative_score` into the attempt table; retain
the raw checker reward and records alongside it. A missing eligible instance,
duplicate name or infrastructure status causes an error.

## Attempt table

Use one CSV row per attempt with these columns:

```csv
model,track,item,attempt,score,adoption_status,score_status,score_type,solver_protocol
my-model,solver,maxcut-mqlib,1,0.25,selected,valid,fixed_reference_relative,offline
```

The score above illustrates the row format. Populate it with the actual
`relative_score` produced for that task and attempt. Add the remaining selected
tasks and planned repetitions before computing an Index.

Read the table by field. A legitimate zero is a valid observed score.

| Field | Values and meaning |
|---|---|
| `adoption_status` | `selected` adopts an attempt; `selected_provisional` adopts it provisionally; `excluded` retains an attempt outside the aggregate. |
| `score_status` | `valid` includes legitimate zeros. States such as `judge_failed`, `not_finished` and `missing` leave the planned result incomplete. |
| `score_type` | Solver requires `fixed_reference_relative`. Other tracks can use `original_task_score`, with theorem and open-conjecture scores already converted to 0 or 1. |
| `solver_protocol` | Solver rows declare `online` or `offline`; other tracks may leave this empty. |
| `attempt` | An identifier unique within each model, track and task. |

Declare the planned repetitions and adoption policy before aggregation. If an
attempt is replaced, retain its row as `excluded` and record why the replacement
was adopted. The aggregator rejects duplicate identities and excess adopted
repetitions.

## Recalculate an Index

Create `cohort.json` to declare the suite, Solver protocol, fixed reference and
number of adopted repetitions planned for every task:

```json
{
  "suite": "lite",
  "solver_protocol": "offline",
  "solver_reference_id": "paper-k3-fixed-260925",
  "models": {"my-model": {"attempts_per_task": 1}}
}
```

Prepare `attempts.csv` with all twenty Lite tasks, then run:

```bash
tcsexam score --suite lite --attempts attempts.csv --cohort cohort.json \
  --output build/index.json
```

All selected Solver rows must match the cohort protocol and use the declared
reference. Preserve the `solver-score` outputs to show which reference produced
them. Aggregation consumes the task scores and labels in the attempt table;
retain the instance records alongside those scores.

For example, if the resulting track means are `P=0.4`, `S=0.25`, `C=1.2` and
`O=0`, the Index is `30×0.4 + 30×0.25 + 30×1.2 + 10×0 = 55.5` points. If one
planned task result is missing, the output instead has `status: "incomplete"`
and `index: null`, with coverage and issues identifying the missing result.
