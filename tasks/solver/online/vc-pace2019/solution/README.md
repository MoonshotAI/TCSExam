# Oracle Answer Installer

This directory provides the standard-answer installer for validating the `vc-pace2019` oracle. It is not included in the agent-visible environment.

`solve.sh` installs the harvested, proven-optimal covers from `precomputed/` into `/app`; each filename uses the SHA-1 hash of the corresponding instance contents. The script replaces the solver, which hashes the instance on standard input and returns its matching cover, and replaces `build.sh` with a successful no-op. The judge then receives a legal cover of size `K` for every instance, for an expected reward of `1.0`.

Each `precomputed/<sha1>.vc` file contains an answer for one judged instance, and `manifest.json` maps each SHA-1 to its instance name. These are the even-numbered private instances with proven optima. Every cover passed the official `vc_validate` and has size `K`. The ingestion date and source task IDs are recorded in `tests/SAMPLING.md`; the files were harvested by `measure/vc-kb`.
