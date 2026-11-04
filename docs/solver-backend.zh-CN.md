<a id="online-solver-backend-protocol"></a>

# Online Solver 后端协议

[English](solver-backend.md) | [简体中文](solver-backend.zh-CN.md)

本参考文档描述 Online Solver 客户端使用的 HTTP 接口。
面向服务运维人员和实现兼容适配器的开发者。

<a id="deployment-scope"></a>

## 部署范围

1. 用 `tcsexam build` 准备选定的开发镜像和判分镜像。
2. 按照 [Docker 部署指南](backend/docker.zh-CN.md)或使用
   [自定义平台适配器](backend/service.zh-CN.md#writing-a-platform-adapter)配置凭证并启动服务。
3. 针对所选部署配置 `prepare`、`doctor` 和 `run`：

   - Docker 部署：提供生成的 `--backend-plan PATH`，其中包含服务地址和选定题目的工作容器规划。
   - 外部服务：传入 `--judge-url URL`，或将 `TCSEXAM_BASE_URL` 设置为题目容器可以访问的地址。
     生成的 Docker 规划可选；未提供时，启动器会使用选择记录中各题的标准工作容器数量、
     资源以及 `standard_client_timing` 下记录的时间设置。服务必须提供这些资源并遵守题目预算。
4. 在作业输出中检查提交记录和最终结果。

客户端为 `tasks/solver/online/<task>/environment/submit.sh` 和
`tasks/solver/online/<task>/tests/fetch_final.py`。它们使用题目声明的实例集、时间预算和计分规则。

<a id="credentials-and-attempt-identity"></a>

## 凭证与尝试标识

所有请求均使用身份认证。归档凭证仅提供给验证器。请求头名称不区分大小写。

读法说明：每行给出一个 HTTP 请求头及其值。

| HTTP 请求头 | 值 |
|---|---|
| `X-TCSEXAM-Token-Id` | `TCSEXAM_TOKEN_ID` |
| `X-TCSEXAM-Token-Secret` | `TCSEXAM_TOKEN_SECRET` |
| `X-TCSEXAM-Client-Id` | 本次题目尝试的稳定标识 |
| `X-TCSEXAM-Run-Id` | 同一个题目尝试标识 |
| `X-TCSEXAM-Agent-Name` | 可选的 `TCSEXAM_AGENT_NAME` |
| `X-TCSEXAM-Archive-Token` | 来自 `/tests/archive_token`、仅供验证器使用的凭证 |

将 `TCSEXAM_RUN_ID` 设为每次尝试唯一且稳定的标识。未设置时，客户端使用容器主机名。
后端必须隔离共用出口地址的不同尝试。凭证和归档内容的访问范围必须限定在所属尝试内；
模型不得获取归档凭证。

随附服务会检查每个会话声明的 Run-Id，以区分共用服务凭证且相互配合的调用方。
Run-Id 是调用方提供的标签；需要防止蓄意冒充的部署还须为每次尝试提供独立认证的凭证。
参见服务的[安全边界](backend/service.zh-CN.md#security-boundaries)。

前台请求、后台保活请求、终判和审计下载应使用相同的请求头名称。TCSEXAM 接口始终使用这一命名空间。
创建隐藏会话、任何携带 `judge_payload` 的创建操作，以及所有会话列表和核对查询，
除服务令牌对外还必须提供归档请求头。在这些创建和列表操作中，归档凭证缺失、错误或未配置均返回 403。
不携带 `judge_payload` 的公开自测创建、状态查询、提交和结果轮询仅使用服务令牌对。
归档请求头只发送到创建、列表以及归档和载荷服务端点，不得经过求解器提交转发接口传入判分工作容器。

使用 TCSExam 启动器将凭证传入 agent 和验证器容器。自定义启动器需填充题目的
`${TCSEXAM_*}` 占位符，并保留凭证仅放置于验证器的要求。

<a id="session-interface"></a>

## 会话接口

以下路径均相对于 `TCSEXAM_BASE_URL`。现有客户端定义每道题的确切行为；下表展示它们共用的接口。

读法说明：每行列出一种方法和路径及其行为。

| 方法和路径 | 行为 |
|---|---|
| `POST /v1/judge/sessions` | 接收 `judge_image`、`ttl`、`n_shards`、`resources`，以及可选的 `instance_set` 和 `judge_payload`；返回 `session_id`。公开自测请求 `public`，且必须存在精确匹配的 `public_image_map` 条目。不带载荷时只需服务身份认证。省略实例集时默认为 `hidden`；创建隐藏会话和所有携带 `judge_payload` 的创建操作还须提供归档请求头。 |
| `GET /v1/judge/sessions` | 列出活跃会话和最近销毁的会话。需要归档请求头；下列 `session_ids` 和 `client_ip` 查询形式也适用。 |
| `GET /v1/judge/sessions/{id}` | 报告就绪状态和失败情况。资源准备必须完成后才能开始判分。 |
| `POST /v1/judge/sessions/{id}/submit` | 接收 `Content-Type: application/gzip` 的原始 tar.gz；接受后返回整数 `submission`。不要通过此转发接口发送归档请求头。 |
| `GET /v1/judge/sessions/{id}/submissions` | 返回 `submissions`，每项包含 `submission`、`status` 和逐实例 `records`。未完成提交使用 `running` 状态。 |
| `GET /v1/judge/sessions/{id}/archive` | 需要归档请求头，返回各分片的原始记录，包括 `instance_set`、`n_shards`、`shard_payloads` 和 `failed_shards`。 |
| `GET /v1/judge/sessions?session_ids=a,b` | 需要归档请求头。返回各会话的隐藏提交计数 `submissions`、`public_submissions` 和 `present`；资源释放后仍保留计数。 |
| `DELETE /v1/judge/sessions/{id}` | 释放工作容器，同时保留验证所需的计数和记录。 |

可选审计端点 `GET /v1/judge/sessions/{id}/payload/submissions` 和
`GET /v1/judge/sessions/{id}/payload/submissions/{seq}` 分别列出提交编号和返回原始上传的 tar 字节。
它们使用归档请求头。可选载荷不可用会单独记录，与判分失败分开处理。
旧版运维查询 `GET /v1/judge/sessions?client_ip=self` 属于可选遥测，同样需要归档请求头；
它不得用于决定一次尝试的分数或提交额度。

提交在接受时计数一次。HTTP 503 表示提交尚未被接受，可以重试。
上传连接断开且是否接受不明确时，不得盲目重试。当前验证器将 `/submit` 的 HTTP 429
解释为触及提交次数上限，因此后端不得用此响应表示普通工作容器拥堵。
HTTP 410 或 `error_class=terminal` 表示会话永久不可用。

保留每个实例的目标值、合法性和状态，包括未计入某项分数均值的实例。
基础设施失败必须与有效零分区分。保留各题的时间池、证书检查、预算、历史选择规则以及公开与隐藏数据的隔离。

<a id="images-and-deployment"></a>

## 镜像与部署

创建公开会话时，使用精确匹配的 `public_image_map` 键，将请求的判分镜像映射为仅含公开数据的工作镜像。
缺少条目时，在创建任何工作容器之前返回 HTTP 403。创建隐藏会话使用所请求的隐藏镜像。

用 `tcsexam build` 准备镜像，或提供包含不可变后端镜像分配的外部清单。
注册公开镜像前，按照[公开镜像准备](backend/public-images.zh-CN.md)检查输入和保留的镜像层。
然后配置映射，并通过 [Docker 指南](backend/docker.zh-CN.md)启动服务。
