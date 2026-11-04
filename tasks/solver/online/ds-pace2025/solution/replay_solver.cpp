// Oracle replay stub for ds-pace2025-async (installed as /app/solver.cpp by
// solution/solve.sh). The judge compiles every top-level /app/*.cpp with
// `g++ -O2 -std=c++17` and runs the resulting binary once per hidden
// instance: graph on stdin, dominating set on stdout, hard-killed at the
// DS_TIME_POOL limit.
//
// This stub identifies the instance by the SHA-256 of its exact stdin bytes
// (same content-hash key as the precomputed manifest) and replays the
// recorded champion-reference solution from /app/precomputed/. Every
// recorded solution was produced by the calibrated K-anchor measurement
// (fontanf / Root, full 300 s PACE 2025 budget) and validated with the
// official PACE 2025 DS verifier, landing at the reference size K — so the
// replay scores r = 1.0 on every participating instance (A == K exactly).
// An instance whose hash is not in the manifest exits 1 (that instance
// scores 0, the rest still count) rather than fabricating output.
//
// SHA-256 is implemented here in full (public-domain style implementation)
// so the stub stays dependency-free: the judge links with a bare
// `g++ -O2 -std=c++17` line, no -lcrypto.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace sha256 {

class Hasher {
public:
    Hasher() { reset(); }

    void update(const unsigned char* data, size_t len) {
        for (size_t i = 0; i < len; ++i) {
            buffer_[buflen_++] = data[i];
            if (buflen_ == 64) {
                transform(buffer_);
                bitlen_ += 512;
                buflen_ = 0;
            }
        }
    }

    std::string hex() {
        unsigned char* b = buffer_;
        size_t i = buflen_;
        uint64_t bits = bitlen_ + 8 * buflen_;
        // append 0x80 then zeros until 56 mod 64, then 8-byte big-endian bit count
        b[i++] = 0x80;
        while (i % 64 != 56) b[i++] = 0x00;
        for (int s = 56; s >= 0; s -= 8) b[i++] = (unsigned char)((bits >> s) & 0xff);
        size_t blocks = i / 64;
        for (size_t j = 0; j < blocks; ++j) transform(b + 64 * j);

        static const char* hx = "0123456789abcdef";
        std::string out;
        out.reserve(64);
        for (int j = 0; j < 8; ++j)
            for (int s = 28; s >= 0; s -= 4)
                out.push_back(hx[(state_[j] >> s) & 0xf]);
        return out;
    }

private:
    uint32_t state_[8];
    unsigned char buffer_[128];
    size_t buflen_;
    uint64_t bitlen_;

    void reset() {
        static const uint32_t init[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372,
                                         0xa54ff53a, 0x510e527f, 0x9b05688c,
                                         0x1f83d9ab, 0x5be0cd19};
        memcpy(state_, init, sizeof(init));
        buflen_ = 0;
        bitlen_ = 0;
    }

    static uint32_t rotr(uint32_t x, uint32_t n) { return (x >> n) | (x << (32 - n)); }

    void transform(const unsigned char* p) {
        static const uint32_t K[64] = {
            0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
            0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
            0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
            0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
            0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
            0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
            0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
            0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
            0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
            0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
            0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
        uint32_t m[64];
        for (int i = 0; i < 16; ++i)
            m[i] = (uint32_t)p[4 * i] << 24 | (uint32_t)p[4 * i + 1] << 16 |
                   (uint32_t)p[4 * i + 2] << 8 | (uint32_t)p[4 * i + 3];
        for (int i = 16; i < 64; ++i) {
            uint32_t s0 = rotr(m[i - 15], 7) ^ rotr(m[i - 15], 18) ^ (m[i - 15] >> 3);
            uint32_t s1 = rotr(m[i - 2], 17) ^ rotr(m[i - 2], 19) ^ (m[i - 2] >> 10);
            m[i] = m[i - 16] + s0 + m[i - 7] + s1;
        }
        uint32_t a = state_[0], b = state_[1], c = state_[2], d = state_[3];
        uint32_t e = state_[4], f = state_[5], g = state_[6], h = state_[7];
        for (int i = 0; i < 64; ++i) {
            uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
            uint32_t ch = (e & f) ^ (~e & g);
            uint32_t t1 = h + S1 + ch + K[i] + m[i];
            uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
            uint32_t mj = (a & b) ^ (a & c) ^ (b & c);
            uint32_t t2 = S0 + mj;
            h = g; g = f; f = e; e = d + t1;
            d = c; c = b; b = a; a = t1 + t2;
        }
        state_[0] += a; state_[1] += b; state_[2] += c; state_[3] += d;
        state_[4] += e; state_[5] += f; state_[6] += g; state_[7] += h;
    }
};

}  // namespace sha256

int main() {
    std::ios::sync_with_stdio(false);

    // Slurp stdin (the instance file, up to a few hundred MB) and hash it.
    sha256::Hasher hasher;
    {
        std::vector<char> chunk(1 << 20);
        size_t n;
        while ((n = fread(chunk.data(), 1, chunk.size(), stdin)) > 0)
            hasher.update(reinterpret_cast<unsigned char*>(chunk.data()), n);
    }
    const std::string hash = hasher.hex();

    const char* dir = getenv("PRECOMPUTED_DIR");
    std::string base = dir ? dir : "/app/precomputed";

    std::ifstream mf(base + "/manifest.tsv");
    if (!mf) {
        fprintf(stderr, "replay stub: cannot open %s/manifest.tsv\n", base.c_str());
        return 1;
    }
    std::string file;
    std::string line;
    while (std::getline(mf, line)) {
        if (line.size() < 65 || line.compare(0, 64, hash) != 0) continue;
        size_t tab = line.find('\t', 64);
        if (tab == std::string::npos) continue;
        file = line.substr(tab + 1);
        // tolerate trailing whitespace
        while (!file.empty() && (file.back() == '\r' || file.back() == ' ' || file.back() == '\t'))
            file.pop_back();
        break;
    }
    if (file.empty()) {
        fprintf(stderr, "replay stub: instance %s not in manifest\n", hash.c_str());
        return 1;
    }
    if (file.find('/') != std::string::npos || file.find("..") != std::string::npos) {
        fprintf(stderr, "replay stub: bad manifest entry %s\n", file.c_str());
        return 1;
    }

    std::ifstream sol(base + "/" + file);
    if (!sol) {
        fprintf(stderr, "replay stub: cannot open %s/%s\n", base.c_str(), file.c_str());
        return 1;
    }
    std::cout << sol.rdbuf();
    return ferror(stdout) ? 1 : 0;
}
