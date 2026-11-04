# Public instances — per-instance table (maxsat-mse)

This table is generated from the task data (do not edit by hand). One row per shipped public instance. `B` is the shipped baseline's cost under its default soft limit; `K` is the best known cost from the MSE 2026 registry (a trailing `*` marks a proven optimum); `B - K` is the gap the baseline leaves. All 11 shipped instances are in the practice set (run by `/app/run_public.py`), marked `yes` in the last column.

| instance | family | vars | hard | soft | B (baseline) | K (registry) | B − K | practice |
|---|---|---|---|---|---|---|---|---|
| argumentation-framework-synthesis--1645126bc049f932.wcnf | argumentation-framework-synthesis | 14604 | 152866 | 110 | 121 | 115 * | 6 | yes |
| decision-trees--d8f5cdbc2e7d1259.wcnf | decision-trees | 18651 | 124971 | 236 | 433 | 139 | 294 | yes |
| inductive-logic-programming-minimum-description-length--a04c49fdcfb80a2b.wcnf | inductive-logic-programming-minimum-description-length | 7968 | 903815 | 7968 | 923 | 667 | 256 | yes |
| interpretable-rule-based-classifiers--d65e49e03a1bef21.wcnf | interpretable-rule-based-classifiers | 16924 | 923731 | 7369 | 181 | 74 | 107 | yes |
| logistics-routing--b1f3bc82f34d8304.wcnf | logistics-routing | 66705 | 133923 | 2350 | 1064 | 584 | 480 | yes |
| max-realizability-robot-navigation--1d69eb0fbbde8c41.wcnf | max-realizability-robot-navigation | 171619 | 713203 | 9 | 39 | 14 | 25 | yes |
| maximum-colorful-subtree--aba43574fdcf5980.wcnf | maximum-colorful-subtree | 254432 | 355290 | 50486 | 839 | 827 * | 12 | yes |
| pareto-optimal-interpretation-synthesis--3332f249f67f78ea.wcnf | pareto-optimal-interpretation-synthesis | 7923 | 22995 | 46 | 336 | 336 * | 0 | yes |
| planning-hplus--ff3edb803a43f49e.wcnf | planning-hplus | 165032 | 1814430 | 42883 | 1812 | 559 | 1253 | yes |
| railway-timetabling--91d8278936cbdcdd.wcnf | railway-timetabling | 10736 | 93375 | 10736 | 54429 | 43213 * | 11216 | yes |
| single-cell-dna-sequencing--ae8b9d05d7e77b28.wcnf | single-cell-dna-sequencing | 32204 | 1504658 | 9481 | 1456983878832568 | 271716016106946 * | 1185267862725622 | yes |
