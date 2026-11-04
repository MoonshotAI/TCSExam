# Public Practice Instance Table (12 Instances)

The 12 public practice instances below are stored in `/app/instances/`. The table lists each instance’s course, room, day and period, curriculum, and unavailability counts. `B` is the shipped baseline penalty; the vendored CPSolver uses a fixed seed and iteration budget, so this value is deterministic. `K` is the best-known penalty. Each OptHub witness schedule passed the official validator, and `proven` indicates that the optimum has been proved in the literature. `gap = B − K` is the baseline’s excess penalty over `K`. The judged set also includes hidden instances, which are not listed here.

| instance | courses | rooms | days x periods | curricula | unavail. | B | K | gap | proven |
|---|---|---|---|---|---|---|---|---|---|
| comp01 | 30 | 6 | 5 x 6 | 14 | 53 | 5 | 5 | 0 | yes |
| comp03 | 72 | 16 | 5 x 5 | 68 | 382 | 84 | 64 | 20 | no |
| comp08 | 86 | 18 | 5 x 5 | 61 | 478 | 47 | 37 | 10 | yes |
| comp10 | 115 | 18 | 5 x 5 | 67 | 694 | 29 | 4 | 25 | yes |
| comp12 | 88 | 11 | 6 x 6 | 150 | 1368 | 363 | 289 | 74 | no |
| comp13 | 82 | 19 | 5 x 5 | 66 | 468 | 81 | 59 | 22 | yes |
| comp14 | 85 | 17 | 5 x 5 | 60 | 486 | 67 | 51 | 16 | yes |
| comp16 | 108 | 20 | 5 x 5 | 71 | 518 | 44 | 18 | 26 | yes |
| comp17 | 99 | 17 | 5 x 5 | 70 | 548 | 88 | 56 | 32 | yes |
| comp18 | 47 | 9 | 6 x 6 | 52 | 594 | 98 | 61 | 37 | yes |
| comp19 | 74 | 16 | 5 x 5 | 66 | 475 | 72 | 57 | 15 | yes |
| comp20 | 121 | 19 | 5 x 5 | 78 | 691 | 26 | 4 | 22 | yes |

`/app/solutions/` contains best-known schedules for four of these instances (comp03/08/10/16); all passed the official validator, are feasible, and have a cost equal to K.
