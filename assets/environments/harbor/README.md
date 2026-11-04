# Harbor egress-control build context

[English](README.md) | [简体中文](README.zh-CN.md)

These notes are for maintainers preparing the optional Docker network-control helper; they are not task instructions.

`egress-control/` is an unmodified copy of the five files in the Docker egress-control context of the [`harbor==0.22.0`](https://pypi.org/project/harbor/0.22.0/) Python package. The package metadata declares Apache-2.0; its accompanying license text is preserved in `LICENSE`.

The CLI normalizes file and directory permissions before calculating Harbor's
`docker_build_context_hash` with `Dockerfile`, empty build arguments and platform
`linux/amd64`. The declared hash is recorded in
[`assets/sources.json`](../../sources.json) under `harbor-0220-egress-control`;
the host-support image declaration uses the same value. The consistency test
checks both declarations against Harbor's installed context and the normalized
vendored files:

```bash
python -m pytest src/tcsexam/tests/test_harbor_egress_control.py
```

Keep provenance material outside `egress-control/`: Harbor's hash covers every
file and its mode in that directory.
