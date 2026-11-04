# JSPLib reference data

Snapshot of the public JSPLib archive — the `jobshop/solutions/`
directory of https://github.com/ScheduleOpt/benchmarks (main branch,
cloned 2026-08-09), redistributed under CC-BY-SA-4.0 (see the repository
root LICENSE upstream). This is the record the task's `K` anchors for the
classic instances come from.

- `bks.json` — the best-known-solutions archive: one entry per instance
  (376 in total: the 332 classic instances including the generated `tai`
  family, plus 44 industrial reentrant ones) with `size`, `family`,
  `status` (`toy` / `easy` / `medium` / `hard` / `closed` / `open` —
  `open` means no proof of optimality is known), the archive
  `lower_bound` and `upper_bound`, and the `lb_data` / `ub_data` traces
  recording who reported each bound, when, on what hardware, at what
  running time, and whether a certificate exists.
- `results_cpsat_9_15_6755.json`, `results_cpo_22_1_1_0.json`,
  `results_cplex_22_1_1_0.json`,
  `results_optalcp_2026_4_0_maxpropagation.json` — JSPLib's standardized
  10-minute engine benchmark: for every instance, the lower bound (`lb`,
  dual) and upper bound (`ub`, primal) that engine reported within a
  10-minute run, each with `value`, `date`, `solver`, `hardware`, `time`
  (minutes), and `certificate` fields. The four engines are Google
  CP-SAT 9.15.6755 (the exact version installed in this image), IBM CP
  Optimizer 22.1.1.0, IBM Cplex 22.1.1.0 (a MIP engine), and OptalCP
  2026.4.0.
