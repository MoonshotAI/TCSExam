<a id="browser-nested-component-materials"></a>

# 浏览器内嵌组件材料

[English](../../../../assets/environments/lean-base/browser-components/README.md) | [简体中文](README.zh-CN.md)

中文译文供参考，许可条款以原文为准。

本目录提供 Expat、Emscripten 运行时组件，以及 Penrose 优化器和其固定 Cargo.lock 中 registry crate 的源码位置与声明。供检查或再分发 Lean 镜像浏览器组件的用户阅读。

记录同时标明已链接组件和构建依赖。再分发时，应结合组件记录、镜像实际内容，以及 `graphviz-epl/` 中单独保存的 Graphviz 源码材料。

## Expat

`expat/LICENSE` 和 `expat/source.json` 保留 Expat 2.8.1 的 MIT 文本和源码位置。固定的 vcpkg port 选择此版本；Graphviz 代码包含链接后的 Expat 组件。

## Emscripten

`emscripten/notices/` 包含固定构建输入中的 Emscripten 6.0.0 许可证、musl COPYRIGHT 和 libc++ LICENSE.TXT。分发生成的 WebAssembly 时，应保留适用的运行时声明；组件记录覆盖构建输入，未指定实际链接的运行时子集。

<a id="penrose-optimizer"></a>

## Penrose 优化器

`penrose-optimizer/LICENSE` 保留 Penrose MIT 声明。`penrose-optimizer/build/` 包含固定 Cargo 元数据。`penrose-optimizer/crates/` 包含 46 个 crate 各自的目录，提供精确源码 URL、归档哈希值、许可声明、77 份原始声明文件和 6 份补充项目声明。

这 46 个 crate 覆盖完整 Cargo.lock，包括构建依赖、宿主机依赖和仅用于 Windows 的依赖。来源记录标明这些用途。补充声明与 crate 归档中随附的声明分别标记。

<a id="obtain-sources-and-retain-notices"></a>

## 获取源码并保留声明

使用每个组件记录中的精确公开 URL 和哈希值获取源码归档。本目录保存源码元数据和声明。分发二进制文件或对应源码时，遵循各组件许可。

固定的 ProofWidgets npm 依赖集记录于 `proofwidgets-npm/`。应包含镜像内全部组件适用的源码材料和声明。
