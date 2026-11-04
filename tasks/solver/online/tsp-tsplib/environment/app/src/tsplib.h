// TSPLIB parser + distance functions + tour I/O for the tsp-tsplib task.
//
// Supports every EDGE_WEIGHT_TYPE / EDGE_WEIGHT_FORMAT present in the 111
// symmetric TSPLIB instances:
//   EUC_2D, CEIL_2D, GEO, ATT,
//   EXPLICIT with FULL_MATRIX, UPPER_ROW, LOWER_ROW, UPPER_DIAG_ROW,
//   LOWER_DIAG_ROW, UPPER_COL, LOWER_COL, UPPER_DIAG_COL, LOWER_DIAG_COL.
//
// Rounding rules follow the TSPLIB documentation (Reinelt, tsp95.pdf):
//   EUC_2D : int(d + 0.5)            (nearest integer)
//   CEIL_2D: ceil(d)
//   GEO    : int(R * acos(...) + 1.0), R = 6378.388, coordinates are
//            degrees.minutes converted by deg + 5*min/3
//   ATT    : rij = sqrt((dx^2+dy^2)/10); tij = nint(rij);
//            tij < rij ? tij+1 : tij
#pragma once
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace tsplib {

struct Instance {
    std::string name;
    std::string edge_weight_type;    // EUC_2D / CEIL_2D / GEO / ATT / EXPLICIT
    std::string edge_weight_format;  // for EXPLICIT
    int n = 0;
    // 1-based coordinates (coordinate types) or full matrix (EXPLICIT).
    std::vector<double> xs, ys;
    std::vector<int64_t> matrix;     // (n+1)*(n+1), 1-based, EXPLICIT only

    inline int64_t dist(int i, int j) const {
        if (edge_weight_type == "EXPLICIT") return matrix[i * (n + 1) + j];
        const double dx = xs[i] - xs[j], dy = ys[i] - ys[j];
        if (edge_weight_type == "EUC_2D")
            return (int64_t)(std::sqrt(dx * dx + dy * dy) + 0.5);
        if (edge_weight_type == "CEIL_2D")
            return (int64_t)std::ceil(std::sqrt(dx * dx + dy * dy));
        if (edge_weight_type == "GEO") {
            static const double R = 6378.388;
            static const double PI = 3.141592;
            auto conv = [](double x) {
                int deg = (int)x;
                double mn = x - deg;
                return PI * (deg + 5.0 * mn / 3.0) / 180.0;
            };
            double lati = conv(xs[i]), latj = conv(xs[j]);
            double loni = conv(ys[i]), lonj = conv(ys[j]);
            double q1 = std::cos(loni - lonj);
            double q2 = std::cos(lati - latj);
            double q3 = std::cos(lati + latj);
            return (int64_t)(R * std::acos(0.5 * ((1.0 + q1) * q2
                                                  - (1.0 - q1) * q3)) + 1.0);
        }
        // ATT (pseudo-euclidean)
        double rij = std::sqrt((dx * dx + dy * dy) / 10.0);
        int64_t tij = (int64_t)(rij + 0.5);
        return tij < rij ? tij + 1 : tij;
    }
};

inline bool parse_header_line(const std::string& s, std::string& key,
                              std::string& val) {
    size_t colon = s.find(':');
    if (colon == std::string::npos) return false;
    key = s.substr(0, colon);
    val = s.substr(colon + 1);
    auto trim = [](std::string& t) {
        size_t a = t.find_first_not_of(" \t\r\n");
        size_t b = t.find_last_not_of(" \t\r\n");
        t = (a == std::string::npos) ? "" : t.substr(a, b - a + 1);
    };
    trim(key);
    trim(val);
    return true;
}

// Dies with a message on stderr and exit(1) on any malformed input.
inline Instance load(const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        fprintf(stderr, "cannot open %s\n", path.c_str());
        exit(1);
    }
    Instance inst;
    std::string line, section;
    std::vector<std::string> body;
    while (std::getline(in, line)) {
        // strip CR (instances come with unix endings, but be tolerant)
        if (!line.empty() && line.back() == '\r') line.pop_back();
        std::string s = line;
        size_t a = s.find_first_not_of(" \t");
        if (a == std::string::npos) continue;
        size_t b = s.find_last_not_of(" \t");
        s = s.substr(a, b - a + 1);
        if (s == "NODE_COORD_SECTION" || s == "EDGE_WEIGHT_SECTION" ||
            s == "DISPLAY_DATA_SECTION" || s == "TOUR_SECTION" ||
            s == "EDGE_DATA_SECTION" || s == "FIXED_EDGES_SECTION") {
            section = s;
            continue;
        }
        if (s == "EOF") break;
        if (section.empty()) {
            std::string key, val;
            if (parse_header_line(s, key, val)) {
                if (key == "NAME") inst.name = val;
                else if (key == "EDGE_WEIGHT_TYPE") inst.edge_weight_type = val;
                else if (key == "EDGE_WEIGHT_FORMAT") inst.edge_weight_format = val;
                else if (key == "DIMENSION") inst.n = atoi(val.c_str());
            }
            continue;
        }
        if (section == "NODE_COORD_SECTION" || section == "EDGE_WEIGHT_SECTION")
            body.push_back(s);
        // other sections (DISPLAY_DATA etc.) are ignored
    }
    if (inst.n <= 0) {
        fprintf(stderr, "%s: missing DIMENSION\n", path.c_str());
        exit(1);
    }
    const int n = inst.n;
    if (inst.edge_weight_type.empty()) inst.edge_weight_type = "EUC_2D";

    if (inst.edge_weight_type == "EXPLICIT") {
        const std::string& f = inst.edge_weight_format;
        int64_t need;
        if (f == "FULL_MATRIX") need = (int64_t)n * n;
        else if (f == "UPPER_ROW" || f == "LOWER_ROW" ||
                 f == "UPPER_COL" || f == "LOWER_COL")
            need = (int64_t)n * (n - 1) / 2;
        else if (f == "UPPER_DIAG_ROW" || f == "LOWER_DIAG_ROW" ||
                 f == "UPPER_DIAG_COL" || f == "LOWER_DIAG_COL")
            need = (int64_t)n * (n + 1) / 2;
        else {
            fprintf(stderr, "%s: unsupported EDGE_WEIGHT_FORMAT %s\n",
                    path.c_str(), f.c_str());
            exit(1);
        }
        std::vector<int64_t> vals;
        vals.reserve(need);
        for (const std::string& bl : body) {
            std::istringstream iss(bl);
            std::string tok;
            while (iss >> tok) {
                if ((int64_t)vals.size() >= need) break;
                vals.push_back(atoll(tok.c_str()));
            }
            if ((int64_t)vals.size() >= need) break;
        }
        if ((int64_t)vals.size() < need) {
            fprintf(stderr, "%s: expected %lld matrix entries, got %zu\n",
                    path.c_str(), (long long)need, vals.size());
            exit(1);
        }
        inst.matrix.assign((int64_t)(n + 1) * (n + 1), 0);
        auto M = [&](int i, int j) -> int64_t& {
            return inst.matrix[i * (n + 1) + j];
        };
        int64_t k = 0;
        if (f == "FULL_MATRIX") {
            for (int i = 1; i <= n; i++)
                for (int j = 1; j <= n; j++) M(i, j) = vals[k++];
        } else if (f == "UPPER_ROW") {
            for (int i = 1; i <= n; i++)
                for (int j = i + 1; j <= n; j++) M(i, j) = M(j, i) = vals[k++];
        } else if (f == "LOWER_ROW") {
            for (int i = 1; i <= n; i++)
                for (int j = 1; j < i; j++) M(i, j) = M(j, i) = vals[k++];
        } else if (f == "UPPER_DIAG_ROW") {
            for (int i = 1; i <= n; i++)
                for (int j = i; j <= n; j++) M(i, j) = M(j, i) = vals[k++];
        } else if (f == "LOWER_DIAG_ROW") {
            for (int i = 1; i <= n; i++)
                for (int j = 1; j <= i; j++) M(i, j) = M(j, i) = vals[k++];
        } else if (f == "UPPER_COL") {
            for (int j = 1; j <= n; j++)
                for (int i = 1; i < j; i++) M(i, j) = M(j, i) = vals[k++];
        } else if (f == "LOWER_COL") {
            for (int j = 1; j <= n; j++)
                for (int i = j + 1; i <= n; i++) M(i, j) = M(j, i) = vals[k++];
        } else if (f == "UPPER_DIAG_COL") {
            for (int j = 1; j <= n; j++)
                for (int i = 1; i <= j; i++) M(i, j) = M(j, i) = vals[k++];
        } else {  // LOWER_DIAG_COL
            for (int j = 1; j <= n; j++)
                for (int i = j; i <= n; i++) M(i, j) = M(j, i) = vals[k++];
        }
    } else if (inst.edge_weight_type == "EUC_2D" ||
               inst.edge_weight_type == "CEIL_2D" ||
               inst.edge_weight_type == "GEO" ||
               inst.edge_weight_type == "ATT") {
        inst.xs.assign(n + 1, 0.0);
        inst.ys.assign(n + 1, 0.0);
        int read = 0;
        for (const std::string& bl : body) {
            if (read >= n) break;
            std::istringstream iss(bl);
            int idx;
            double x, y;
            if (!(iss >> idx >> x >> y)) break;
            if (idx < 1 || idx > n) {
                fprintf(stderr, "%s: bad node index %d\n", path.c_str(), idx);
                exit(1);
            }
            inst.xs[idx] = x;
            inst.ys[idx] = y;
            read++;
        }
        if (read < n) {
            fprintf(stderr, "%s: expected %d coordinate lines, got %d\n",
                    path.c_str(), n, read);
            exit(1);
        }
    } else {
        fprintf(stderr, "%s: unsupported EDGE_WEIGHT_TYPE %s\n", path.c_str(),
                inst.edge_weight_type.c_str());
        exit(1);
    }
    return inst;
}

// Reads a tour file: whitespace-separated city indices (1..n), a permutation
// in visiting order. Returns false on any malformation.
inline bool load_tour(const std::string& path, int n, std::vector<int>& tour) {
    std::ifstream in(path);
    if (!in) return false;
    tour.clear();
    std::string tok;
    while (in >> tok) {
        if (!tok.empty() && tok[0] == 'c') {  // comment line: skip to EOL
            std::string rest;
            std::getline(in, rest);
            continue;
        }
        char* end = nullptr;
        long v = strtol(tok.c_str(), &end, 10);
        if (end == tok.c_str() || *end != '\0') return false;
        tour.push_back((int)v);
    }
    if ((int)tour.size() != n) return false;
    std::vector<char> seen(n + 1, 0);
    for (int v : tour) {
        if (v < 1 || v > n || seen[v]) return false;
        seen[v] = 1;
    }
    return true;
}

inline int64_t tour_length(const Instance& inst, const std::vector<int>& tour) {
    int64_t total = 0;
    for (size_t i = 0; i < tour.size(); i++)
        total += inst.dist(tour[i], tour[(i + 1) % tour.size()]);
    return total;
}

}  // namespace tsplib
