<a id="solver-protocols"></a>

# Solver 协议

[English](solver-protocols.md) | [简体中文](solver-protocols.zh-CN.md)

本指南定义 Solver 开发期间的反馈方式和协议选择方法。
面向选择评测协议或准备相关依赖的用户。

<a id="feedback-and-defaults"></a>

## 反馈与默认设置

Full 包含 100 道题；Lite 从 Full 的各类题目中选取 20 道。在任一套件中，
`--solver-protocol online|offline` 用于选择 Solver 开发期间的反馈协议。
两种选择下，定理、构造和开放猜想题均共用相同目录。Full 默认使用 `online`；
Lite 默认使用 `offline`。两个套件都允许显式覆盖默认值。

读法说明：每行描述一套完整的开发与终判协议。

| 协议 | 十二小时开发期间 | 开发结束后 |
|---|---|---|
| `online` | `submit.sh` 可以请求判分并返回反馈 | 在隐藏实例上评判最终提交 |
| `offline` | 在公开实例上运行本地自测 | 在隐藏实例上评判最终提交 |

Offline 在开发期间不提供隐藏判分反馈。两种协议使用相同的最终题目检查器和计分规则。

互联网访问是独立的题目设置：允许的网络使用范围以题目配置和说明为准。

<a id="select-and-prepare-a-protocol"></a>

## 选择并准备协议

全部三十道 Solver 题目均提供 online 和 offline 题包。
[题目注册表](../suites/tasks.json) 将题目映射到对应的 Harbor 目录。
套件选择和协议选择会解析这些目录，不改变题目内容。

```bash
tcsexam list --suite lite --track solver --solver-protocol offline
tcsexam list --suite full --track solver --solver-protocol online
```

用 [`tcsexam build`](resources.zh-CN.md) 准备选定镜像，然后以相同选项运行
`tcsexam doctor`。缺少依赖时，`run` 会在发出任何模型请求之前停止；缺少某个变体会报错。

Online 还需要用户自行运营判分后端。题包提供客户端和判分代码；
[TCSEXAM 接口](solver-backend.zh-CN.md) 定义身份认证、会话、尝试标识和结果归档。

Offline 在开发结束后使用独立的判分适配器。适配器根据可用 CPU 和内存选择并发数，
资源不足时可退回串行执行，同时保留逐实例限额。共享时间池题目仍使用同一个时间池。
模型环境与隐藏数据和 Docker 控制器隔离。适配器行为见
[离线适配器](offline-adapters.zh-CN.md)。

<a id="report-the-selected-protocol"></a>

## 报告所选协议

online 和 offline 结果应分别形成独立系列，即使它们选择了相同题目。
记录实际使用的协议，以及套件、源码提交、模型和 agent 版本、计分依据及采用的尝试次数。
参见[报告字段](citation.zh-CN.md#citing-results)。
