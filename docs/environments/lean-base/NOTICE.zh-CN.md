<a id="third-party-notices-for-the-lean-environment"></a>

# Lean 环境第三方声明

[English](../../../assets/environments/lean-base/NOTICE.md) | [简体中文](NOTICE.zh-CN.md)

中文译文供参考，许可条款以原文为准。

这里是安装在 `/usr/share/doc/tcsexam/` 下的组件许可和源码材料入口。

- [mathlib 和 Lake 组件许可证](lean-components/README.zh-CN.md)：九份组件各自的许可文本、固定提交、公开源码位置，以及独立 NOTICE 的搜索结果，安装在 `/usr/share/doc/tcsexam/lean-components/`。
- [Graphviz EPL-2.0 材料](graphviz-epl/README.zh-CN.md)：Graphviz 许可证、对应源码提供声明、完整源码归档、封装层修改、构建规则、官方源码 URL 和已验证哈希值，安装在 `/usr/share/doc/tcsexam/graphviz-epl/`。
- [浏览器内嵌组件材料](browser-components/README.zh-CN.md)：Expat、Emscripten 运行时声明，以及 Penrose 优化器与其精确 Cargo.lock 对应的声明全集，包含代码内容及链接范围，安装在 `/usr/share/doc/tcsexam/browser-components/`。
- [ProofWidgets 固定 npm 材料](proofwidgets-npm/README.zh-CN.md)：全部 387 个固定锁文件依赖，附各包来源元数据、364 份原始声明、44 份补充声明、六份复用的 cliui 随包声明，以及一份明确标记的 SPDX 标准文本，安装在 `/usr/share/doc/tcsexam/proofwidgets-npm/`。

ProofWidgets 浏览器代码包含 Graphviz 15.0.0。Graphviz 使用 Eclipse Public License 2.0（EPL-2.0）。`@hpcc-js/wasm` 封装层单独采用 Apache-2.0；该封装层许可不适用于 Graphviz。

浏览器和 npm 目录保留声明及精确源码位置，清单中的构建依赖或锁文件依赖不全部视为已链接的代码。镜像内其他软件保留各自的许可和声明要求。分发包含这些组件的镜像时，应保留对应源码与声明；依赖清单没有断言每项构建依赖都链接到了最终代码中。
