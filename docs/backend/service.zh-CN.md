<a id="deploy-the-online-judging-service"></a>

# 部署 Online 判分服务

[English](service.md) | [简体中文](service.zh-CN.md)

本指南介绍服务配置、运行和平台适配器。
面向托管 Online Solver 判分的运维人员。

服务管理 HTTP 请求、判分会话、并行工作容器、反馈、归档和提交计数。
本地 Docker 主机可选择随附的 Docker 适配器，其他运行时可实现平台适配器接口。
运维人员负责提供执行主机、判分镜像和服务凭证。

本地 Docker 部署按[配置生成流程](docker.zh-CN.md)操作。
[HTTP 协议参考](../solver-backend.zh-CN.md)定义客户端请求和响应。

<a id="install"></a>

## 安装

```bash
python -m pip install -e '.[runtime,backend]'
```

<a id="configure"></a>

## 配置

手动配置服务时，复制示例并在服务环境中设置凭证：

```bash
mkdir -p build
cp docs/backend/config.example.yaml build/backend.yaml
: "${TCSEXAM_TOKEN_ID:?Set the service identity}"
: "${TCSEXAM_TOKEN_SECRET:?Set the service secret}"
: "${TCSEXAM_ARCHIVE_TOKEN:?Set the verifier-only secret}"
```

从 [config.example.yaml](config.example.yaml) 开始；这是一个 Docker 示例，注释值展示默认设置。
敏感配置优先从环境读取（`TCSEXAM_TOKEN_ID`、`TCSEXAM_TOKEN_SECRET`、
`TCSEXAM_ARCHIVE_TOKEN`、`TCSEXAM_WORKER_GROUP`），并覆盖 YAML 值；
不要将真实令牌写入提交到仓库的文件。`TCSEXAM_DOCKER_SOCKET` 覆盖 Docker 套接字路径。

