// Public mathematical explanations, based on the task statements. These omit
// changing record claims and the private evaluation or environment instructions.
const explanations = {
  'ramsey-r55': [
    "The Ramsey number R(5,5) is the first size at which every red–blue coloring of a complete graph contains five vertices with all ten connecting edges the same color.",
    "A coloring on N vertices that avoids both kinds of five-cliques proves R(5,5) > N. A proof that every coloring on N vertices contains a monochromatic five-clique proves R(5,5) ≤ N. The task accepts a certified lower or upper bound."
  ],
  'ramsey-r46': [
    "Here the two colors have different restrictions: four vertices may not form an all-red clique, and six vertices may not form an all-blue clique.",
    "A valid avoiding coloring on N vertices certifies R(4,6) > N. A proof that every coloring on N vertices contains a red four-clique or a blue six-clique certifies R(4,6) ≤ N. The task accepts either direction."
  ],
  'ramsey-r3-10': [
    "A graph is sought with no triangle and no independent set of ten vertices. Equivalently, color its edges red and the missing edges blue; red triangles and blue ten-cliques are forbidden.",
    "A valid avoiding graph on N vertices certifies R(3,10) > N. A proof that no such graph on N vertices exists certifies R(3,10) ≤ N. Both the triangle exclusion and the independent-set exclusion must refer to the same graph; the task accepts either a lower or an upper bound."
  ],
  'vdw-w27': [
    'An arithmetic progression has a fixed positive step: its seven positions are a, a+d, …, a+6d. The van der Waerden number W(2,7) is the first interval length for which every two-coloring contains a monochromatic progression of this length.',
    'The construction assigns a color to every integer in a long initial interval. All seven-term progressions that fit inside that interval must be checked, including those with large steps.'
  ],
  'capset-d7': [
    "The points have seven coordinates, each in the field with three elements. A cap set contains no affine line: there are no three distinct selected points whose coordinatewise sum is zero.",
    "The task accepts either a large cap set with a proof of its properties or an upper-bound proof excluding cap sets of a chosen size. The planar sketch illustrates the forbidden relation in ternary affine space; the task has seven coordinates."
  ],
  'covering-code-k10': [
    'The ten-dimensional binary cube contains every ten-bit word. The Hamming distance between two words counts the positions where they differ.',
    'A covering code is a selected collection of words. Every word in the cube must either be selected or differ in only one position from a selected word. The task minimizes the size of this collection and certifies coverage of the whole cube.'
  ],
  'binary-code-a22-10': [
    "A binary code is a set of words of a fixed length. Here every word has 22 bits, and each pair of distinct words must differ in at least ten positions. The quantity A(22,10) is the largest possible size of such a code.",
    "The task accepts either direction: an explicit code with verified pairwise distances gives a lower bound on A(22,10), while a proof limiting the size of every valid code gives an upper bound. A construction is valid only when every distinct pair satisfies the distance requirement. The illustration uses shortened rows to explain that check."
  ],
  'binary-code-a24-10': [
    "A binary code is a set of words of a fixed length. Here every word has 24 bits, and each pair of distinct words must differ in at least ten positions. The quantity A(24,10) is the largest possible size of such a code.",
    "The task accepts either direction: an explicit code with verified pairwise distances gives a lower bound on A(24,10), while a proof limiting the size of every valid code gives an upper bound. A construction is valid only when every distinct pair satisfies the distance requirement. The illustration uses shortened rows to explain that check."
  ],
  'quantum-code-25-7': [
    'A stabilizer code is specified by independent, pairwise-commuting Pauli generators. This task fixes 25 physical qubits and seven logical qubits, and asks for a large code distance d.',
    'The distance is the minimum weight of a Pauli operator that commutes with every stabilizer generator but is outside the stabilizer itself. Low-weight elements inside the stabilizer are permitted, so checking only the lightest commuting operator would give the wrong objective.'
  ],
  'mols-n10': [
    "A Latin square of order n is an n-by-n array in which each of n symbols appears exactly once in every row and column. Two such squares are orthogonal when superimposing them produces each ordered pair exactly once.",
    "The task permits orders 10, 12, 14, 15, 18, 20, 21, 22, 24 and 26, with a separate reference family size at each order. Choose an order and construct a large family of pairwise orthogonal squares there. The order-three illustration explains the overlay condition."
  ],
  'cage-girth': [
    'A regular graph gives every vertex the same degree. Its girth is the length of its shortest cycle. For a prescribed degree and minimum girth, the cage problem asks how few vertices can suffice.',
    'The task includes several degree–girth parameter pairs. A submitted graph must satisfy the selected pair and certify its vertex count. The Petersen graph in the illustration is the small degree-three, girth-five example.'
  ],
  'sorting-network-size': [
    'A sorting network is a fixed sequence of comparisons between wires. Each comparison sends the smaller value to one wire and the larger to the other; the sequence cannot depend on the input values.',
    'This task uses 16 wires and minimizes the number of comparators. Correctness must hold for every input. It is sufficient to check all Boolean inputs, because the zero–one principle extends this guarantee to arbitrary ordered values.'
  ],
  'ex-c3c4-maxedges': [
    "For a fixed vertex count, the extremal function ex(n, {C₃, C₄}) is the greatest number of edges in a simple graph containing neither a triangle nor a four-cycle. This task fixes n = 124.",
    "A valid explicit graph on 124 vertices certifies a lower bound on ex(124, {C₃, C₄}). The highlighted five-cycle is allowed. The homepage case study displays a submitted graph on the required 124 vertices whose triangle and four-cycle checks were verified."
  ],
  'kissing-d9': [
    'The kissing number counts how many equal spheres can touch one central sphere without overlapping. After rescaling their centers, the question becomes a point configuration on the unit sphere in nine-dimensional space.',
    'Every pair of distinct points must have inner product at most one half, equivalent to an angular separation of at least 60 degrees. The construction seeks many points and must certify all pairwise constraints.'
  ],
  'kissing-d13': [
    'This task studies equal spheres around a central sphere in thirteen-dimensional space. Their center directions form points on the twelve-dimensional unit sphere S¹².',
    'The certificate must establish at least 60 degrees of separation for every distinct pair. The task representation uses explicit coordinates and exact checks, so rounding a plotted configuration is insufficient to establish validity.'
  ],
  'circles-in-square-n100': [
    'Exactly 100 circles of the same radius must fit inside a unit square. Every center must be at least that radius from each boundary, and every pair of centers must be separated by at least twice the radius.',
    'The radius is the objective to improve. A construction includes all center coordinates and a certificate of containment and non-overlap. The small grid in the illustration explains the constraints without claiming an optimal packing.'
  ],
  'spherical-code-d3-n50': [
    "The Tammes problem places a fixed number of points on the surface of a sphere. For fifty points, the objective is to make the closest pair as far apart in angle as possible.",
    "For unit vectors, a larger angle corresponds to a smaller inner product. The certificate uses fifty nonzero rational vectors and bounds every pair’s normalized inner product. Radially projecting each vector onto the unit sphere preserves those angles, so exact unit-length rational coordinates are unnecessary. The plotted arrangement is illustrative."
  ],
  'tsp-gap': [
    'Metric traveling salesperson asks for a shortest tour under distances satisfying the triangle inequality. Its subtour linear program relaxes a tour to fractional edge weights while retaining degree and cut constraints.',
    'The construction seeks an instance with a large ratio between the two optima. A feasible fractional solution alone gives no tour lower bound; the task also requires a certificate that every tour is sufficiently expensive.'
  ],
  'graph-tsp-gap': [
    "The distances in this variant are shortest-path distances in a connected unweighted graph. A traveling-salesperson tour is evaluated in the complete metric induced by that graph.",
    "The task constructs a graph metric and certifies a separation between its optimal tour cost and its subtour relaxation. Both quantities must refer to the same underlying graph and metric.",
    "The evaluated instances have 11 to 20 vertices. Smaller examples are used only to check the certificate format."
  ],
  'rectilinear-tsp-gap': [
    'Points lie in the plane and distances use the sum of horizontal and vertical displacement. This restriction gives a particular class of metric traveling-salesperson instances.',
    'The objective is a certified ratio between the shortest tour and the subtour linear program. The certificate must account for every possible tour, alongside the feasibility and cost of the fractional solution.'
  ],
  'aaronson-ambainis': [
    'Consider a low-degree real multilinear polynomial that stays bounded on the Boolean cube and has nontrivial variance. The influence of a coordinate measures the expected squared change when that input bit is flipped.',
    'The conjecture predicts that at least one coordinate has influence bounded below by a polynomial in the variance parameter and inverse degree. The guarantee must hold uniformly as the number of variables grows.'
  ],
  'alon-jaeger-tarsi': [
    'An invertible matrix over a finite field maps vectors to vectors. The question asks for an input with every coordinate nonzero whose image also has every coordinate nonzero.',
    'The task fixes the prime-field form and its field-size hypotheses. A valid proof must handle every permitted matrix size and matrix, rather than find a vector for just the displayed example.'
  ],
  'bin-packing-mirup': [
    "A bin pattern is a combination of items that fits into one bin. The configuration linear program allows fractional amounts of these patterns, giving a lower bound on the integer number of bins.",
    "The modified integer round-up property conjectures that rounding the fractional optimum upward and adding one extra bin always suffices. Its quantifier ranges over every valid instance.",
    "Current status: OpenAI has published a counterexample and Lean proof in its [public mathematics release](https://github.com/openai/math/blob/main/lean/docs/118.md). The benchmark retains the statement fixed for evaluation. DeepSeek V4.1 Flash 1017 retrieved and adapted that public proof to the task’s fixed definitions in the evaluated runs."
  ],
  'caccetta-haggkvist': [
    'In a directed graph on n vertices, minimum out-degree k means that every vertex has arcs to at least k other vertices. This local condition is proposed to force a directed cycle of length at most the ceiling of n/k.',
    'The task asks for a proof under its graph and parameter hypotheses, or a formal counterexample. Finding some directed cycle is insufficient: its length must satisfy the stated bound.'
  ],
  'd-vs-r-total-functions': [
    'A query algorithm learns an unknown Boolean input by inspecting individual bits. D(f) is the least worst-case query count of a deterministic algorithm, and R(f) is the bounded-error randomized query complexity.',
    'The target is a universal quadratic upper bound on D(f) in terms of R(f) for total Boolean functions. Totality matters: the function must be defined on every input, with no promise restricting the input set.'
  ],
  'evasiveness-graph-properties': [
    'A graph property is a Boolean function of the possible edges. The task concerns properties invariant under relabeling vertices, monotone under adding edges, and nontrivial.',
    'A deterministic decision tree asks whether particular edges exist. Evasiveness means that a worst-case input forces a query about every possible edge. The conjecture asserts this for every property satisfying the hypotheses.'
  ],
  'explicit-ramsey-graph-log': [
    "For a prime q congruent to 1 modulo 4, the Paley graph P_q has vertex set 𝔽_q. Distinct vertices are adjacent when their difference is a nonzero square. The task considers this prime-order family.",
    "The task asks whether one universal exponent k bounds both the largest clique and the largest independent set by (⌊log₂ q⌋ + 1)^k for every such prime q. An existence argument for unrelated random graphs does not establish this claim."
  ],
  'explicit-rigid-matrix': [
    'Matrix rigidity counts how many entries must be edited before rank drops to a chosen threshold. The task fixes a concrete family over the rationals: the Hilbert matrix with entries 1/(i+j+1).',
    'Its target is a superlinear edit lower bound when the allowed rank is a fixed fraction of the dimension. The constants and all-size quantifiers are part of the formal statement.'
  ],
  'fourier-entropy-influence': [
    'A Boolean function has a Fourier expansion indexed by subsets of its input coordinates. Its squared Fourier coefficients sum to one, so they define a probability distribution with an entropy.',
    'Total influence measures the expected number of coordinates whose individual flips change the function. The conjecture asks whether one universal constant bounds Fourier entropy by total influence for all Boolean functions.'
  ],
  'frege-not-pbounded': [
    'A Frege proof derives propositional tautologies through a fixed collection of axioms and inference rules. Proof size measures the total syntactic length, rather than the number of formulas alone.',
    'The task asks whether there is no polynomial bound on the shortest proof of every tautology. Establishing this requires a family of unavoidable proof-size lower bounds, or refuting the claim within the fixed formal system.'
  ],
  'frege-vs-extended-frege': [
    'Extended Frege permits fresh variables naming previously constructed subformulas. These names can be reused in subsequent derivations without repeatedly expanding the entire subformula.',
    'The task compares shortest proof lengths in this system and ordinary Frege. The conjectured separation concerns whether ordinary Frege can simulate every extended proof with a polynomial increase in size.'
  ],
  'krw-composition-conjecture': [
    'A Boolean formula is a tree of AND and OR gates with literals at its leaves. Its depth is the longest root-to-leaf path. In block composition, copies of g process disjoint input blocks and f combines their answers.',
    'The task uses the reciprocal-share statement: for some universal k ≥ 2 and all nonconstant f and g, the depth of f composed with g is at least D(f) + D(g)/k. Nonconstancy and this particular lower-bound form are part of the target.'
  ],
  'log-rank-conjecture': [
    "Alice receives x and Bob receives y, and they exchange bits to compute a fixed Boolean function f(x,y). The communication matrix records the function value for every input pair.",
    "The real rank of the communication matrix gives a lower bound on deterministic communication. The task asks whether, for one universal exponent c, every such matrix of real rank at least two satisfies D(f) ≤ (1 + log₂ rank(M_f))^c. The rank condition is part of the fixed formal statement."
  ],
  'lovasz-hamiltonicity': [
    'A graph is vertex-transitive when an automorphism can map any vertex to any other. The conjecture concerns finite connected graphs with this symmetry.',
    'The required Hamiltonian path visits every vertex exactly once. Its endpoints need not be adjacent, so the task does not require a Hamiltonian cycle. The Petersen graph provides the illustrated example.'
  ],
  'mansour-conjecture': [
    'A disjunctive normal form is an OR of terms, each term being an AND of literals. The conjecture concerns the distribution of Fourier mass for functions with small such formulas.',
    'It asks whether a suitably small set of Fourier coefficients captures all but a prescribed amount of the squared mass. The task fixes how that set’s size depends on the number of terms and the approximation error.'
  ],
  'mds-conjecture-nonprime': [
    'A linear code with length n and dimension k is maximum-distance-separable when its minimum distance equals n−k+1. Equivalently, any k coordinates determine the message.',
    'This task concerns the maximum possible length over non-prime finite fields. The nontrivial parameter range and the even-field exceptions are essential to the stated bound.'
  ],
  'nexp-vs-tc0': [
    'Threshold circuits combine gates that decide whether enough of their inputs are true. Polynomial-size circuits with a constant number of layers define the circuit class TC⁰.',
    'NEXP contains decision problems solvable by a nondeterministic machine in exponential time. The task asks for the specified separation between this time class and shallow threshold circuits, or its formal negation.'
  ],
  'prg-constant-width-robp': [
    'A width-four read-once branching program has four states in each layer. At layer i it reads input bit i and follows the corresponding transition, eventually accepting or rejecting.',
    'The generator must fool every length-n program with error at most 1/n while using o(log² n) seed bits. The seed-length schedule and output bits must be uniformly polynomial-time computable; a counting argument alone does not satisfy this explicitness requirement.'
  ],
  'np-vs-acc': [
    'ACC circuits have constant depth and use AND, OR, NOT and fixed-modulus counting gates. The circuit size is allowed to grow polynomially with the input length.',
    'The task fixes a satisfiability problem and asks for its separation from these circuit families, or the formal negation. Gate types, depth, modulus and size bounds are governed by the supplied definitions.'
  ],
  'omega-2': [
    'The matrix multiplication exponent describes the infimum asymptotic power needed to multiply square matrices. A direct entry-by-entry algorithm takes cubic arithmetic work, while structured algorithms reuse intermediate products.',
    'The conjecture is that the exponent equals two. This is an asymptotic statement about an algorithm family; a faster computation at one fixed matrix size does not settle it.'
  ],
  'online-bin-packing-ratio': [
    'Items arrive sequentially and must be placed immediately into capacity-limited bins. Earlier placements cannot be changed. An offline optimum knows the full item sequence in advance.',
    'The task fixes the threshold 1.56 for the optimal asymptotic competitive ratio. A ratio r permits one fixed additive constant C in the guarantee A(I) ≤ r·OPT(I) + C, uniformly over all input sequences.'
  ],
  'online-matching-random-order': [
    'One side of a bipartite graph is known in advance. Vertices on the other side arrive in uniformly random order, revealing their neighbors. Each arrival can be matched to an available neighbor or left unmatched, with no later revision.',
    'The target is a three-quarter guarantee at all sufficiently large sizes. The expectation includes both the arrival order and the algorithm’s randomness, and the comparison is with a maximum matching of the same graph.'
  ],
  'permanent-vs-determinant': [
    'The permanent sums one product for every permutation, using one matrix entry from each row and each column. The determinant uses the same products with permutation-dependent signs.',
    'Determinantal complexity asks for the size of a matrix of affine linear forms whose determinant equals the permanent polynomial. The target is a superpolynomial size lower bound under the task’s field assumptions.'
  ],
  'pfr-integers': [
    'For a finite integer set A, the sumset A+A contains all pairwise sums. Small doubling means this sumset is at most K times as large as A.',
    'The conjecture predicts that such a set has a controlled structural description using a convex body progression and a small number of translates. The task fixes the quantitative polynomial dependence on K.'
  ],
  'planar-l1-gnrs': [
    "A finite connected unweighted planar graph defines distances by the number of edges on a shortest path. An embedding into ℓ₁ assigns a vector to each vertex, with vector distance given by the sum of absolute coordinate differences.",
    "The task asks for one universal constant controlling the distortion of all pairwise distances across every permitted planar metric. The dimension of the embedding may vary; the distortion bound must remain universal."
  ],
  'polar-scaling-exponent': [
    'Polarization recursively transforms a binary-input channel into synthetic channels of different reliabilities. At a fixed error target, the scaling exponent describes how block length must grow as coding rate approaches capacity.',
    'The task fixes the threshold four for all binary memoryless symmetric channels. A proof must establish the stated universal rate of polarization, or establish its formal negation for the channel model in the task.'
  ],
  'ryser-conjecture': [
    "An r-partite r-uniform hypergraph divides vertices into r parts, with each hyperedge containing one vertex from each part. A matching consists of pairwise disjoint hyperedges.",
    "A vertex cover meets every hyperedge. Ryser’s conjecture bounds the size of a smallest such cover by r−1 times the size of a largest matching.",
    "Current status: OpenAI has published counterexamples and Lean proofs in its [public mathematics release](https://github.com/openai/math/blob/main/lean/docs/162.md). The benchmark retains the statement fixed for evaluation. DeepSeek V4.1 Flash 1017 and Kimi K3.1 Pro retrieved and adapted that public proof to the task’s fixed definitions in the evaluated runs."
  ],
  'total-coloring-conjecture': [
    'A total coloring assigns colors to both vertices and edges. Adjacent vertices must differ, edges sharing a vertex must differ, and each edge must differ from both of its endpoints.',
    'The conjecture asks whether maximum degree plus two colors always suffice. The illustrated triangle satisfies these simultaneous restrictions with three colors; the task concerns arbitrary graphs.'
  ],
  'tuza-conjecture': [
    'A triangle packing is a collection of triangles sharing no edges. A triangle edge cover is a set of edges that meets every triangle in the graph.',
    'The conjecture claims that a smallest edge cover has size at most twice a largest packing. Triangles in a packing may share vertices, so vertex-disjoint packing would measure a different problem.'
  ],
  'xor-log-rank-conjecture': [
    "A parity decision tree can query the XOR of any subset of input bits at each node. This is more flexible than querying a single input coordinate.",
    "Fourier sparsity sp(f) counts the nonzero Fourier coefficients of a Boolean function. The task asks whether one universal exponent c bounds parity decision-tree depth by (1 + log₂ sp(f))^c for every Boolean function. The added 1 handles sparsity one: a nonconstant parity function has sparsity one and needs one query."
  ]
};
export const explanationIds=Object.keys(explanations);
export function taskExplanation(task){return explanations[task.id];}
