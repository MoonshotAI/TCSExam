// jssp_check: validity checker + makespan evaluator for the jsplib-jssp
// task. Clean-room, written for this task (no third-party code).
//
//   jssp_check INSTANCE SOLUTION
//
// stdout: "OK <makespan>" iff the solution is a feasible schedule of the
// instance; otherwise "INVALID <reason>". Exit code 0 iff valid.
//
// Instance format (JSPLib standard text): first line "n m" (n jobs, m
// machines, machines numbered 0..m-1); then n lines, line j holding m pairs
// "machine duration" giving job j's operations in route order.
//
// Solution format: n lines; line j holds m non-negative integers, the start
// times of job j's operations in the same route order.
//
// Checks: exact shape (n rows of m ints, >= 0); job precedence
// (start[j][k+1] >= start[j][k] + duration[j][k]); no overlap between any
// two intervals on the same machine; makespan = max(start + duration).

#include <algorithm>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

static int fail(const string& msg) {
    printf("INVALID %s\n", msg.c_str());
    return 1;
}

int main(int argc, char** argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s INSTANCE SOLUTION\n", argv[0]);
        return 2;
    }
    ifstream in(argv[1]);
    if (!in) return fail("cannot open instance");
    long long n, m;
    if (!(in >> n >> m)) return fail("bad instance header");
    if (n <= 0 || m <= 0 || n > 100000 || m > 100000)
        return fail("bad instance dimensions");
    vector<vector<int>> mach(n, vector<int>(m)), dur(n, vector<int>(m));
    for (int j = 0; j < n; j++)
        for (int k = 0; k < m; k++) {
            if (!(in >> mach[j][k] >> dur[j][k]))
                return fail("truncated instance");
            if (mach[j][k] < 0 || mach[j][k] >= m)
                return fail("machine id out of range in instance");
            if (dur[j][k] < 0)
                return fail("negative duration in instance");
        }

    ifstream sol(argv[2]);
    if (!sol) return fail("cannot open solution");
    vector<string> lines;
    string line;
    while (getline(sol, line)) {
        // strip trailing CR/whitespace-only lines are ignored
        istringstream iss(line);
        vector<long long> row;
        long long x;
        while (iss >> x) row.push_back(x);
        if (!row.empty()) lines.push_back(line);
    }
    if ((long long)lines.size() != n) {
        char buf[128];
        snprintf(buf, sizeof buf, "expected %lld rows, got %zu", n, lines.size());
        return fail(buf);
    }
    vector<vector<long long>> st(n, vector<long long>(m));
    for (int j = 0; j < n; j++) {
        istringstream iss(lines[j]);
        vector<long long> row;
        long long x;
        string tok;
        while (iss >> tok) {
            // strict integer token
            size_t p = 0;
            if (tok[0] == '+') p = 1;
            bool digits = p < tok.size();
            for (size_t i = p; i < tok.size(); i++)
                if (!isdigit((unsigned char)tok[i])) { digits = false; break; }
            if (!digits) {
                char buf[96];
                snprintf(buf, sizeof buf, "row %d: non-integer field", j);
                return fail(buf);
            }
            row.push_back(stoll(tok));
        }
        if ((long long)row.size() != m) {
            char buf[128];
            snprintf(buf, sizeof buf, "row %d has %zu fields, expected %lld",
                     j, row.size(), m);
            return fail(buf);
        }
        for (int k = 0; k < m; k++) {
            if (row[k] < 0) {
                char buf[96];
                snprintf(buf, sizeof buf, "row %d: negative start time", j);
                return fail(buf);
            }
            st[j][k] = row[k];
        }
    }
    // job precedence
    for (int j = 0; j < n; j++)
        for (int k = 0; k + 1 < m; k++) {
            long long need = st[j][k] + dur[j][k];
            if (st[j][k + 1] < need) {
                char buf[192];
                snprintf(buf, sizeof buf,
                         "job %d: operation %d starts at %lld before operation %d ends at %lld",
                         j, k + 1, st[j][k + 1], k, need);
                return fail(buf);
            }
        }
    // machine overlap
    vector<vector<tuple<long long, long long, int, int>>> per(m);
    for (int j = 0; j < n; j++)
        for (int k = 0; k < m; k++)
            per[mach[j][k]].emplace_back(st[j][k], st[j][k] + dur[j][k], j, k);
    for (int q = 0; q < m; q++) {
        auto& v = per[q];
        sort(v.begin(), v.end());
        for (size_t i = 1; i < v.size(); i++)
            if (get<0>(v[i]) < get<1>(v[i - 1])) {
                char buf[224];
                snprintf(buf, sizeof buf,
                         "machine %d: overlap between job %d op %d [%lld,%lld) and job %d op %d [%lld,%lld)",
                         q,
                         get<2>(v[i - 1]), get<3>(v[i - 1]), get<0>(v[i - 1]), get<1>(v[i - 1]),
                         get<2>(v[i]), get<3>(v[i]), get<0>(v[i]), get<1>(v[i]));
                return fail(buf);
            }
    }
    long long ms = 0;
    for (int j = 0; j < n; j++)
        for (int k = 0; k < m; k++)
            ms = max(ms, st[j][k] + dur[j][k]);
    printf("OK %lld\n", ms);
    return 0;
}
