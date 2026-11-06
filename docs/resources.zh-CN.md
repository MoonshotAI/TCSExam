<a id="runtime-images-and-resource-preparation"></a>

# 运行镜像与资源准备

[English](resources.md) | [简体中文](resources.zh-CN.md)

本指南介绍如何下载固定输入并构建本地评测镜像。
面向为 TCSExam 准备 Docker 主机的用户。

<a id="prepare-images-with-tcsexam-build"></a>

## 用 `tcsexam build` 准备镜像

针对将要评测的套件、题目和 Solver 协议运行 `tcsexam build`。
若所选内容包含本地 Lean 构建，先准备其[固定源码归档](#prepare-fixed-lean-source-archives)：

```bash
tcsexam source-inputs
tcsexam build --suite lite --solver-protocol offline
tcsexam doctor --suite lite --solver-protocol offline
```

构建器会复用已验证的本地镜像，获取声明的公开镜像，或运行声明的本地配方。
配方下载固定的官方归档，验证大小和哈希，变换选定输入并组装所需镜像。
本地准备需要 Docker、磁盘空间以及对声明来源的访问权限；不需要注册表账号或上传镜像。
全部三十道 Solver 题目均有默认配方，使用官方下载或源码中附带的固定输入。
各资源的具体要求见下文。

每道题均有开发环境和判分环境。数据镜像和工具镜像为这些完整运行镜像提供构建输入。
开始评测前先准备好它们。题目执行期间，Harbor 运行完整镜像；模型环境不执行资源准备，也不启动数据容器。
隐藏判分输入只能放入判分镜像，包括其继承的镜像层。

[镜像清单](../assets/images.json)将产物关联到配方、内容清单和分发条件。
产物可通过 `acquisition.preferred` 优先选择 `local_build` 或 `public_image`。
未指定偏好时，若有固定版本的公开镜像则优先选择，否则使用本地配方。
获取完整镜像时，执行主机无需具备原始数据集或中间数据镜像。
获取或构建失败会报告错误；不会改选其他题目数据。

<a id="cache-downloads-and-host-requirements"></a>

## 缓存、下载与主机要求

设置 `TCSEXAM_CACHE`，将准备缓存放到空间充足的磁盘；默认位置为 `~/.cache/tcsexam`。
配方固定运行路径、大小、哈希和权限。准备过程验证缓存内容、协调并发调用，
并以原子方式安装完成的结果。准备中断后可以重试；输入损坏会连同路径一起报告，
便于删除并重新获取声明的确切字节内容。

为下载归档、解压输入、变换输出、临时文件和 Docker 层预留空间。
大规模数据准备应在规格适合所选配方的主机上进行。
模型执行和判分在题目配置中各自有独立的 CPU、内存和时间限制。

调用方环境中的 `HTTP_PROXY`、`HTTPS_PROXY` 和 `NO_PROXY` 会转发给下载和构建命令。
`docker pull` 还需要在 Docker 守护进程中配置代理支持。
代理凭证应在守护进程中配置；构建器拒绝将其作为 Docker 构建参数。

对于固定的上游镜像，构建器先尝试 `docker pull`。
如果守护进程无法访问注册表，且已安装 [`crane`](https://github.com/google/go-containerregistry)，
则可直接下载固定版本镜像，并验证其清单、文件系统层和运行配置。
本地构建引用只在临时 Dockerfile 中修改。两种获取方式都会填充 `doctor` 和 `run` 使用的同一镜像身份缓存。

<a id="prepare-fixed-lean-source-archives"></a>

## 准备固定 Lean 源码归档

本地构建 Lean 镜像前，准备 Graphviz 的对应源码输入：

```bash
tcsexam source-inputs
tcsexam build --suite lite --track theorem
```

[源码清单](../assets/environments/lean-base/graphviz-epl/source-manifest.json)
固定 Graphviz 15.0.0 和 hpcc-js/wasm 包装层提交
`8b86e2f83cc7344aca44fb3d8aa29a227358c5c4`。
`source-inputs` 下载它们的官方归档，检查确切大小与 SHA-256/SHA-512 哈希，
并安装到 `assets/environments/lean-base/graphviz-epl/source/`。
Lean 基础镜像的 Dockerfile 复制这些归档并验证 `SHA256SUMS`。
此过程准备镜像中随 Graphviz 提供的源码和许可证材料。

已验证的构建上下文文件或缓存归档会被复用，并在每次调用时检查。
归档按有界大小的数据块写入，验证后通过原子重命名完成写入。
准备好的归档仍由 Git 忽略。离线操作时，获取声明的确切官方归档并导入：

```bash
tcsexam source-inputs --offline \
  --input graphviz=/path/to/graphviz-15.0.0.tar.gz \
  --input wrapper=/path/to/hpcc-js-wasm-8b86e2f83cc7344aca44fb3d8aa29a227358c5c4.tar.gz
```

`--offline` 禁用网络下载。构建上下文或缓存中已有且验证通过的文件，
以及通过 `--input` 提供的文件，仍可使用。文件缺失、大小错误或哈希错误会在准备前失败。
上游访问限制或 URL 不可用会作为下载错误报告；
可从官方来源获取相同归档后重试。获取完整已发布 Lean 镜像会跳过本地源码准备步骤。

<a id="maxsat-hidden-data"></a>

## MaxSAT 隐藏数据

默认配方从固定的 [MaxSAT Evaluation 2026 归档](https://zenodo.org/records/21358014)
重建最终判分集的 200 个 MaxSAT 公式。
[配方](../assets/data/solver/solver-maxsat-mse-judging-data-recipe.json)
固定归档哈希、选定文件、转换参数、随机种子以及输入/输出公式哈希。
它复现声明的变量和子句顺序，并验证完整公式和压缩输出。
Online 与 Offline 终判使用相同隐藏公式；公开自测数据单独准备。

```bash
tcsexam build --suite full --task maxsat-mse --solver-protocol offline
```

Online 使用 `--solver-protocol online`。官方归档约 1.97 GB，
变换后的公式在压缩前共约 26.8 GB。为中间文件、压缩输出和 Docker 层预留额外磁盘空间。
转换使用磁盘中间文件，以限制内存使用。

`build.download_timeout_sec` 设置下载与重试预算。
构建器额外增加 180 秒，用于下载工具准备和验证；数据处理有独立的构建截止时间。
题目判分预算单独定义。

<a id="other-resource-specific-requirements"></a>

## 其他资源的具体要求

查看各条目，了解相应资源的额外要求。

读法说明：每行给出一种资源的准备步骤和要求。

| 资源 | 准备与要求 |
|---|---|
| BPPLIB | Python 3.12+，以及支持 RAR 的系统 libarchive，例如 Debian/Ubuntu 的 `libarchive13` 或 `libarchive13t64`。配方下载 19 个固定版本的官方文件，并重建选定实例、示例装箱方案和开发表。 |
| QBF 公开数据 | 固定版本的 ParaProofa v1 源码归档约 949 MB。配方重建十三个公开实例及其固定 XZ 压缩文件。 |
| PACE 2021 Cluster Editing 和 PACE 2022 Directed Feedback Vertex Set 验证器 | 配方下载固定版本的官方 ZIP/tar.gz，在以摘要固定的 Ubuntu 22.04 linux/amd64 构建器中编译 `ce_verify` 或 `fvs_verify`，并检查源码和编译结果哈希。Docker 提供编译器环境。`tcsexam build` 将生成的工具镜像组合进题目镜像。 |
| PACE 2025 Hitting Set | 独立配方从 `MarioGrobler/PACE2025-instances` 提交 `e0bff608037db1f2b9eec7a7963e31b86663e1ed` 重建 100 个公开和 100 个隐藏明文输入。镜像构建前检查哈希和 HGR 维度。判分时隐藏文件无需解密密钥。 |
| Radiation | 默认配方验证全部 36 个最终判分输入：24 个项目生成的 Apache-2.0 输入和 12 个固定的 MiniZinc MIT 许可文件。无需另行提供归档。 |

在 BPPLIB 开发表中，`best` 是已发布的可行上界，最优性尚未确定时则为下界到上界的区间。
`gap` 是首次适应递减算法的箱数减去该可行上界。此列用于比较两种构造；
最终计分使用题目检查器，确定最优值需使用最优性证书。

若要在不构建完整镜像的情况下检查准备好的文件系统，使用 `tcsexam resources`：

```bash
tcsexam resources --resource bpplib-development --cache /path/to/resource-cache
tcsexam resources --resource qbf-public --cache /path/to/resource-cache
```

QBF 资源命令还可通过 `--input source_archive=PATH` 接收声明的官方归档，
或通过 `--input frozen_input=PATH` 接收经过哈希检查的中间产物。
配方声明列出全部支持的输入名称。构建与源码维护流程见 [CONTRIBUTING](../.github/CONTRIBUTING.zh-CN.md)。

<a id="use-an-external-image-manifest"></a>

## 使用外部镜像清单

外部 `artifacts.json` 可选择现有镜像，替代默认获取方式。
它提供不可变镜像引用、平台、内容身份以及题目角色分配。
注册表凭证保留在清单之外。题目镜像片段如下：

```json
{
  "images": [{
    "id": "example-development",
    "image": "registry.example/tcsexam@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "platform": "linux/amd64"
  }],
  "tasks": {
    "tasks/theorem/dijkstra-universal": {"development": "example-development"}
  }
}
```

为每个所需角色提供实际镜像记录，包括 `verifier` 或 online `backend`，
以及为 Harbor 辅助镜像和固定内核探测器选定的 `type: host_support` 记录。
上述片段仅展示开发镜像分配。`--image-map` 可覆盖题目角色分配，
同时 `--artifacts` 提供主机支持镜像。

```bash
tcsexam setup --suite full --task dijkstra-universal \
  --artifacts /path/to/artifacts.json --output build/setup.json
tcsexam doctor --suite full --task dijkstra-universal \
  --artifacts /path/to/artifacts.json --output build/readiness.json
```

`setup` 验证选择项、拉取缺少的镜像、检查摘要和平台，并将可用性记录到缓存。
它还为 Harbor 支持镜像分配 Harbor 0.22.0 预期的名称。
辅助镜像必须匹配已安装的 Harbor 包上下文，包括文件权限。
未知上下文需要先提供匹配的辅助镜像，才能继续获取。

`--pull-policy never` 要求镜像已在本地；`always` 重新检查注册表获取。
`--docker-context NAME` 选择运行 CLI 和 Harbor 的 Linux 主机上的本地 Unix 套接字 context，
共用题目和作业路径。远程 SSH/TCP context 会被拒绝。
Online 后端镜像也必须在后端主机上可用。就绪检查见[运行评测](running.zh-CN.md)。

<a id="sharing-prepared-products"></a>

## 共享准备好的产物

遵循各资源的[分发条件](licenses/distribution.zh-CN.md)。
BPPLIB 生成文件及所有包含这些文件的镜像均只能本地使用。
QBF 包含三个 BMC 实例，附有额外的非商业教学和研究条款。
包含输入的镜像须保留各输入的全部限制，包括继承层中的文件。
源码导出见 [CONTRIBUTING](../.github/CONTRIBUTING.zh-CN.md)。
