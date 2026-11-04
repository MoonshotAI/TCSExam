<a id="reference-answer-archives"></a>

# 参考答案归档

[English](oracle-answers.md) | [简体中文](oracle-answers.zh-CN.md)

本指南说明如何打包和验证另行提供的参考答案。
供已持有答案及其来源规格的运行维护人员阅读。

参考答案归档用于使用另行提供的答案进行运行检查。将归档及其输入规格放在公开工作副本之外，或被排除的 `build/` 目录内，与模型开发环境分开。归档只能包含其声明的答案和元数据。普通模型评测请遵循[快速开始指南](getting-started.zh-CN.md)。

<a id="create-and-verify"></a>

## 创建与验证

`tcsexam.oracle_package` 创建确定性的 tar 归档，包含任务及变体覆盖范围、Git 来源、各文件哈希值、`SHA256SUMS` 和范围说明。归档自身的 SHA-256 写入相邻的 `.sha256` 文件。

```bash
python -m tcsexam.oracle_package create \
  --spec /path/to/answer-specification.json \
  --output /path/to/answer-archives/answers-VERSION.tar.gz \
  --report /path/to/answer-archives/create-report.json

python -m tcsexam.oracle_package verify \
  --package /path/to/answer-archives/answers-VERSION.tar.gz \
  --destination /path/to/new-verification-directory \
  --authority-spec /path/to/answer-specification.json
```

验证使用新目录，只接受普通文件，并拒绝缺失、多余或超出范围的内容。它会检查哈希值和清单总数，也可以重新核对权威来源的 Git blob。要检查答案能否被接受，需要另外通过对应任务的判分器执行答案。

<a id="publish-an-authorized-archive"></a>

## 发布获准公开的归档

分发前检查每份所含答案的权利。配置 Buildx 构建器及镜像仓库凭据，然后显式提供仓库与版本标签：

```bash
python -m tcsexam.oracle_package publish \
  --package /path/to/answer-archives/answers-VERSION.tar.gz \
  --destination registry.example.org/namespace/tcsexam-answers:VERSION \
  --confirm-public-release PUBLISH_ORACLE_ANSWERS
```

该命令验证归档，并发布包含归档及其 SHA-256 的 OCI 数据镜像。缺少确认、缺少目标地址或使用 `latest` 标签时，发布前会被拒绝。发布时保留适用的来源声明和分发条件。
