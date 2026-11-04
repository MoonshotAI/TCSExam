<a id="contributing-to-tcsexam"></a>

# 为 TCSExam 作贡献

语言：[English](CONTRIBUTING.md) | [简体中文](CONTRIBUTING.zh-CN.md)

本指南介绍如何贡献研究题目、反馈更正，以及改进代码和文档。
面向希望参与完善 TCSExam 的研究者与开发者。

<a id="suggest-a-task-or-correction"></a>

## 提出新题或更正

通过 [GitHub Issue](https://github.com/MoonshotAI/TCSExam/issues) 提出研究题目或反馈题目问题。请提供题目陈述、来源、所属题型，以及检查提交结果的方法。对于构造题，同时提供参考界及其出处。

反馈更正时，请注明题目并给出能说明问题的具体例子。已有实现时，可以提交包含题面、验证代码和计分规则的 Pull Request。下方的开发说明列出了需要运行的检查。

<a id="set-up-a-development-checkout"></a>

## 准备开发工作副本

使用 Python 3.12 或以上版本，安装运行、后端和测试依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[runtime,backend]' pytest
tcsexam source-inputs
```

`source-inputs` 准备 Lean 构建配方和材料测试所用的固定版本源码归档。
上游下载不可用时，使用[经核验的本地导入](../docs/resources.zh-CN.md#prepare-fixed-lean-source-archives)。

<a id="check-a-change"></a>

## 检查修改

```bash
tcsexam validate
python -m tcsexam.recipes --check
python -m pytest src/tcsexam/backend/tests src/tcsexam/tests -q
tcsexam check-public --phase source --output build/source-check.json
git diff --check
```

`validate` 检查题目结构、评测套件成员、脚本执行权限和源码标识。测试套件覆盖
命令配置、数据配方、评分、后端行为和文档链接。`check-public --phase source`
检查拟分发的源码文件，包括内部引用和分发规则。导出前应解决报告中的错误。

修改运行逻辑时，还应使用有代表性的输入测试受影响的命令或判分器。执行隔离相关
修改使用[判分镜像预检查](../docs/judge-execution-isolation.zh-CN.md)；平台适配器使用
[适配器契约检查](../docs/backend/service.zh-CN.md#writing-a-platform-adapter)。
调整打包方式时，保留题目输入、评分定义和声明的资源预算。

生成的镜像、下载的数据集和评测输出应放在配置的缓存或输出目录中。
构建配方放在 `assets/` 下；题目定义放在 `tasks/` 下，通过
`suites/tasks.json` 选择。

<a id="write-public-documentation"></a>

## 编写公开文档

围绕读者的任务组织指南：前置条件、命令、预期输出和故障处理。
每个配置项、输入准备流程和分数只在一份参考文档中定义，其他指南链接到该文档。
中英文指南的命令、默认值和行为说明应保持一致。

`docs/` 中的 Markdown 是文档内容的源文件，仓库与文档网站共用这些文件。
新增或移动指南时，同时更新[文档首页](../docs/index.zh-CN.md)和对应英文页面的导航。
语言切换只链接同一内容的另一语言版本；阅读路径使用独立的内容链接。

在限制会影响操作的位置说明限制，并写清所需条件和读者应采取的措施。
交付报告、内部评审、开发日记、执行日志和私有基础设施信息应放在源码仓库之外。
保留上游署名、许可文本、来源 URL、固定版本和内容哈希。

仓库内页面和文件使用相对链接。公开仓库地址维护在 `pyproject.toml` 的
`project.urls.Repository` 中。要修改该地址并更新两份入门指南，请运行
`python -m tcsexam.project_links --repository-url https://github.com/OWNER/REPOSITORY`。
运行 `python -m tcsexam.project_links --check` 检查一致性。

默认分支保存评测代码、Markdown 指南和 `paper.pdf`。
网站源码位于 [`gh-pages` 分支的 website 目录](https://github.com/MoonshotAI/TCSExam/tree/gh-pages/website)。
文档站构建程序读取本分支中的 Markdown 指南。

<a id="export-a-source-package"></a>

## 导出源码包

使用目标发布提交的干净工作副本，在仓库根目录运行：

```bash
tcsexam export --normalize-modes --output build/tcsexam-source
tcsexam validate --root build/tcsexam-source
tcsexam check-public --root build/tcsexam-source --phase source
```

目标目录必须尚不存在或为空。如果位于工作副本内部，则必须在 `build/` 下。
导出工具按照分发记录处理文件，排除 Git 元数据、缓存、任务输出、凭据、
参考答案数据和声明为仅供本地使用的输入。导出的目录树包含准备运行环境所需的
配方和获取说明。在导出的工作副本中，进行 Lean 构建或材料测试前，应先运行
`tcsexam source-inputs`。

从导出目录创建公开仓库和发布归档。将源码提交、导出清单和检查结果与发布记录
一同保存，以便追溯发布文件的来源。源码工作副本可能包含参考答案和被排除的
输入；发布导出文件时使用全新的 Git 历史。

`--normalize-modes` 将普通文件权限设为 0644、可执行文件设为 0755、目录设为
0755，同时保留文件内容和可执行状态。不使用该选项时，导出保留源文件权限。

镜像分发另有[组件要求](../docs/licenses/distribution.zh-CN.md)。准备包含已发布镜像的
分发产物时，使用 `tcsexam check-public --phase release`；该检查涵盖镜像地址
和匿名拉取权限。

<a id="extend-the-backend-or-task-resources"></a>

## 扩展后端或题目资源

- [平台适配器契约](../docs/backend/service.zh-CN.md#writing-a-platform-adapter)：worker 创建、
  文件传输、执行、资源计量和清理。
- [后端 HTTP 协议](../docs/solver-backend.zh-CN.md)：客户端请求、凭据、会话状态和提交处理。
- [资源清单](../assets/README.zh-CN.md)：镜像依赖、源码输入和分发记录。
- [公开自测镜像](../docs/backend/public-images.zh-CN.md)：在每个镜像层中将公开数据与隐藏判分
  数据分开。
- [参考答案归档](../docs/oracle-answers.zh-CN.md)：将另行提供、供操作者使用的答案打包。
