# TCSExam

[![Website](assets/badges/website.svg)](https://moonshotai.github.io/TCSExam/)
[![arXiv](assets/badges/arxiv.svg)](https://arxiv.org/abs/2611.07962)
[![Documentation](assets/badges/docs.svg)](https://moonshotai.github.io/TCSExam/docs/)
[![License](assets/badges/license.svg)](docs/licenses/README.md)

Language: [English](README.md) | [简体中文](docs/README.zh-CN.md)

TCSExam evaluates model–agent systems on verifiable theoretical computer science research tasks.
This repository is for researchers inspecting tasks, running evaluations, and comparing verified results.

Choose a reading path from the [documentation home](docs/index.md). For your
first evaluation, follow [Run TCSExam from scratch](docs/getting-started.md).
For an existing setup, use [Run configuration and parameters](docs/running.md).

## Tasks

Full contains 100 tasks. Lite selects 20 from Full, with five from each task
category. The table shows the number of tasks in each suite; every Solver task
provides separate Online and Offline packages.

| Suite | Theorem proving | Solver engineering | Constructions | Open conjectures | Total |
|---|---:|---:|---:|---:|---:|
| Full | 20 | 30 | 20 | 30 | **100** |
| Lite | 5 | 5 | 5 | 5 | **20** |

Theorem tasks ask for a Lean proof of a published result. Solver tasks ask for
an algorithm implementation evaluated on hidden instances. Construction tasks
ask for a verified construction or bound. Open-conjecture tasks accept a
complete Lean proof or refutation of the stated conjecture. See the
[task catalogue](docs/tasks.md) for task-level statements and sources.

Full defaults to Online Solver, which provides judging feedback during
model development. Lite defaults to Offline Solver, which provides public
self-tests during development and hidden judging afterward. Both suites support
both protocols through `--solver-protocol`; report their results separately.
[Solver protocols](docs/solver-protocols.md) defines the feedback and network rules.

## Run an evaluation

Use a Linux x86-64 host, Python 3.12+, Docker Engine with Compose and Buildx,
and a model API account. The runtime dependency installs Harbor 0.22.0, which
runs the agents and collects their outputs. Solver judging additionally requires
Landlock ABI 3 or later and the required container syscall permissions. Online
Solver uses a judging backend; Offline Solver runs its controller on the Docker
host. See [runtime requirements](docs/runtime-availability.md) for host sizing.

The [getting-started guide](docs/getting-started.md) takes you through cloning,
installation, a single `discrete-bidding-games` task, Lite, Full, and reading the
actual result files. It uses Kimi Code by default. Claude Code, Codex and Grok
Build are also supported; [agent configuration](docs/running.md#choose-an-agent)
provides their settings and commands.

Use [Run configuration and parameters](docs/running.md) for task selection, budgets,
credentials and saved jobs; [resource preparation](docs/resources.md) for inputs
and image builds; and the [Docker backend guide](docs/backend/docker.md) for
Online Solver service deployment. Source-package contents and build entry points
are described in [source packages](docs/source-delivery.md).

## Scores

```text
TCSExam Index = 30 × theorem success
             + 30 × fixed-K3-relative Solver score
             + 30 × original Construction score
             + 10 × complete Open-conjecture success
```

Average adopted attempts within each task, then average tasks equally within
each track. Report all four track scores alongside the Index. Construction
scores may exceed one, so the Index is measured in points and may exceed 100.
Failed or missing judging remains distinct from a completed zero score.
[Scoring](docs/scoring.md) defines the formulas, fixed Solver reference and input
formats for `tcsexam solver-score` and `tcsexam score`.

<a id="license-and-citation"></a>

## Licensing and third-party attribution

Project-authored code, checkers, scripts and build configuration use
[Apache-2.0](LICENSE). Original task statements, documentation and website
content use [CC BY 4.0](docs/licenses/CC-BY-4.0.txt). The [paper PDF](paper.pdf)
is licensed separately under [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/).
Third-party materials retain
their own terms; preserve their task-level sources and
[notices](docs/licenses/THIRD_PARTY_NOTICES.md). Consult the
[license guide](docs/licenses/README.md) before redistributing inputs or images.

For attribution, licensing or material-use concerns, open a repository Issue; the
[corrections process](docs/licenses/README.md#rights-and-corrections)
describes the process. Development and source-export instructions are in
[CONTRIBUTING.md](.github/CONTRIBUTING.md).

<a id="citation"></a>

## Cite TCSExam

If you use TCSExam in your research, please cite the [paper](https://arxiv.org/abs/2611.07962). [Export BibTeX](https://arxiv.org/bibtex/2611.07962) · [Download PDF](paper.pdf).

```bibtex
@misc{luo2026tcsexamevaluatingfrontierllms,
  title={TCSExam: Evaluating Frontier LLMs on the Full Range of TCS Research},
  author={Yifan Luo and Zhengying Liu and Yang Yuan and Zhilin Yang and Andrew Chi-Chih Yao},
  year={2026},
  eprint={2611.07962},
  archivePrefix={arXiv},
  primaryClass={cs.AI},
  url={https://arxiv.org/abs/2611.07962},
}
```
