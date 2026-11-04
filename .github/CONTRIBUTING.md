# Contributing to TCSExam

Language: [English](CONTRIBUTING.md) | [简体中文](CONTRIBUTING.zh-CN.md)

Contribute research tasks, report corrections, or improve code and documentation.
This guide is for researchers and developers helping improve TCSExam.

## Suggest a task or correction

[Open a GitHub issue](https://github.com/MoonshotAI/TCSExam/issues) to propose a research problem or report a task issue. Include the problem statement, its source, the relevant track, and how a submission could be checked. For a construction task, include the reference bound and its source.

For a correction, identify the task and show a concrete example of the problem. If you have an implementation, submit a pull request with the task statement, verification code, and scoring rule. The development instructions below describe the checks to run.

## Set up a development checkout

Use Python 3.12 or later and install the runtime, backend and test dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[runtime,backend]' pytest
tcsexam source-inputs
```

`source-inputs` prepares the pinned source archives used by the Lean build
recipes and material tests. For an unavailable upstream download, use the
[verified local import](../docs/resources.md#prepare-fixed-lean-source-archives).

## Check a change

```bash
tcsexam validate
python -m tcsexam.recipes --check
python -m pytest src/tcsexam/backend/tests src/tcsexam/tests -q
tcsexam check-public --phase source --output build/source-check.json
git diff --check
```

`validate` checks task structure, suite membership, executable scripts and source
identities. The test suite covers command configuration, data recipes, scoring,
backend behavior and documentation links. `check-public --phase source` checks
the files intended for source distribution, including internal references and
distribution rules. Resolve reported errors before exporting.

For runtime changes, also exercise the affected command or judge with representative
inputs. Use the [judge image preflight](../docs/judge-execution-isolation.md) for
execution-isolation changes and the [adapter contract checks](../docs/backend/service.md#writing-a-platform-adapter)
for a platform adapter. Preserve task inputs, scoring definitions and declared
resource budgets when changing packaging.

Keep generated images, downloaded datasets and evaluation outputs in the configured
cache or output directory. Build recipes belong under `assets/`; task definitions
belong under `tasks/` and are selected through `suites/tasks.json`.

## Write public documentation

Organize guides around a reader's task: prerequisites, commands, expected outputs
and troubleshooting. Define each configuration option, input procedure and score
in one reference page, then link to it from other guides. Keep English and Chinese
guides consistent in commands, defaults and behavior.

Markdown files under `docs/` are the source for both repository reading and the
documentation website. When adding or moving a guide, update the
[documentation home](../docs/index.md) and the corresponding Chinese navigation.
Language links should lead to the same content in the other language; keep
reading-path links separate.

Document limitations where they affect an operation, with the required condition
and the action the reader should take. Keep delivery reports, internal reviews,
development diaries, execution logs and private infrastructure details outside
the source repository. Preserve upstream attribution, license texts, source URLs,
fixed versions and content hashes.

Use relative links for pages and files within this repository. The public
repository address is maintained in `project.urls.Repository` in `pyproject.toml`.
To change it and update both getting-started guides, run
`python -m tcsexam.project_links --repository-url https://github.com/OWNER/REPOSITORY`.
Run `python -m tcsexam.project_links --check` to check consistency.

The default branch contains evaluation code, Markdown guides and `paper.pdf`.
Website source lives in the [website directory on `gh-pages`](https://github.com/MoonshotAI/TCSExam/tree/gh-pages/website).
Its documentation renderer reads the Markdown guides from this branch.

## Export a source package

Use a clean checkout of the intended release commit. From the repository root:

```bash
tcsexam export --normalize-modes --output build/tcsexam-source
tcsexam validate --root build/tcsexam-source
tcsexam check-public --root build/tcsexam-source --phase source
```

The destination must be new or empty. A destination inside the checkout must be
under `build/`. The exporter applies the distribution records and omits Git
metadata, caches, job outputs, credentials, reference-answer payloads and declared
local-only inputs. The exported tree contains the recipes and acquisition
instructions needed to prepare its environments. In the exported checkout, run
`tcsexam source-inputs` before Lean builds or material tests.

Create public repositories and release archives from the exported directory.
Keep the source commit, export manifest and check results with the release
records so the published files can be traced to their source. The source
checkout can contain reference answers and excluded inputs; publish the
exported files with a fresh Git history.

`--normalize-modes` writes regular files as 0644, executable files as 0755 and
directories as 0755 while preserving file contents and executable status.
Without this option, export preserves source file modes.

Image distribution has its own [component requirements](../docs/licenses/distribution.md).
Use `tcsexam check-public --phase release` when preparing a distribution that
includes published images; that check includes image addresses and anonymous
pull access.

## Extend the backend or task resources

- [Platform adapter contract](../docs/backend/service.md#writing-a-platform-adapter):
  worker creation, file transfer, execution, resource accounting and cleanup.
- [Backend HTTP protocol](../docs/solver-backend.md): client requests, credentials,
  session state and submission handling.
- [Resource inventories](../assets/README.md): image dependencies, source inputs and
  distribution records.
- [Public self-test images](../docs/backend/public-images.md): separate public data
  from hidden judging data in every image layer.
- [Reference-answer archives](../docs/oracle-answers.md): package separately supplied
  answers for operator use.
