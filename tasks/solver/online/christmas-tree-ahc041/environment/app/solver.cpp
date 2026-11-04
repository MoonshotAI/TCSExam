// Baseline solver for the christmas-tree-ahc041 task.
//
// Reads one AHC041 instance from stdin (N M H, then N weights A, then M
// edges, then N points) and writes the most trivial legal forest: every
// vertex is a root (N copies of -1). Score = 1 + sum(A). This is legal,
// deterministic, and intentionally weak — your job is to beat it.
#include <cstdio>

int main() {
    int N, M;
    long long H;
    if (scanf("%d %d %lld", &N, &M, &H) != 3) return 1;
    for (int i = 0; i < N; i++) {
        long long a;
        if (scanf("%lld", &a) != 1) return 1;
    }
    for (int i = 0; i < M; i++) {
        int u, v;
        if (scanf("%d %d", &u, &v) != 2) return 1;
    }
    for (int i = 0; i < N; i++) {
        long long x, y;
        if (scanf("%lld %lld", &x, &y) != 2) return 1;
    }
    for (int i = 0; i < N; i++) {
        printf("-1%c", i + 1 == N ? '\n' : ' ');
    }
    return 0;
}
