<a id="prepare-public-self-test-images"></a>

# 准备公开自测镜像

[English](public-images.md) | [简体中文](public-images.zh-CN.md)

本指南从现有判分镜像构建公开自测镜像。
面向配置 Online 后端公开会话镜像映射的运维人员。

公开自测镜像包含公开输入、参考值、工具和经批准的练习文件。
每个保留的镜像层都必须排除隐藏输入、隐藏参考值、凭证和未经批准的答案。
清单记录哪些文件属于公开镜像。构建前先审查清单。

<a id="manifest"></a>

## 清单

schema-version-1 清单的形式如下：

```json
{
  "schema_version": 1,
  "task": "tasks/solver/online/example-task",
  "remove_paths": ["/tests"],
  "allow_content_paths": [
    "/tests-public",
    "/public-instances",
    "/public_reference.json",
    "/judge"
  ],
  "required_paths": [
    "/judge/entry.sh",
    "/tests-public/checker.py",
    "/tests-public/reference.json",
    "/tests-public/instances",
    "/public-instances"
  ],
  "distribution": "redistributable",
  "public_upload_allowed": true
}
```

`distribution` 和 `public_upload_allowed` 控制注册表写入。
公开 `--push` 要求 `redistributable` 和 `public_upload_allowed: true`；
缺少分发决定或决定尚未明确时会被拒绝。对于已明确授权的私有注册表，添加 `--private-registry`。
`local_prepare` 和 `private_only` 产物只能采用此方式。本地构建和运行使用所声明的准备方式。

路径必须为绝对路径且采用规范形式。`/`、相对路径、`.` 路径段和 `..` 路径段均被拒绝。
`remove_paths` 控制从镜像移除的内容，必须覆盖 `/tests/anchors.json`、
`/tests/reference-hidden.json` 和 `/tests/solution`，可以直接指定，也可以通过 `/tests` 等父目录覆盖，
即使某个镜像不包含这些路径也如此。`allow_content_paths` 仅用于显式声明匹配文件的内容公开且允许重复；
要限制敏感根目录下保留的文件，使用 `payload_allowlist`。
SHA256 检查检测普通文件的完全相同副本。还需审查选定文件是否包含经过变换的隐藏输入和内嵌凭证。

需要路径级隔离的清单应添加 `payload_allowlist`。
每个条目覆盖一个互不重叠的敏感根目录，并重复声明其预期文件数，作为独立一致性检查：

```json
"payload_allowlist": [
  {
    "root": "/app",
    "files": ["/app/public.txt", "/app/solutions/public-example.sol"],
    "regular_file_count": 2
  }
]
```

每个列出的文件必须位于根目录之下，声明数量必须等于列出的唯一文件路径数，
载荷根目录不得与任何移除根目录重叠。目录可不经列举直接出现。
根目录下所有其他条目必须是显式列出的普通文件；链接、设备、未列出的文件、
额外答案和重复的普通文件条目都会导致拒绝。导入后同样要求路径集合和数量完全一致。
应根据当前公开开发环境、公开数据清单和逐一审查过的公开练习答案生成此列表。
不要通过列举隐藏镜像内容生成它，并将隐藏路径和哈希值保留在公开清单之外。

DS 示例位于 `assets/environments/solver/ds-pace2025/public-image.json`。
它移除隐藏的 `/tests` 目录树，同时保留公开检查器、参考数据、实例和判分入口。
源镜像和输出镜像引用通过 CLI 参数传入，有意不写入清单。

<a id="build-and-verify"></a>

## 构建与验证

在持有源镜像的 Docker 主机上，从仓库根目录运行：

```bash
PYTHONPATH=src python -m tcsexam.public_image \
  --source-image registry.example/team/ds-judge:hidden \
  --output-image registry.example/team/ds-judge:public \
  --manifest assets/environments/solver/ds-pace2025/public-image.json
```

