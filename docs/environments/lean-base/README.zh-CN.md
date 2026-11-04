<a id="lean-task-environment"></a>

# Lean 任务环境

[English](../../../assets/environments/lean-base/README.md) | [简体中文](README.zh-CN.md)

本指南说明共用 Lean 环境的构建和使用方法。

环境面向 Linux `amd64`。执行任务时安装 Harbor `0.22.0`。Lean 使用 `leanprover/lean4:v4.33.0-rc1`；mathlib 固定在提交 `5b3f719bf129e3cf48daf6ff76a2ec5cb6e9b1e3`，安装路径为 `/opt/lean-lib/mathlib4`。Elan 选择 Lean 工具链，Lake 管理其依赖。固定的传递依赖列于 `mathlib-lake-manifest.json`。

从仓库根目录准备固定的公开源码归档，并构建所选任务：

```bash
tcsexam source-inputs
tcsexam build --suite lite --track theorem
tcsexam doctor --suite lite --track theorem
```

`source-inputs` 将 `graphviz-epl/source-manifest.json` 中声明的 Graphviz 和封装层归档放入构建上下文前，会先验证它们。如果上游下载不可用，可按照[资源指南](../../resources.zh-CN.md#prepare-fixed-lean-source-archives)中显式导入的方法，提供内容完全一致的本地归档。源码准备不会编译 Lean，也不会构建 Docker 镜像。

使用整个目录作为基础镜像的构建上下文。Dockerfile 固定了 Ubuntu 镜像、Elan 归档和 mathlib 提交。构建时获取依赖需要网络访问；获取失败会停止构建。构建期间使用宿主机网络不会改变所选任务运行时的网络策略。本地产物与历史镜像记录使用不同的标识。

为镜像层、编译后的库、任务构建和日志预留至少 40 GB 磁盘空间。Lean 任务使用 4 个 CPU 核和 16 GB 内存；存储与编译限制请查看所选 `task.toml`。开发预算为十二小时（43,200 秒）。环境构建、智能体安装和终判各有单独预算。外部运行超时倍率保持为 `1`。

基础镜像允许非 root 用户读取编译后的 mathlib 文件。每个开发镜像仅复制本任务的 `environment/app/`，并执行任务声明的安装步骤。在新项目中调用 Lean 前，应先完成安装，使 Lake 能够解析固定的依赖配置。运行时网络连通性遵循各任务配置。

<a id="running-and-judging"></a>

## 运行与判分

保留 Harbor 原生任务入口。参见 [Harbor 任务文档](https://docs.harborframework.com/tasks/overview)和仓库[运行指南](../../running.zh-CN.md)。以下命令可以生成配置，无需调用模型或编译 Lean：

```bash
tcsexam prepare --suite lite --track theorem \
  --base-url https://YOUR_PROVIDER.example/v1 --output build/theorem.json
python -m tcsexam.harbor_launch run --config build/theorem.json --print-config
```

独立判分器使用同一任务的开发镜像和原始 `tests/` 文件。开发构建上下文排除 `tests/`、`solution/` 和历史完整证明。这些材料应保存在模型解题环境之外。

保留任务的参考陈述、可编辑范围、公理检查和计分文件。定理任务使用其声明的标准公理；构造任务使用 `judge.json` 中列出的计算公理。开放猜想任务分别判定两个主要陈述。每次提交均受编译和判分限制约束。

运行 `tcsexam validate` 执行仓库静态检查。该命令不会编译 Lean。更改任务清单后，使用 `PYTHONPATH=src python -m tcsexam.lean_recipes` 重新生成声明，或加上 `--check` 检查是否存在未更新字段。

<a id="source-and-license-materials"></a>

## 源码与许可材料

Dockerfile 将 [`NOTICE.md`](NOTICE.zh-CN.md) 安装到 `/usr/share/doc/tcsexam/README.md`，并分别保留以下材料：

- [`lean-components/`](lean-components/README.zh-CN.md)：固定的 Lake 组件提交及原始许可证。
- [`graphviz-epl/`](graphviz-epl/README.zh-CN.md)：Graphviz EPL-2.0 文本、源码提供声明、固定源码归档、封装层修改和构建规则。
- [`browser-components/`](browser-components/README.zh-CN.md)：Expat、Emscripten 和 Penrose 声明，以及所说明的依赖范围。
- [`proofwidgets-npm/`](proofwidgets-npm/README.zh-CN.md)：固定 npm 依赖的来源记录，以及原始或明确标识的补充许可证。

重建镜像时，保留材料路径及其校验和检查。各依赖继续适用自身条款；项目许可不会替代第三方许可。依赖清单可能包含仅供构建使用的组件，列入清单不代表每个组件都链接到了浏览器代码中。参见[分发指南](../../licenses/distribution.zh-CN.md)。

任务来源记录于 `assets/sources.json`，共用依赖固定版本记录于 `pins.json`，资源准备要求见[资源指南](../../resources.zh-CN.md)。`tcsexam doctor` 分别报告本地镜像可用性和运行环境的接受情况。
