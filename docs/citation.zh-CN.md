<a id="citation-and-attribution"></a>

# 引用与署名

[English](citation.md) | [简体中文](citation.zh-CN.md)

在研究中使用 TCSExam 时，请引用以下论文。
下方同时说明报告评测结果和复用题目材料时应提供的信息。

<a class="docs-paper-link" href="https://arxiv.org/abs/2611.07962" target="_blank" rel="noopener">阅读论文</a>

[导出 BibTeX](https://arxiv.org/bibtex/2611.07962)

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

<a id="citing-results"></a>

## 引用结果

软件名称写作 **TCSExam**，并注明仓库提交或发布版本及获取日期。

报告评测结果时，一并提供以下信息：

- 任务套件：Full 或 Lite，以及明确选取的任务子集。
- 源码提交或发布版本，以及所选镜像标识。
- 模型及服务商版本、智能体版本、配置和开发预算。
- Solver 协议：`online` 或 `offline`，以及自定义后端配置。
- 计划和采用的重复次数、采用规则及不完整结果。
- Solver 固定参照标识符、综合指数指标标识符、四个题型平均分及综合指数点数。

不同任务套件和 Solver 协议应标为不同的结果系列。保留原始判分奖励、最终实例记录和计分输出，使读者能够重新计算报告的分数。参见[运行评测](running.zh-CN.md)和[计分](scoring.zh-CN.md)。

<a id="attribution-for-reused-material"></a>

## 复用材料的署名

保留对原论文、竞赛、数据集和软件的署名，包括许可声明和修改说明。[第三方声明](licenses/THIRD_PARTY_NOTICES.zh-CN.md)列出了组件来源及必须保留的声明。

共享已准备的数据、二进制文件或镜像前，请查看相应材料的[分发条件](licenses/distribution.zh-CN.md)及[组件记录](licenses/full-review.zh-CN.md)。源码包与准备完成的产物包含不同内容，许可要求也有所不同。
