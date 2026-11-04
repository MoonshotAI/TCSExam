# Public Practice Instance Table (13 Instances)

How to read this table: each row is a public practice instance (the file is in `/app/instances/`). `variables` is the number of links, `hard/soft` are the counts of hard equality/soft separation constraints, `costs` lists the four violation costs, `B` is the objective value of the shipped pipeline (deterministic and fixed), and `K` is the best known value. The judged set also contains hidden instances, which are not listed here.

| Instance | variables | hard | soft | costs | B (baseline) | K (best known) |
|---|---|---|---|---|---|---|
| graph01.dzn | 200 | 0 | 0 | [1000,100,10,1] | 0 | 0 |
| graph02.dzn | 400 | 0 | 0 | [1000,100,10,1] | 0 | 0 |
| graph04.dzn | 400 | 0 | 0 | [1000,100,10,1] | 0 | 0 |
| graph06.dzn | 400 | 200 | 1970 | [1000,100,10,1] | 192386 | 4123 (measured in this project; CP-SAT proved optimality) |
| graph09.dzn | 916 | 0 | 0 | [1000,100,10,1] | 0 | 0 |
| graph11.dzn | 680 | 340 | 3417 | [1000,100,10,1] | 341282 | 3080 (literature value, ZIB CALMA table) |
| graph12.dzn | 680 | 340 | 3677 | [1000,100,10,1] | 366061 | 9609 (new project-measured record; CP-SAT proved optimality) |
| graph14.dzn | 916 | 0 | 0 | [1000,100,10,1] | 0 | 0 |
| scen01.dzn | 916 | 0 | 0 | [1000,100,10,1] | 0 | 0 |
| scen02.dzn | 200 | 0 | 0 | [1000,100,10,1] | 0 | 0 |
| scen07.dzn | 400 | 200 | 2665 | [1000000,10000,100,1] | 201424125 | 343592 (literature value; witness verified in this project's validation run) |
| scen09.dzn | 680 | 340 | 3763 | [1000,100,10,1] | 384594 | 4130 (new project-measured record, not proved optimal) |
| scen11.dzn | 680 | 340 | 0 | [1000,100,10,1] | 0 | 0 |

- Instances with B=K=0 (scen01/02/11, graph01/02/04/09/14) are of type Minimum Order / Minimum Span in the official feature table. They have no soft constraints, or their weighted soft objective is always 0. The shipped constructor was measured to produce a legal solution with objective 0 for each (witnesses are archived).
- “Measured in this project” means recomputed with CP-SAT using 8 workers and 1700 s per instance on isolated execution environment. “Literature value” means the ZIB CALMA results table. No local witness is available for graph11=3080; it is recorded as such under the 2026-09-10 rule.
