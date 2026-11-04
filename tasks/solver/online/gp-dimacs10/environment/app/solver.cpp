// Baseline balanced graph partitioner (starting point for the agent).
//
// Reads an undirected, unweighted graph on stdin in the METIS/DIMACS10
// format:
//   - optional comment lines starting with '%'
//   - header line: n m            (n vertices, m undirected edges)
//   - then n lines: line i lists the neighbours of vertex i (1-based ids)
//
// Writes a partition of the vertices into k = 4 blocks on stdout: exactly
// n integers from {0,1,2,3} (whitespace-separated, any layout), where token
// i is the block of vertex i (vertices are 1-based in the input order).
// A partition is valid iff every block holds at most floor(1.03 * n / 4)
// vertices; the judge recomputes the edge cut from scratch.
//
// Heuristic: a single call to KaHIP's kaffpa() library function in FAST
// mode with a fixed seed (KaHIP v3.25, MIT license, vendored in /app/kahip).
// The imbalance parameter passed to KaHIP is adjusted so that KaHIP's
// internal block-weight cap equals the judge's cap floor(1.03 * n / 4).
// Deliberately plain: one mode, one seed, no restarts, no time management.
// There is a lot of room to improve (stronger modes, multi-seed restarts,
// spending the shared time pool where it pays, your own refinement, ...).
//
// Env: GP_TIME_POOL carries the remaining total time pool in seconds (the
// judge enforces it globally). This baseline does not use it: one FAST call
// is always far inside the pool.
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

#include "kaHIP_interface.h"

// Read the whole graph from stdin in METIS/DIMACS10 format into CSR.
// Returns false on a malformed input.
static bool read_graph(int& n, std::vector<kahip_idx>& xadj,
                       std::vector<kahip_idx>& adjncy) {
    std::string line;
    long long m = -1;
    // header: first non-comment, non-blank line
    while (std::getline(std::cin, line)) {
        size_t b = line.find_first_not_of(" \t\r");
        if (b == std::string::npos || line[b] == '%') continue;
        if (std::sscanf(line.c_str(), "%d %lld", &n, &m) != 2 || n <= 0 || m < 0)
            return false;
        break;
    }
    if (m < 0) return false;
    xadj.assign(n + 1, 0);
    adjncy.clear();
    adjncy.reserve(2 * m);
    int v = 0;
    while (v < n && std::getline(std::cin, line)) {
        size_t b = line.find_first_not_of(" \t\r");
        if (b != std::string::npos && line[b] == '%') continue;  // comment
        // every other line (blank included) is vertex v's adjacency list
        const char* p = line.c_str();
        while (*p) {
            while (*p && std::isspace((unsigned char)*p)) ++p;
            if (!*p) break;
            char* end = nullptr;
            long u = std::strtol(p, &end, 10);
            if (end == p || u < 1 || u > n) return false;
            adjncy.push_back((kahip_idx)u - 1);
            p = end;
        }
        xadj[v + 1] = (kahip_idx)adjncy.size();
        ++v;
    }
    return v == n && (long long)adjncy.size() == 2 * m;
}

int main() {
    int n = 0;
    std::vector<kahip_idx> xadj, adjncy;
    if (!read_graph(n, xadj, adjncy)) return 1;

    const int k = 4;
    // Judge's balance cap: every block <= floor(1.03 * n / k) vertices.
    // KaHIP's library path internally allows up to
    // ceil((1+eps) * n / k); pick eps so that cap lands exactly on ours.
    const long long cap = (103LL * n) / (100LL * k);  // floor(1.03 * n / k)
    double eps = (cap - 0.5) * k / (double)n - 1.0;   // ceil((1+eps)n/k) = cap
    if (eps < 0.0) eps = 0.0;

    std::vector<int> part(n, 0);
    int nparts = k, seed = 0;
    kahip_idx edgecut = 0;
    // single FAST-mode call, fixed seed, no restarts
    kaffpa(&n, nullptr, xadj.data(), nullptr, adjncy.data(), &nparts, &eps,
           true /*suppress_output*/, seed, FAST, &edgecut, part.data());

    for (int i = 0; i < n; ++i) std::printf("%d\n", part[i]);
    return 0;
}
