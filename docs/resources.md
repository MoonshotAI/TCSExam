# Runtime images and resource preparation

[English](resources.md) | [简体中文](resources.zh-CN.md)

This guide explains how to download fixed inputs and build local evaluation images.
It is for users preparing a Docker host for TCSExam.

## Prepare images with `tcsexam build`

Run `tcsexam build` for the suite, tasks and Solver protocol you will evaluate.
For selections containing a local Lean build, first prepare its
[fixed source archives](#prepare-fixed-lean-source-archives):

```bash
tcsexam source-inputs
tcsexam build --suite lite --solver-protocol offline
tcsexam doctor --suite lite --solver-protocol offline
```

The builder reuses verified local images, acquires a declared public image, or
runs the declared local recipe. Recipes download fixed official archives,
verify their sizes and hashes, transform the selected inputs and assemble the
required images. Local preparation needs Docker, disk space and access to the
declared sources; it needs no registry account or image upload. All thirty
Solver tasks have default recipes using official downloads or fixed inputs
included in the source. See the resource-specific requirements below.

Each task has a development environment and a judging environment. Data and tool
images supply build inputs to these complete runtime images. Prepare them before
starting the evaluation. During task execution, Harbor runs the complete images;
the model environment does not perform resource preparation or start a data
container. Hidden judging inputs belong only in judging images, including their
inherited layers.

The [image manifest](../assets/images.json) links products to recipes, content
manifests and distribution conditions. A product can prefer `local_build` or
`public_image` through `acquisition.preferred`. Without a preference, a pinned
public image is selected when available, followed by the local recipe. Acquiring
a complete image requires neither its original datasets nor intermediate data
images on the execution host. A failed acquisition or build reports its error;
it does not select different task data.

## Cache, downloads and host requirements

Set `TCSEXAM_CACHE` to place the preparation cache on a disk with sufficient
space; its default is `~/.cache/tcsexam`. Recipes fix runtime paths, sizes,
hashes and permissions. Preparation verifies cached content, coordinates
concurrent calls and installs completed results atomically. An interrupted
preparation is retried; a corrupt input is reported with its path so that you
can remove it and reacquire the declared bytes.

Allow space for downloaded archives, extracted inputs, transformed outputs,
temporary files and Docker layers. Large data preparation should run on a host
sized for the selected recipe. Model execution and judging have their own CPU,
memory and time limits in the task configuration.

`HTTP_PROXY`, `HTTPS_PROXY` and `NO_PROXY` from the caller's environment are
forwarded to downloads and build commands. `docker pull` additionally needs
proxy support configured in the Docker daemon. Configure proxy credentials in
the daemon; the builder rejects them as Docker build arguments.

For a fixed upstream image, the builder first tries `docker pull`. If the daemon
cannot reach the registry and [`crane`](https://github.com/google/go-containerregistry)
is installed, it can download the pinned image directly and verify its manifest,
filesystem layers and runtime configuration. Local build references are changed
only in a temporary Dockerfile. Both acquisition routes populate the same image
identity cache used by `doctor` and `run`.

## Prepare fixed Lean source archives

Before a local Lean image build, prepare the Graphviz corresponding-source inputs:

```bash
tcsexam source-inputs
tcsexam build --suite lite --track theorem
```

The [source manifest](../assets/environments/lean-base/graphviz-epl/source-manifest.json)
pins Graphviz 15.0.0 and the hpcc-js/wasm wrapper commit
`8b86e2f83cc7344aca44fb3d8aa29a227358c5c4`. `source-inputs` downloads their
official archives, checks exact sizes and SHA-256/SHA-512 hashes, and installs
them in `assets/environments/lean-base/graphviz-epl/source/`. The Lean base
Dockerfile copies these archives and verifies `SHA256SUMS`. This prepares source
and license materials accompanying Graphviz in the image.

Verified context files or cached archives are reused and checked on every
invocation. Archive writes use bounded blocks and an atomic rename after
verification. Prepared archives remain ignored by Git. To work without network
access, acquire the exact declared official archives and import them:

```bash
tcsexam source-inputs --offline \
  --input graphviz=/path/to/graphviz-15.0.0.tar.gz \
  --input wrapper=/path/to/hpcc-js-wasm-8b86e2f83cc7344aca44fb3d8aa29a227358c5c4.tar.gz
```

`--offline` disables network downloads. Verified files already in the build
context or cache, and files supplied through `--input`, remain available.
Missing files, wrong sizes and wrong hashes fail before preparation. An upstream
access restriction or unavailable URL is reported as a download error; retry with
the same archives obtained from their
official source. Acquiring a complete published Lean image skips this local
source-preparation step.

## MaxSAT hidden data

The default recipe reconstructs the 200 MaxSAT final-judging formulas from the fixed
[MaxSAT Evaluation 2026 archive](https://zenodo.org/records/21358014).
The [recipe](../assets/data/solver/solver-maxsat-mse-judging-data-recipe.json)
pins the archive hash, selected files, conversion parameters, random seeds and
input/output formula hashes. It reproduces the declared variable and clause
ordering and verifies the complete formulas and compressed outputs. Online and
Offline final judging use the same hidden formulas; public self-test data is
prepared separately.

```bash
tcsexam build --suite full --task maxsat-mse --solver-protocol offline
```

Select `--solver-protocol online` for Online. The official archive is about
1.97 GB, and transformed formulas total about 26.8 GB before compression. Reserve
additional disk space for intermediate files, compressed outputs and Docker
layers. Conversion uses disk-backed intermediate files to limit memory use.

`build.download_timeout_sec` sets the download and retry budget. The builder
adds 180 seconds for download-tool setup and verification; data processing has
a separate build deadline. Task judging budgets are defined independently.

## Other resource-specific requirements

Read each entry for the additional requirements of that resource.

| Resource | Preparation and requirements |
|---|---|
| BPPLIB | Python 3.12+ and system libarchive with RAR support, such as Debian/Ubuntu `libarchive13` or `libarchive13t64`. The recipe downloads 19 pinned official files and reconstructs the selected instances, example packings and development table. |
| QBF public data | The pinned ParaProofa v1 source archive is about 949 MB. The recipe reconstructs the thirteen public instances and their fixed XZ compression. |
| PACE 2021 Cluster Editing and PACE 2022 Directed Feedback Vertex Set verifiers | Recipes download the pinned official ZIP/tar.gz, compile `ce_verify` or `fvs_verify` in a digest-pinned Ubuntu 22.04 linux/amd64 builder, and check source and compiled hashes. Docker supplies the compiler environment. `tcsexam build` composes the resulting tool image into the task images. |
| PACE 2025 Hitting Set | Separate recipes reconstruct the 100 public and 100 hidden plaintext inputs from `MarioGrobler/PACE2025-instances` commit `e0bff608037db1f2b9eec7a7963e31b86663e1ed`. Hashes and HGR dimensions are checked before image construction. The hidden files need no decryption key at judging time. |
| Radiation | The default recipe verifies all 36 final-judging inputs: 24 project-generated Apache-2.0 inputs and 12 fixed MiniZinc MIT-licensed files. No separately supplied archive is required. |

In BPPLIB's development table, `best` is the published feasible upper bound, or
the lower-to-upper interval when optimality is unresolved. `gap` is the
first-fit-decreasing bin count minus that feasible upper bound. Use this column
to compare the two constructions; use the task checker for final scoring and
an optimality certificate to establish an optimum.

To inspect a prepared filesystem without building a complete image, use
`tcsexam resources`:

```bash
tcsexam resources --resource bpplib-development --cache /path/to/resource-cache
tcsexam resources --resource qbf-public --cache /path/to/resource-cache
```

The QBF resource command also accepts the declared official archive through
`--input source_archive=PATH`, or a hash-checked intermediate through
`--input frozen_input=PATH`. Recipe declarations list all supported input names.
Build and source-maintenance procedures are in [CONTRIBUTING](../.github/CONTRIBUTING.md).

## Use an external image manifest

An external `artifacts.json` can select existing images instead of the default
acquisition routes. It supplies immutable image references, platform, content
identity and task-role assignments. Keep registry credentials outside the
manifest. A task-image fragment looks like this:

```json
{
  "images": [{
    "id": "example-development",
    "image": "registry.example/tcsexam@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "platform": "linux/amd64"
  }],
  "tasks": {
    "tasks/theorem/dijkstra-universal": {"development": "example-development"}
  }
}
```

Supply actual image records for every required role, including `verifier` or
online `backend`, and the selected `type: host_support` records for the Harbor
helper and fixed kernel probe. The fragment above shows only a development-image
assignment. `--image-map` can override task-role assignments while `--artifacts`
supplies host support.

```bash
tcsexam setup --suite full --task dijkstra-universal \
  --artifacts /path/to/artifacts.json --output build/setup.json
tcsexam doctor --suite full --task dijkstra-universal \
  --artifacts /path/to/artifacts.json --output build/readiness.json
```

`setup` validates the selection, pulls missing images, checks digest and platform,
and records availability in the cache. It also assigns Harbor support images
the names expected by Harbor 0.22.0. The helper must match the installed Harbor
package context, including file permissions. An unknown context requires a
matching helper before acquisition can proceed.

`--pull-policy never` requires local images; `always` rechecks registry
acquisition. `--docker-context NAME` selects a local Unix-socket context on the
Linux host running the CLI and Harbor, with shared task and job paths. Remote
SSH/TCP contexts are rejected. Online backend images must also be available on
the backend host. See [running evaluations](running.md) for readiness checks.

## Sharing prepared products

Follow each resource's [distribution conditions](licenses/distribution.md).
BPPLIB generated files and all containing images are local-only products.
QBF includes three BMC instances with additional non-commercial teaching and
research terms. A containing image retains every input's restrictions,
including files in inherited layers. Source export is documented in
[CONTRIBUTING](../.github/CONTRIBUTING.md).
