<a id="mathlib-and-lake-component-licenses"></a>

# mathlib 和 Lake 组件许可证

[English](../../../../assets/environments/lean-base/lean-components/README.md) | [简体中文](README.zh-CN.md)

中文译文供参考，许可条款以原文为准。

各组件均有独立的 `LICENSE` 和 `source.json`。即使多个上游项目的 Apache-2.0 许可文本逐字节相同，组件各自的文件仍保留其署名。只有找到独立上游 NOTICE 的文件，才会在此作为该组件专属的 NOTICE 提供。

固定源码树和文件级版权头保留在 `/opt/lean-lib/mathlib4/` 及其 `.lake/packages/` 目录下。`source.json` 给出各组件的公开仓库、完整提交、源码归档、固定许可 URL，以及递归 NOTICE 搜索结果。

对固定提交的 Git 树递归搜索后，这九个组件均未发现独立的 NOTICE 或 COPYRIGHT 文件。mathlib 和 batteries 各自只有 `.vscode/copyright.code-snippets` 编辑器模板；这些模板记录在各自的 `source.json` 中，不作为独立声明。

读法说明：每行给出一个组件的许可、固定提交、公开来源和安装材料。

| 组件 | 许可 | 固定提交 | 公开源码 | 已安装材料 |
|---|---|---|---|---|
| mathlib | Apache-2.0 | `5b3f719bf129e3cf48daf6ff76a2ec5cb6e9b1e3` | https://github.com/leanprover-community/mathlib4 | `mathlib/LICENSE`, `mathlib/source.json` |
| plausible | Apache-2.0 | `b1c4a69a7e247ab7df20460212001673d74f08c0` | https://github.com/leanprover-community/plausible | `plausible/LICENSE`, `plausible/source.json` |
| LeanSearchClient | Apache-2.0 | `0498c7c070c143a3bf7379f4d99a2c63bb9d9715` | https://github.com/leanprover-community/LeanSearchClient | `LeanSearchClient/LICENSE`, `LeanSearchClient/source.json` |
| importGraph | Apache-2.0 | `18a90119a5d316358fde6c86e0ca24e59212e32c` | https://github.com/leanprover-community/import-graph | `importGraph/LICENSE`, `importGraph/source.json` |
| proofwidgets | Apache-2.0 | `b1436dc749e722c9920036b52cdc43b3451d0b69` | https://github.com/leanprover-community/ProofWidgets4 | `proofwidgets/LICENSE`, `proofwidgets/source.json` |
| aesop | Apache-2.0 | `57d3325be72a842920813bcb40f96a6f7393c185` | https://github.com/leanprover-community/aesop | `aesop/LICENSE`, `aesop/source.json` |
| Qq | Apache-2.0 | `ee41917ae11d38479fb8fb24745f7ca4bf0a784d` | https://github.com/leanprover-community/quote4 | `Qq/LICENSE`, `Qq/source.json` |
| batteries | Apache-2.0 | `d60e6444e6fd881dfa077ff36e96de75753afa28` | https://github.com/leanprover-community/batteries | `batteries/LICENSE`, `batteries/source.json` |
| Cli | MIT | `da07ca808b6718cb2aed14dba154e5a08b8f8ecf` | https://github.com/leanprover/lean4-cli | `Cli/LICENSE`, `Cli/source.json` |

这些材料提供许可和源码位置，不表示已经下载每份固定源码归档，也不表示已经完成整个镜像的许可审查。
