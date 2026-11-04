<a id="graphviz-1500-epl-20-materials"></a>

# Graphviz 15.0.0 EPL-2.0 材料

[English](../../../../assets/environments/lean-base/graphviz-epl/README.md) | [简体中文](README.zh-CN.md)

中文译文供参考，许可条款以原文为准。

ProofWidgets 提交 `b1436dc749e722c9920036b52cdc43b3451d0b69` 提供 Lean 镜像内生成的浏览器文件。这些文件以 WebAssembly 形式嵌入 Graphviz 15.0.0，其 SHA-256 为 `b73447cdf82c85bc61be2ebb78f1ac17a70fb7567c9f739268d7542e88cc421c`。

Graphviz 使用 EPL-2.0。`@hpcc-js/wasm` 2.34.2 封装层单独采用 Apache-2.0。封装层许可不覆盖 Graphviz。

先阅读 [SOURCE-OFFER.md](SOURCE-OFFER.zh-CN.md)，了解对应源码声明、已验证的归档哈希值、官方源码 URL 和重建路径。完整 Graphviz 和封装层及构建源码归档随镜像保存在 `source/` 中；获取这些源码材料无需网络访问。

内容：

- `EPL-2.0.txt`：从已验证的 Graphviz 归档中提取的 Graphviz 许可证。
- `WRAPPER-APACHE-2.0.txt`：从已验证的封装层归档中提取的封装层许可证。
- [`SOURCE-OFFER.md`](SOURCE-OFFER.zh-CN.md)：如何获取和检查对应源码。
- `source-manifest.json`：机器可读的版本、URL、字节数和哈希值。
- `source/`：Graphviz 15.0.0 和 `hpcc-js-wasm` 提交 `8b86e2f83cc7344aca44fb3d8aa29a227358c5c4` 的完整固定源码归档。
- `build-rules/`：同一封装层归档中构建规则、Graphviz 封装层 C++ 源码和 Graphviz overlay 修改的可读副本。
- `SHA256SUMS`：除校验和文件自身外，已安装文件的哈希值。

这些材料随生成的 Graphviz JavaScript 和 WebAssembly 一并提供。其他浏览器依赖的来源和声明见单独的浏览器组件及 npm 清单。
