# Public instances — baseline (B) vs best known (K)

Scoring contract (260831 rework): a solution's beam-on time must attain
the structural lower bound `LB` (the maximum per-row total positive
gradient of the intensity matrix) to score at all; scoring is then on the
**shape count** alone. `B` is the shipped baseline's shape count — the
deterministic unit-time constructor (`N[1] = LB`, so `B = LB` by
construction) — and `K` is the best known shape count at `Beamtime = LB`
(proven optimal for every instance below: the small ones by a direct
CP-SAT optimality proof on the shipped `radiation_lb.mzn`, the larger
ones inherited from the proven-optimal reference runs, since any
decomposition with fewer shapes at `Beamtime = LB` would have beaten
those proven optima).

| instance | size m×n | max intensity | LB | B (baseline shapes) | K (best shapes) | gap B−K |
|---|---|---|---|---|---|---|
| 01.dzn | 5×5 | 8 | 14 | 14 | 6 | 8 |
| 02.dzn | 5×5 | 8 | 14 | 14 | 5 | 9 |
| 03.dzn | 5×5 | 8 | 15 | 15 | 6 | 9 |
| 04.dzn | 6×6 | 8 | 17 | 17 | 7 | 10 |
| 05.dzn | 6×6 | 8 | 16 | 16 | 6 | 10 |
| 06.dzn | 6×6 | 8 | 17 | 17 | 6 | 11 |
| 07.dzn | 6×6 | 9 | 13 | 13 | 6 | 7 |
| 08.dzn | 6×6 | 9 | 18 | 18 | 7 | 11 |
| 09.dzn | 6×6 | 9 | 18 | 18 | 7 | 11 |
| m06_15_15.dzn | 6×6 | 15 | 19 | 19 | 8 | 11 |
| m07_07_20.dzn | 7×7 | 7 | 17 | 17 | 6 | 11 |
| pub14_12a.dzn | 14×14 | 12 | 53 | 53 | 13 | 40 |
| pub16_12a.dzn | 16×16 | 12 | 46 | 46 | 15 | 31 |
| pub18_15a.dzn | 18×18 | 15 | 67 | 67 | 16 | 51 |
| pub16_14a.dzn | 16×16 | 14 | 54 | 54 | 15 | 39 |

The judging instances are freshly generated at harder sizes
and are not listed here.
