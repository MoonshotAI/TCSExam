<a id="graphviz-corresponding-source-offer"></a>

# Graphviz 对应源码提供声明

[English](../../../../assets/environments/lean-base/graphviz-epl/SOURCE-OFFER.md) | [简体中文](SOURCE-OFFER.zh-CN.md)

中文译文供参考，许可条款以原文为准。

ProofWidgets 浏览器代码中嵌入的 Graphviz 15.0.0 程序以 EPL-2.0 提供。Graphviz 完整对应源码、固定封装层源码、封装层对 Graphviz 的修改和构建规则随镜像保存在 `/usr/share/doc/tcsexam/graphviz-epl/` 下。接收者可直接从该目录获取这些源码材料，无需网络访问。

<a id="complete-source-archives"></a>

## 完整源码归档

读法说明：每行列出一个组件的安装归档、官方来源、大小和已验证哈希值。

| 组件 | 已安装归档 | 官方来源 | 字节数 | 已验证 SHA-256 |
|---|---|---|---:|---|
| Graphviz 15.0.0 | `source/graphviz-15.0.0.tar.gz` | https://gitlab.com/graphviz/graphviz/-/archive/15.0.0/graphviz-15.0.0.tar.gz | 41113527 | `dfa5be5c311f760aa9c88273c8f8101bb11f50b0de8b29bbd54acff3adc2d563` |
| `hpcc-js-wasm` 提交 `8b86e2f83cc7344aca44fb3d8aa29a227358c5c4` | `source/hpcc-js-wasm-8b86e2f83cc7344aca44fb3d8aa29a227358c5c4.tar.gz` | https://github.com/hpcc-systems/hpcc-js-wasm/archive/8b86e2f83cc7344aca44fb3d8aa29a227358c5c4.tar.gz | 455080 | `5443207dda2c30581e0632c8add206fcae3906f5faf20d4a0808499934743ee6` |

Graphviz 归档的 SHA-512 为 `d69e2dd7b5127650b6e09de92508a84886d52d5dfd1eacf9e6abb797ca231db3c1b12546c7b8561e311150cd62be8dfea689021b7d139ffcdb3d4e16da670352`，与封装层 `vcpkg-overlays/graphviz/portfile.cmake` 中固定的值完全一致。封装层归档的 SHA-512 为 `1a195429ba1d9d47803a78fc700c601ffcbd340d42b3c753f0f2a77cec4782768844b658227543bad7597ea5af553590c401a25ccc1aefea31a6b04f19e16a63`。

源码准备命令根据声明的大小和哈希值验证完整归档。Graphviz 中的 `LICENSE` 文件安装为 `EPL-2.0.txt`；封装层中的 `LICENSE` 文件安装为 `WRAPPER-APACHE-2.0.txt`。

<a id="modifications-and-build-rules"></a>

## 修改与构建规则

封装层归档是 `@hpcc-js/wasm` 2.34.2 的固定源码。npm 版本元数据将提交 `8b86e2f83cc7344aca44fb3d8aa29a227358c5c4` 标为其 `gitHead`。

封装层的 `vcpkg-overlays/graphviz/portfile.cmake` 使用 overlay 内的文件替换 Graphviz 顶层的 `CMakeLists.txt` 和 `cmake/config_checks.cmake`。它还替换该 portfile 中说明的 `GVPLUGIN_CURRENT` 和 `GVPLUGIN_REVISION` 替换项。具体文件既保存在封装层归档中，也以可读副本形式保存在 `build-rules/vcpkg-overlays/graphviz/` 下。

封装层 C++ 入口和支持源码位于 `build-rules/packages/graphviz/src-cpp/`。封装层构建文件选择 Emscripten SDK 6.0.0 和 vcpkg 2026.06.01。它们的官方项目位置为：

- https://github.com/emscripten-core/emsdk
- https://github.com/microsoft/vcpkg

从源码重建时，将封装层归档解压到可写目录，并遵循 `build-rules/README.md`。该固定源码记录的主要命令为 `npm ci`、`npm run install-build-deps` 和 `npm run build`。完整归档包含构建脚本和预设。安装指定构建工具，并在这组 Graphviz 专用归档旁一并保留这些工具适用的源码及许可材料。

<a id="verification"></a>

## 验证

从安装目录运行：

```bash
cd /usr/share/doc/tcsexam/graphviz-epl
sha256sum -c SHA256SUMS
```

`source-manifest.json` 以机器可读形式记录相同的版本、官方 URL、归档大小和哈希值。镜像中其他组件的源码和声明见单独的浏览器组件及 npm 清单。