将两个镜像引用分别替换为你的源和目标。添加 `--pull` 可先拉取源镜像。
工具构建单层镜像并检查其内容和配置，然后输出 JSON 报告。使用输出标签前先审查报告。
验证失败时，检查报告路径并修正清单或输入；失败尝试可能仍留下本地输出标签。

分发镜像时遵循[组件条件](../licenses/distribution.zh-CN.md)。
审查报告和分发设置后，添加 `--push` 发布输出。工具在推送前验证镜像。
注册表凭证应放在 Docker 本地配置中。

<a id="relationship-to-public_image_map"></a>

## 与 `public_image_map` 的关系

将客户端请求的原始判分镜像引用映射到已验证的公开镜像：

```yaml
public_image_map:
  registry.example/team/ds-judge:hidden: registry.example/team/ds-judge:public
```

公开会话使用映射后的镜像，并设置 `INSTANCE_SET=public`。
未映射的引用返回 HTTP 403。将此映射加入后端配置，然后按照 [Docker 部署指南](docker.zh-CN.md)操作。

<a id="verify-before-enabling-public-sessions"></a>

## 启用公开会话前验证

在部署主机上实际执行一次公开提交，检查响应是否包含请求的全部公开实例记录。
比较公开运行程序与题目检查器在相同输入上的结果。检查工作容器资源、仅限验证器的归档访问，
以及所创建工作容器的清理情况。检查结果时，将判分失败与已完成的分数区分开。

如果通过注册表分发镜像，还应检查其发布地址是否允许匿名拉取。
适配器创建和清理检查使用 [Docker 契约测试套件](docker.zh-CN.md#adapter-development-and-manual-configuration)。

<a id="image-construction-and-content-checks"></a>

## 镜像构建与内容检查

`tcsexam.public_image` 导出当前容器根文件系统，过滤 tar 流，
并使用 `docker import` 创建输出。将过滤后的文件系统合并为单层，会从输出镜像层移除隐藏字节；
使用 Dockerfile 删除则会在早先镜像层中留下这些内容。
过滤后的 tar 通过未命名临时文件流式处理，避免整体加载到内存。
所得镜像必须恰好有一个 RootFS 层。

构建器保留 `Entrypoint`、`Cmd`、`WorkingDir`、`User`、`ExposedPorts`、
`Volumes` 和 `StopSignal`。它丢弃已有标签，并添加中性的 TCSExam 标签。
名称包含 `KEY`、`TOKEN`、`SECRET` 或 `PASSWORD` 的环境项会被移除，匹配不区分大小写；
报告只列出它们的名称。输出设置 `INSTANCE_SET=public`。

清单声明要移除的路径、普通文件内容被显式认定为公开的路径、必须保留的路径，
以及可选的敏感根目录精确公开载荷允许列表。
初次流式扫描时，构建器对待移除目录树和允许的公开目录树中的普通文件计算哈希。
导入后，从输出创建一个全新容器，再导出其根文件系统。这次独立扫描拒绝以下内容：

* 已移除路径、`.key` 文件和加密 `.enc` 文件，包括旧版 `.xz.enc` 名称；
* 已知隐藏参考值和标准答案内容，即使清单遗漏也会检查：
  `/tests/anchors.json`、`/tests/reference-hidden.json`、`/tests/solution` 和
  `/tests/reference.json.bak*` 备份；
* 缺少必须保留的路径，以及解析后指向已移除隐藏目录树的链接；
* SHA256 仅属于已移除内容的任何普通文件，即使内容已复制到无关路径；
* 对每个已配置的载荷根目录，任何不属于精确列举普通文件的非目录条目，
  以及列举文件缺失或重复、普通文件数量不一致的情况。

同样出现在允许的公开路径下的内容，会从仅隐藏内容哈希集合中排除，因此显式公开的副本可以通过检查。
哈希检测结果报告路径、哈希和数量，绝不报告文件内容。
全部验证（包括单层检查和 OCI 配置比较）均在可选推送之前完成。
