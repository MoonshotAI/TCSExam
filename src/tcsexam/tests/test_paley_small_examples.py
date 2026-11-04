"""Cross-check the numerical reference against independent subset enumeration."""

import importlib.util
from itertools import combinations, permutations
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "tasks/open/explicit-ramsey-graph-log/tests/reference/small_examples.py"
spec = importlib.util.spec_from_file_location("paley_examples", SCRIPT)
examples = importlib.util.module_from_spec(spec)
spec.loader.exec_module(examples)


def from_edges(n, edges):
    adjacency = [0] * n
    for u, v in edges:
        adjacency[u] |= 1 << v
        adjacency[v] |= 1 << u
    return adjacency


def exhaustive_clique(n, adjacency):
    for size in range(n, -1, -1):
        for vertices in combinations(range(n), size):
            if all(adjacency[u] & (1 << v) for u, v in combinations(vertices, 2)):
                return size


class PaleyReferenceTests(unittest.TestCase):
    def test_every_simple_graph_up_to_five_vertices(self):
        for n in range(6):
            edges = list(combinations(range(n), 2))
            for mask in range(1 << len(edges)):
                adjacency = from_edges(n, (edge for i, edge in enumerate(edges) if mask >> i & 1))
                self.assertEqual(examples.max_clique(n, adjacency),
                                 exhaustive_clique(n, adjacency), (n, mask))

    def test_vertex_relabeling_preserves_clique_size(self):
        edges = [(0, 1), (1, 2), (0, 2), (2, 3), (3, 4), (4, 5), (5, 3)]
        for permutation in permutations(range(6)):
            adjacency = from_edges(6, ((permutation[u], permutation[v]) for u, v in edges))
            self.assertEqual(examples.max_clique(6, adjacency), 3, permutation)

    def test_small_paley_graphs_and_complements_against_enumeration(self):
        for n, expected in ((5, 2), (13, 3), (17, 3)):
            adjacency = examples.paley_adj(n)
            for graph in (adjacency, examples.complement_adj(n, adjacency)):
                self.assertEqual(exhaustive_clique(n, graph), expected)
                self.assertEqual(examples.max_clique(n, graph), expected)

    def test_empty_and_complete_graphs(self):
        for n in range(10):
            empty = [0] * n
            self.assertEqual(examples.max_clique(n, empty), min(n, 1))
            self.assertEqual(examples.max_clique(n, examples.complement_adj(n, empty)), n)


if __name__ == "__main__":
    unittest.main()
