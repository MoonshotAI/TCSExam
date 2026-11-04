# Building the corresponding `vc_validate` source

This document accompanies the GPL-3.0 `vc_validate` program in the public VC judge image. It is for recipients who want to rebuild the validator from the exact accompanying source.

## Source identity

- Upstream: https://github.com/hmarkus/vc_validate
- Source path: `cpp/vc_validate.cpp`
- Reviewed upstream commit: `8b6a8cd6dfe5d98b5ddba8b2049423c81576326d`
- Source URL: https://raw.githubusercontent.com/hmarkus/vc_validate/8b6a8cd6dfe5d98b5ddba8b2049423c81576326d/cpp/vc_validate.cpp
- Source SHA-256: `a728ea6a3ca2bbc8a8b0f367c1485759d799724e22da615117a1fc04d8e7856a`
- License SHA-256: `8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903`

The accompanying `vc_validate.cpp` is byte-identical to the upstream file and to the source embedded in the original public-only image. No source edit was made for this release candidate.

## Fixed public build toolchain

Use the multi-platform Docker Hub GCC image resolved by this immutable digest:

```text
docker.io/library/gcc@sha256:b99b86a28812b1e6453a231a947dc43d76fe192788a12f344a9b568bf9f5d24c
```

The acceptance build selected `linux/amd64` and reported `g++ (GCC) 14.2.0`. The original image contains Debian `g++ 14.2.0-19`; its original task build command was `g++ -std=c++11 -O3`. The public rebuild uses the same language level and optimization arguments with the fixed public toolchain above.

Run the accompanying build script:

```bash
bash build-vc_validate.sh ./vc_validate
```

Its complete compile step is:

```bash
g++ -std=c++11 -O3 -o /out/vc_validate /src/vc_validate.cpp
```

The script mounts this directory read-only as `/src` and the caller-selected output directory as `/out`. No task data, hidden files, credentials, or internal registry is needed.

## Acceptance and binary retention

The original image binary has SHA-256 `dbeb592aed921967305a9de012d88eddce4e98ff1acca4cb4fa2b9b057a9ed3a`; the rebuilt acceptance binary has SHA-256 `9b8d648791cbe238a0dbececfeadefbbb3122f989fd690fb8a62e48d37f5d356`. They are not claimed to be byte-identical.

Both binaries were compared on all 100 public instances with a generated valid all-vertex cover, a generated invalid cover leaving one public edge uncovered, and a generated invalid declared-size header. All 300 process results matched exactly, including exit status, standard output, standard error, and success classification. Complete public scoring documents also matched after removing only elapsed seconds. The top-level public baseline is null, so both unsharded comparison runs reported null `reward` and `raw_reward`; this is not a numeric zero score.

The candidate retains the original binary at `/usr/local/bin/vc_validate`. The rebuilt binary is acceptance evidence only and is not substituted into the payload.
