# Citation and attribution

[English](citation.md) | [简体中文](citation.zh-CN.md)

Cite the paper when using TCSExam in your research.
The guidance below also covers reporting evaluations and reusing task materials.

<a class="docs-paper-link" href="https://moonshotai.github.io/TCSExam/paper/tcsexam.pdf" target="_blank" rel="noopener">Read the paper</a>

```bibtex
@misc{tcsexam2026,
  title = {{TCSExam}: Evaluating frontier {LLMs} on the full range of {TCS} research},
  author = {Luo, Yifan and Liu, Zhengying and Yuan, Yang and Yang, Zhilin and Yao, Andrew Chi-Chih},
  year = {2026},
  month = nov,
  url = {https://github.com/MoonshotAI/TCSExam}
}
```

## Citing results

Identify the software as **TCSExam**, with its repository commit or release
version and acquisition date.

Report the following with evaluation results:

- Suite: Full or Lite, plus any explicit task subset.
- Source commit or release and the selected image identities.
- Model/provider version, agent version, configuration and development budget.
- Solver protocol: `online` or `offline`, including any custom backend setup.
- Planned and adopted repetitions, adoption policy and incomplete results.
- Fixed Solver reference ID, Index metric ID, four track means and Index points.

Label separate suites and Solver protocols as separate result series. Keep raw
checker rewards, final instance records and scoring outputs so readers can
recalculate the reported scores. See [running evaluations](running.md) and
[scoring](scoring.md).

## Attribution for reused material

Retain attribution to the underlying papers, competitions, datasets and
software, including license notices and statements of modifications. Component
sources and required notices are listed in [third-party notices](licenses/THIRD_PARTY_NOTICES.md).

Before sharing prepared data, binaries or images, consult the material-specific
[distribution conditions](licenses/distribution.md) and
[component records](licenses/full-review.md). Source packages and prepared
products have distinct contents and licensing requirements.
