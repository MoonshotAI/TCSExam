# INRC-I instance library — per-instance table

This table covers all 60 instances of the First International Nurse
Rostering Competition (INRC-I, 2010): the three tracks (sprint / medium /
long), each released in three waves (bare name = early, `_late`, `_hidden`).
All instances have a 28-day planning horizon. "best known (K)" is the best
soft-constraint penalty published on the competition site
(nrpcompetition.kuleuven-kulak.be, Instances & Results page), and "reached
by" lists the teams that reported attaining it, in the order the site
records them (competition entries 2010; later improvements through 2014).
Burke & Curtois (*New approaches to nurse rostering benchmark instances*,
EJOR 237:71-81, 2014) proved many of the medium/long values optimal with
branch-and-price.

All 60 of these instances are hidden judging instances and are physically
absent from this environment. The practice set shipped in `/app/instances/`
is the official `*_hint` series (9 instances from the INRC organizer's
repository, not part of the 60); their baseline/reference values are in
`/app/public_reference.json`.

| instance | track | nurses | shift types | skills | patterns | best known (K) | reached by |
|---|---|---|---|---|---|---|---|
| long01 | long | 49 | 5 | 2 | 3 | 197 | B. Bilgin, P. Demeester, M. Misir, W. Vancroonenburg, G. Vanden Berghe, T. Wauters (2010) E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| long02 | long | 49 | 5 | 2 | 3 | 219 | E.K. Burke and T. Curtois (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| long03 | long | 49 | 5 | 2 | 3 | 240 | B. Bilgin, P. Demeester, M. Misir, W. Vancroonenburg, G. Vanden Berghe, T. Wauters (2010) E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| long04 | long | 49 | 5 | 2 | 3 | 303 | B. Bilgin, P. Demeester, M. Misir, W. Vancroonenburg, G. Vanden Berghe, T. Wauters (2010) E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| long05 | long | 49 | 5 | 2 | 3 | 284 | B. Bilgin, P. Demeester, M. Misir, W. Vancroonenburg, G. Vanden Berghe, T. Wauters (2010) E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| long_hidden01 | long | 50 | 5 | 2 | 9 | 346 | R.A.M. Gomes, H.G. Santos, T. Toffolo, S. Ribas and R.H. Vareto |
| long_hidden02 | long | 50 | 5 | 2 | 9 | 89 | R.A.M. Gomes, H.G. Santos, T. Toffolo, S. Ribas and R.H. Vareto Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| long_hidden03 | long | 50 | 5 | 2 | 9 | 38 | C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| long_hidden04 | long | 50 | 5 | 2 | 9 | 22 | C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| long_hidden05 | long | 50 | 5 | 2 | 9 | 41 | C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| long_late01 | long | 50 | 5 | 2 | 9 | 235 | E.K. Burke and T. Curtois (2010) |
| long_late02 | long | 50 | 5 | 2 | 9 | 229 | E.K. Burke and T. Curtois (2010) |
| long_late03 | long | 50 | 5 | 2 | 9 | 220 | E.K. Burke and T. Curtois (2010) |
| long_late04 | long | 50 | 5 | 2 | 9 | 221 | E.K. Burke and T. Curtois (2010) |
| long_late05 | long | 50 | 5 | 2 | 9 | 83 | Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2014) E.K. Burke and T. Curtois (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) |
| medium01 | medium | 31 | 4 | 1 | 0 | 240 | E.K. Burke and T. Curtois (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Z. Liu and J. Hao (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| medium02 | medium | 31 | 4 | 1 | 0 | 240 | E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| medium03 | medium | 31 | 4 | 1 | 0 | 236 | E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2014) |
| medium04 | medium | 31 | 4 | 1 | 0 | 237 | E.K. Burke and T. Curtois (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2014) |
| medium05 | medium | 31 | 4 | 1 | 0 | 303 | E.K. Burke and T. Curtois (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) |
| medium_hidden01 | medium | 30 | 5 | 2 | 9 | 111 | Isaac Cleland, Andrew Mason and Michael O’Sullivan |
| medium_hidden02 | medium | 30 | 5 | 2 | 9 | 219 | Isaac Cleland, Andrew Mason and Michael O’Sullivan |
| medium_hidden03 | medium | 30 | 5 | 2 | 9 | 34 | Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2014) |
| medium_hidden04 | medium | 30 | 5 | 2 | 9 | 78 | Isaac Cleland, Andrew Mason and Michael O’Sullivan |
| medium_hidden05 | medium | 30 | 5 | 2 | 9 | 118 | Isaac Cleland, Andrew Mason and Michael O’Sullivan |
| medium_late01 | medium | 30 | 4 | 1 | 7 | 157 | R.A.M. Gomes, H.G. Santos, T. Toffolo, S. Ribas and R.H. Vareto |
| medium_late02 | medium | 30 | 4 | 1 | 7 | 18 | E.K. Burke and T. Curtois (2010) |
| medium_late03 | medium | 30 | 4 | 1 | 0 | 29 | E.K. Burke and T. Curtois (2010) |
| medium_late04 | medium | 30 | 4 | 1 | 7 | 35 | E.K. Burke and T. Curtois (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| medium_late05 | medium | 30 | 5 | 2 | 7 | 107 | E.K. Burke and T. Curtois (2010) |
| sprint01 | sprint | 10 | 4 | 1 | 3 | 56 | E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Z. Liu and J. Hao (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint02 | sprint | 10 | 4 | 1 | 3 | 58 | E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Z. Liu and J. Hao (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint03 | sprint | 10 | 4 | 1 | 3 | 51 | E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Z. Liu and J. Hao (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint04 | sprint | 10 | 4 | 1 | 3 | 59 | B. Bilgin, P. Demeester, M. Misir, W. Vancroonenburg, G. Vanden Berghe, T. Wauters (2010) E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint05 | sprint | 10 | 4 | 1 | 3 | 58 | B. Bilgin, P. Demeester, M. Misir, W. Vancroonenburg, G. Vanden Berghe, T. Wauters (2010) E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Z. Liu and J. Hao (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint06 | sprint | 10 | 4 | 1 | 3 | 54 | B. Bilgin, P. Demeester, M. Misir, W. Vancroonenburg, G. Vanden Berghe, T. Wauters (2010) E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Z. Liu and J. Hao (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint07 | sprint | 10 | 4 | 1 | 3 | 56 | B. Bilgin, P. Demeester, M. Misir, W. Vancroonenburg, G. Vanden Berghe, T. Wauters (2010) E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Z. Liu and J. Hao (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint08 | sprint | 10 | 4 | 1 | 3 | 56 | E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Z. Liu and J. Hao (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint09 | sprint | 10 | 4 | 1 | 3 | 55 | E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Z. Liu and J. Hao (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint10 | sprint | 10 | 4 | 1 | 3 | 52 | E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Z. Liu and J. Hao (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_hidden01 | sprint | 10 | 3 | 1 | 4 | 32 | R.A.M. Gomes, H.G. Santos, T. Toffolo, S. Ribas and R.H. Vareto Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_hidden02 | sprint | 10 | 3 | 1 | 4 | 32 | B. Bilgin, P. Demeester, M. Misir, W. Vancroonenburg, G. Vanden Berghe, T. Wauters (2010) K. Nonobe (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_hidden03 | sprint | 10 | 4 | 1 | 8 | 62 | K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_hidden04 | sprint | 10 | 4 | 1 | 8 | 66 | R.A.M. Gomes, H.G. Santos, T. Toffolo, S. Ribas and R.H. Vareto Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_hidden05 | sprint | 10 | 4 | 1 | 8 | 59 | B. Bilgin, P. Demeester, M. Misir, W. Vancroonenburg, G. Vanden Berghe, T. Wauters (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_hidden06 | sprint | 10 | 3 | 1 | 4 | 130 | R.A.M. Gomes, H.G. Santos, T. Toffolo, S. Ribas and R.H. Vareto Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2014) |
| sprint_hidden07 | sprint | 10 | 3 | 1 | 4 | 153 | C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2014) |
| sprint_hidden08 | sprint | 10 | 4 | 1 | 8 | 204 | R.A.M. Gomes, H.G. Santos, T. Toffolo, S. Ribas and R.H. Vareto Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2014) |
| sprint_hidden09 | sprint | 10 | 4 | 1 | 8 | 338 | C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2014) |
| sprint_hidden10 | sprint | 10 | 4 | 1 | 8 | 306 | C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_late01 | sprint | 10 | 4 | 1 | 8 | 37 | E.K. Burke and T. Curtois (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_late02 | sprint | 10 | 3 | 1 | 4 | 42 | E.K. Burke and T. Curtois (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_late03 | sprint | 10 | 4 | 1 | 8 | 48 | E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_late04 | sprint | 10 | 4 | 1 | 8 | 73 | R.A.M. Gomes, H.G. Santos, T. Toffolo, S. Ribas and R.H. Vareto Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_late05 | sprint | 10 | 4 | 1 | 8 | 44 | E.K. Burke and T. Curtois (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_late06 | sprint | 10 | 4 | 1 | 0 | 42 | E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Z. Liu and J. Hao (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_late07 | sprint | 10 | 4 | 1 | 0 | 42 | E.K. Burke and T. Curtois (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2014) |
| sprint_late08 | sprint | 10 | 4 | 1 | 0 | 17 | E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Z. Liu and J. Hao (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_late09 | sprint | 10 | 4 | 1 | 0 | 17 | E.K. Burke and T. Curtois (2010) K. Nonobe (2010) C. Valouxis, C. Gogos, G. Goulas, P. Alefragis, E. Housos (2010) Z. Liu and J. Hao (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
| sprint_late10 | sprint | 10 | 4 | 1 | 0 | 43 | E.K. Burke and T. Curtois (2010) Ioannis Tassopoulos, Ioannis Solos, Grigorios Beligiannis (2013) |