需特别注意 `public_base_url`：每个判分工作容器内的 agent 会连接
`<public_base_url>/v1/tunnel/{app}`，因此该地址必须能从判分工作容器访问。
默认值为 `http://127.0.0.1:<port>`，适用于随附测试适配器的本地测试。
Docker 示例显式使用 `http://host.docker.internal:8420`；当工作容器网络为非 host 模式时，
Docker 适配器会拒绝容器回环 URL。参见 [Docker 网络与主机要求](docker.zh-CN.md#host-requirements)。

归档凭证仅供验证器使用。启动服务前，确认工作容器能访问回调地址，且已准备好选定镜像。

<a id="start-and-check"></a>

## 启动与检查

```bash
tcsexam backend check --config build/backend.yaml   # validate config + load the adapter
tcsexam backend serve --config build/backend.yaml   # run the service
```

`check` 以 JSON 输出实际生效的配置，并加载已配置的适配器。
成功时退出码为 0，任何配置问题（包括 `adapter` 为空或适配器加载失败）均以 2 退出，
因此可以安全地接入部署流水线。`serve` 接受 `--host` / `--port` 覆盖选项。
`python -m tcsexam.backend --config build/backend.yaml` 是等价入口。

<a id="configuration-reference"></a>

## 配置参考

读法说明：各值均为内置默认值，YAML 缺少对应键时使用。
标有“env”的键，在对应环境变量已设置时由其覆盖。

顶层键：

| 键 | 默认值 | 说明 |
|---|---|---|
| `host` | `0.0.0.0` | HTTP 服务绑定地址 |
| `port` | `8420` | 绑定端口 |
| `public_base_url` | `""`（回退到 `http://127.0.0.1:<port>`） | 外部可访问的基础 URL；工作容器内的 agent 连接 `<public_base_url>/v1/tunnel/{app}` |
| `auth.token_id` | 空 | 共享令牌认证 id（env `TCSEXAM_TOKEN_ID`）；两者均为空时不认证，仅限本地测试 |
| `auth.token_secret` | 空 | 共享令牌认证密钥（env `TCSEXAM_TOKEN_SECRET`） |
| `auth.additional_tokens` | `[]` | 为平滑轮换而额外接受的 (id, secret) 对 |
| `auth.run_id_mode` | `warn` | 调用方身份要求：`warn` 记录日志后提供服务，`required` 以 400 拒绝，`off` 不读取请求头 |
| `state_dir` | `/tmp/tcsexam-backend-state` | 会话日志、归档和持久化载荷 |
| `adapter` | `""` | 平台适配器配置：`docker`、`module:factory`，或仅供测试的 `local-test`；空值表示服务以明确错误拒绝创建会话 |
| `docker_socket` | `/var/run/docker.sock` | 本地 Docker Engine Unix 套接字（env `TCSEXAM_DOCKER_SOCKET`）；拒绝远程 TCP 端点 |
| `docker_network` | `bridge` | 判分工作容器使用的 Docker 网络；须能从此网络访问 `public_base_url` |
| `docker_pull_missing_images` | `true` | 使用完整创建预算拉取缺少的判分镜像；私有镜像应由运维人员拉取 |
| `docker_host_gateway` | `true` | 为工作容器添加 `host.docker.internal:host-gateway`，作为 Docker 主机隧道地址 |
| `docker_api_timeout_seconds` | `60` | 普通 Docker API 调用超时；首次拉取镜像使用完整创建预算 |
| `worker_group` | `tcsexam` | 工作容器组标签前缀（env `TCSEXAM_WORKER_GROUP`）；空值表示不标记组。创建带 run-id 的会话时，每个分片的工作容器创建均携带 `labels={run_id, token_id}` 和 `group_name="<worker_group>--<run-id slug>"`（平台可精确回收某一次尝试的工作容器）；不带 run-id 的会话创建时不打标签 |
| `archive_token` | `""` | 仅供验证器使用的凭证（env `TCSEXAM_ARCHIVE_TOKEN`），用于归档/载荷、创建隐藏会话、所有携带 `judge_payload` 的创建操作及会话列表/核对查询；空值禁用这些操作 |
| `public_image_map` | `{}` | 从客户端请求的原始判分镜像到仅含公开数据的工作镜像的精确映射。映射为空或缺少所请求镜像时，创建公开会话直接以 403 拒绝；创建隐藏会话从不使用此映射 |

`backend` 部分（工作容器创建与全局使用上限）：

读法说明：每行列出一个配置键、默认值及其作用。

| 键 | 默认值 | 说明 |
|---|---|---|
| `create_retries` | `20` | 首次失败后的额外创建尝试次数，仅用于暂时性错误 |
| `create_retry_delay_seconds` | `60` | 创建重试之间的基础延迟；第 N 次尝试等待 base x 2^(N-1)，上限为 10 min |
| `create_concurrency` | `64` | 并发创建工作容器的上限 |
| `session_create_concurrency` | `64` | 单会话创建并发数，在全局并发控制之前获取名额 |
| `max_sandboxes_global` | `4096` | 接受创建请求时进行的全局工作容器数量预检 |
| `max_sandbox_memory_mb` | `32768000` | 同一预检的内存维度（MiB） |
| `ready_timeout_seconds` | `2400` | 交给适配器的平台侧创建/就绪预算 |

`backend.judge_sessions` 部分（主要设置；其余见示例文件注释）：

读法说明：每行列出一个配置键、默认值及其作用。

| 键 | 默认值 | 说明 |
|---|---|---|
| `max_sessions` | `16` | 全局活跃会话上限；超出时创建以暂时性错误失败 |
| `profile` | `""` | 原样传给适配器的调度提示，服务不解释其内容 |
| `spec` | `{cpu_count: 4, memory_mb: 8192, storage_mb: 20480}` | 原样传给适配器的逐工作容器资源 |
| `command` | `python3 /judge/judge_worker.py` | 在工作容器内启动的判分程序；空值表示 agent 仅转发到已运行的服务 |
| `judge_port` | `8082` | 工作容器内判分服务监听端口 |
| `ttl_seconds` | `21600` | 默认单会话生存时间（TTL），用作平台兜底限制 |
| `max_ttl_seconds` | `46800` | 调用方请求 TTL 的上限 |
| `idle_ttl_seconds` | `14400` | 空闲回收阈值；必须大于最长的单次判分请求 |
| `ready_timeout_seconds` | `1800` | 隧道等待失败前允许的创建与启动预算 |
| `max_shards` | `512` | 各会话 `n_shards` 上限 |
| `min_ready_ratio` | `1.0` | 降级就绪最低比例；1.0 表示部分资源准备失败时整个会话失败，避免产生部分分数 |
| `hibernate_enabled` | `true` | 将已结束处理且安静的会话回收为仅保留元数据的状态，下次提交时重新准备资源 |
| `hibernate_grace_seconds` | `1800` | 已结束处理的会话进入休眠前的安静期 |
| `submission_cap.enabled` | `false` | 单会话提交次数上限（需主动启用）；无论是否启用都会计数，供核对查询使用 |
| `submission_cap.default` | `10` | 每个判分会话的上限 |
| `submission_cap.overrides` | `{}` | 按镜像族设置的上限；匹配到镜像族时优先于默认值 |
| `routes` | `[]` | 按镜像族设置的就绪/生命周期预算；第一个 `image_contains` 子串匹配生效。`ready_timeout_seconds` 控制隧道等待和 agent 启动；`create_ready_timeout_seconds` 传给适配器。调用方省略 TTL 时，`ttl_seconds` 提供默认值；`idle_ttl_seconds` 设置该会话空闲阈值。显式请求的 TTL 优先，但仍受 `max_ttl_seconds` 约束。路由值在休眠和唤醒后保留。 |

主凭证 `auth.token_id` 和 `auth.token_secret` 都必须是非空字符串。
本地测试若需禁用认证，应同时省略两项。仅配置一项或提供空值对会导致配置验证失败。
每个 `additional_tokens` 条目必须恰好包含两个非空字符串，且轮换凭证要求有主凭证对：
工作容器用主凭证连接隧道。验证会在加载 YAML 并应用环境覆盖后执行，
构建应用时再次执行；错误仅指出无效字段，不输出其值。
凭证比较支持 Unicode，对每对凭证的两个元素均使用常量时间字节比较。

只有显式提供 `X-TCSEXAM-Client-Id` 且实际生效的输入完全相同，
并发创建才会共用一个正在准备资源的会话。这些输入包括令牌身份、经验证的 run-id、
实际工作镜像（公开映射后）、上传文件名与内容、资源、生存时间、分片数和实例集。
省略默认资源或生存时间，等价于显式传入相同默认值。输入变化会创建独立会话；
不会悄然复用包含另一份上传内容的工作容器。

会话生存时间、工作容器启动和请求读取分别计时。
随附开发客户端请求 46800 秒（12 小时加一小时余量）；默认 `max_ttl_seconds` 也是 46800。
公开分片存储在整组就绪时开始服务侧生存时间，而平台工作容器生存时间从创建工作容器时开始。
因此启动耗时会占用部分平台余量。休眠释放工作容器，后续提交会准备新的工作容器；
提交历史会保留，服务侧生存时间在就绪时重新开始。
最终评测客户端创建独立会话，并保留各题 14400–28800 秒的生存时间。
降低 `max_ttl_seconds` 会限制两种客户端的请求，可能在预算用完前使活跃会话到期；
平台配置应同时容纳判分时间和启动余量。

`ready_timeout_seconds` 限制隧道连接等待时间。
无论创建单个工作容器还是分片组，工作容器 agent 均使用相同的启动预算，上限为 7200 秒。
逐镜像的 `create_ready_timeout_seconds` 传给平台适配器。
`read_timeout_seconds`（默认 7200）限制上游判分响应等待时间，并转发给每个工作容器 agent。
对于长时间判分请求，应增加读取超时及相应的分发超时；
只增加会话生存时间不会增加这些请求限额。

<a id="behavior-contract"></a>

## 行为契约

以下语义由题目客户端固定，并有测试覆盖；部署不得改变。

* 提交在接受时计数一次。`POST
  /v1/judge/sessions/{id}/submit` 接受请求体后返回整数提交编号。
  计数单位是转发层 `/submit`；向分片分发属于判分内部并行，不计提交次数。
* `/submit` 的 HTTP 429 表示触及单会话提交次数上限，响应体为
  `{"error": "submission_cap_exceeded", "cap": ..., "used": ...}`。
  验证器将 429 解释为该上限，因此后端不得用它表示普通工作容器拥堵。
* HTTP 503（`error_class=transient`）表示提交未被接受，可以重试。
  它涵盖仍在准备资源的会话和全局容量不足的拒绝。
  暂时性错误消息携带标记 "please try again"，题目侧重试匹配器会逐字匹配该标记。
* HTTP 410（或 JSON 响应体中的 `error_class=terminal`）表示会话已永久销毁。
* DELETE 销毁属于该会话的每个工作容器，并关闭服务侧每条反向隧道，包括所有分片。
  使用已销毁会话的一次性应用名进行迟到重连会被以 404 拒绝；普通隧道断开仍允许重连。
  会话状态变为 410 后，验证器仍能读取保留的归档以及创建/提交载荷历史。
* 基础设施失败绝不产生有效零分。默认 `min_ready_ratio: 1.0` 下，部分资源准备失败会使整个会话失败；
  失败的资源准备从未接受提交，因此不消耗调用方的提交预算。
* 实例间共享一个时间池的题目必须以 `n_shards=1` 创建，即完整实例集放在一个工作容器中。
  对时间池题分片会改变其判分语义。随附客户端已编码这一要求。
* 归档凭证（`X-TCSEXAM-Archive-Token`）仅由验证器提供。
  它控制归档和载荷下载、隐藏会话创建（包括省略 `instance_set` 的情况，默认值为 hidden）、
  所有携带 `judge_payload` 的公开或隐藏创建操作，以及所有会话列表/核对查询。
  凭证缺失、错误或未配置时，在创建任何工作容器或返回会话数据前即拒绝请求。
  归档和载荷端点保留统一 404 契约；创建和列表入口返回 403。
* 不携带 `judge_payload` 的公开自测会话（`instance_set=public`）仅需要服务令牌对。
  其状态、提交和结果轮询路径不使用归档凭证。
  创建公开会话要求精确匹配的 `public_image_map` 条目，并将仅含公开数据的映射值用作会话和工作容器镜像。
  映射为空或请求镜像未注册时，在注册会话或创建工作容器前返回 403；不会回退到原始镜像。
  创建隐藏会话从不应用此映射。公开会话写入日志以保留历史，但不计入提交次数上限。
* 会话属于创建它的运行。实际生效的 run-id（经身份认证中间件验证的 `X-TCSEXAM-Run-Id`）
  存储在会话中并写入日志，因此在 DELETE 和服务重启后仍保留。
  每个会话级端点——状态、转发（`/submit`、`/submissions` 和任何转发的尾部路径）、
  DELETE、归档、三个载荷端点，以及 `?session_ids=` 核对查询——仅服务于 run-id 与会话所有者匹配的请求。
  不匹配时的响应与未知会话 id 完全相同：统一 404（`unknown judge session {sid}`），
  绝不返回 401/403 或已销毁状态的 410 形式，因此该检查不会泄漏会话是否存在；
  在 `?session_ids=` 响应中，不匹配的 sid 返回 `present=false` 且不提供计数。
  普通列表和 `?client_ip=` 诊断查询返回的会话遵循相同归属过滤，包括保留的已销毁会话；
  诊断查询总数仅包含可见行。对未知会话执行 DELETE 与错误运行的请求返回相同 404，
  而已知且已释放会话的所有者重复 DELETE 时仍返回 200 和 `stopped=false`，日志重放后亦如此。
  `/v1/status` 路由仍提供含全局统计的服务级运维视图。
  创建时未携带 run-id 的会话无所有者且不受限制（从不发送 run-id 的本地和旧版调用方仍可使用）。
  创建去重键也包括 run-id：即使发送相同的 `X-TCSEXAM-Client-Id`，两个运行也绝不共用正在准备资源的会话，
  同一运行的并发重试仍可共用。

<a id="security-boundaries"></a>

## 安全边界

- 需要身份认证的部署应使用服务令牌对，并通过环境注入。真实凭证存放于源码仓库之外。
- 归档令牌只交给验证器。它授权隐藏会话创建、会话核对和归档访问；
  不得进入模型环境、工作容器和提交转发接口。
- Run-Id 是调用方提供的尝试标签。对于彼此不信任的调用方，
  除共享令牌服务外，还需为每次尝试提供独立认证的凭证或等效授权层。
- 公开会话映射到仅含公开数据的镜像。按[公开镜像指南](public-images.zh-CN.md)审查所有保留镜像层；
  镜像内容分离后再选择公开判分模式。
- Docker 套接字仅交给后端进程。它能控制主机，必须保留在模型容器和判分工作容器之外。
- 平台凭证保留在适配器配置内，不得出现在日志、工作容器环境和异常消息中。

<a id="troubleshooting"></a>

## 故障排查

读法说明：根据现象或部署条件查看相应处理方法。

| 现象或部署条件 | 处理方法 |
|---|---|
| Docker 准入或配额检查失败 | 按 [Docker 主机指南](docker.zh-CN.md#host-requirements)检查实际生效的 CPU、内存和配置的存储配额。 |
| 服务停止后仍有工作容器残留 | 重启服务以恢复其管理的工作容器，或检查并仅删除确认归属的容器。到期处理在后端进程内运行。 |
| 自定义或旧版工作程序在 `run_id_mode=required` 时收到 HTTP 400 | 隧道连接携带其所属的 `X-TCSEXAM-Run-Id`。混合版本升级期间保持 `warn`，启用 `required` 前先更新工作容器 agent。 |
| 长时间评测丢失会话 | 在 `max_ttl_seconds` 中允许所请求的生存时间和启动余量；同时检查配置参考中的请求读取超时。 |
| 选择 `local-test` | 仅用于后端开发测试。其工作环境是本地临时目录，无资源限制或隔离。 |

<a id="writing-a-platform-adapter"></a>

## 编写平台适配器

完整契约见 `tcsexam.backend.adapter` 模块文档字符串。
带注释的最小框架位于 [examples/adapter_minimal.py](examples/adapter_minimal.py)。

读法说明：下表列出会话存储调用的成员。加载器在启动时验证全部成员；
缺少成员会被视为配置错误，绝不静默降级。

| 成员 | 签名 | 契约 |
|---|---|---|
| `ready_timeout_seconds` | 属性 `float` | 适配器自身的创建预算，存储在计算资源准备截止时间时读取 |
| `create_sandbox` | `(profile, image_url, *, ttl_seconds, spec, ready_timeout_seconds, group_name, labels) -> Worker` | 从 `image_url` 创建一个工作容器，资源必须与请求完全一致 |
| `register_long_lived` | `(app_name, worker) -> None` | 将工作容器加入长驻资源表（隧道关闭回收器和 `stop_app` 通过该表工作） |
| `sandbox_for_app` | `(app_name) -> Worker \| None` | 返回应用的活跃长驻工作容器，不改变状态 |
| `long_lived_count` / `long_lived_memory_mb` | `() -> int` | 长驻资源表大小和内存总量，用于使用量统计 |
| `stop_app` | `async (app_name) -> None` | 销毁长驻工作容器；幂等，未知应用不做操作 |

存储使用的工作容器接口：

读法说明：每行列出一个工作容器成员、签名和必须满足的契约。

| 成员 | 签名 | 契约 |
|---|---|---|
| `worker.ctrl.write_bytes` | `async (path, data: bytes, parents=False) -> None` | 在工作容器内写入字节；`parents=True` 创建缺少的目录 |
| `worker.ctrl.run` | `async (cmd, shell=False, text=False, timeout=30)` | 在工作容器内运行命令；返回带 `stdout` 属性的对象。传输失败时抛出异常；退出码非零时报告该退出码，不抛出异常 |
| `worker.ctrl.read_text` | `async (path) -> str` | 读取文本文件；不存在或不可读时抛出异常 |
| `worker.name` | 属性 `str` | 平台侧标识，仅用于日志 |
| `worker.delete` | `async () -> None` | 销毁工作容器；幂等，尽力执行（工作容器自身 TTL 是最终兜底限制） |
| `worker.resources` | 可选属性 `WorkerResources` | 创建时的资源。非必需：`BasePlatformAdapter` 优先用它统计 `long_lived_memory_mb`，否则回退到自身 `create_sandbox` 记录的资源 |

每个实现必须遵循的行为规则：

* 按请求原样提供镜像和资源。平台无法提供时，抛出明确错误。
  静默启动较小规格的工作容器违反契约：判分运行假定资源与声明一致。
* 错误按类名分类。`errors.NON_TRANSIENT_ERROR_NAMES` 中的名称
  （`AuthenticationError`、`PermissionDeniedError`、`InvalidArgumentError`、
  `InsufficientCreditsError`、`JudgeBootError`）从不重试；
  其他异常均视为暂时性错误，以指数退避重试。
  `ValueError` 始终视为非暂时性错误（调用方程序错误）。
* `stop_app` 和 `worker.delete()` 均幂等。
* 清理范围有限：仅销毁适配器自己创建的资源，绝不执行整个账号范围的清理。
* 取消创建不能遗留已创建一部分的工作容器。
* 平台凭证保存在适配器自身配置中，不得出现在日志、工作容器环境变量或异常消息中，
  因为异常文本会传播到题目客户端。

继承 `BasePlatformAdapter` 可获得受创建并发控制的暂时性错误重试循环、
长驻资源表，以及支持恢复 agent.log 尾部的幂等 `stop_app`；
此时只需实现 `_create_worker`，即面向具体平台的一次创建尝试。

加载方式：`adapter: docker` 选择 [Docker 指南](docker.zh-CN.md)描述的随附 Docker 实现。
其他平台将 `adapter` 设为 `module:factory`。
工厂被导入后，若接受一个位置参数，则用已加载的 `Config` 调用；否则不传参数。
返回结果会按上述完整接口检查。`adapter` 为空时，启动以 `ConfigurationError` 失败，
服务绝不静默回退到测试替代实现。显式值 `local-test` 选择随附的本地进程测试适配器
（仅用于测试；其工作环境是服务主机上的临时目录，无隔离或资源限制）。

使用随附契约测试套件自检任意适配器：

```bash
python -m tcsexam.backend.contracttest --adapter mypackage.cloud:make_adapter --config config.yaml \
    --image registry.example.com/your-judge:1 --profile your-profile
python -m tcsexam.backend.contracttest --adapter docker --config config.yaml \
    --image registry.example.com/your-judge:1 --profile local
python -m tcsexam.backend.contracttest --adapter local-test   # exercise the test double
```

套件为每项检查输出一行；全部通过时退出码为 0，任一检查失败为 1，适配器无法加载为 2。
它通过适配器创建真实资源，并销毁自己创建的每个工作容器，因此应指向测试环境。
检查与具体平台无关：创建严格遵循请求、工作容器身份唯一、文件准备、状态诊断、
命令启动、内存统计、幂等停止/删除、创建失败清理，以及限定范围的清理。

`--image` 和 `--profile` 决定检查传给 `create_sandbox` 的参数。
传入可用镜像以及平台预期的 profile。默认值
（`registry.example.com/contract-judge:1` / `contract-profile`）是供本地测试适配器使用的示例。

<a id="testing-and-verification"></a>

## 测试与验证

```bash
python -m pytest src/tcsexam/backend/tests/
```

套件测试 HTTP 请求、分片、提交统计、归档、运行归属、生命周期和适配器行为。
Docker 单元测试通过 Unix 套接字使用模拟 Engine。
实际测试工作容器创建和清理时，使用可用镜像与平台 profile 运行
[适配器契约测试套件](#writing-a-platform-adapter)。
完整源码检查见[贡献指南](../../.github/CONTRIBUTING.zh-CN.md)。
