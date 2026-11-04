<a id="run-the-online-backend-with-docker"></a>

# 使用 Docker 运行 Online 后端

[English](docker.md) | [简体中文](docker.zh-CN.md)

本指南在本地 Linux Docker 主机上部署 TCSExam 判分服务。
面向使用随附适配器准备 Online Solver 评测的运维人员。

<a id="host-requirements"></a>

## 主机要求

使用 Linux x86-64、Docker Engine 和本地 Unix 套接字，通常为 `/var/run/docker.sock`。
服务用户需要套接字访问权限。使用其他本地套接字路径时，设置 `TCSEXAM_DOCKER_SOCKET`。
适配器支持本地 Unix 套接字；CLI 和 Docker 主机共用题目与输出路径。

Docker 必须能够执行内存和交换空间限制、CPU 配额和 CPU 集合限制。
规划器检查实际生效的守护进程和 cgroup 限制及 CPU 亲和性，包括为开发环境和控制器预留的容量。
各判分镜像还须在此主机上通过 [Landlock 预检](../judge-execution-isolation.zh-CN.md)。

配置可写层存储配额需要 Docker 存储驱动和文件系统支持。复现资源受限的结果时，
保留题目的存储设置。自定义部署若不使用该配额，显式选择 `--storage-limit none`；
规划会将其记录为禁用。

准备好的工作镜像提供 `/bin/sh`、`sleep`、`mkdir`、`setsid` 和 `python3`。
镜像准备使用本地构建配方或配置中固定版本的镜像；见[资源准备](../resources.zh-CN.md)。

<a id="generate-a-selected-task-configuration"></a>

## 生成所选题目的配置

[安装 TCSExam](../getting-started.zh-CN.md) 后，准备一道题并生成服务配置：

```bash
python -m pip install -e '.[runtime,backend]'
tcsexam build --suite full --track solver --task bpp-bpplib --solver-protocol online
tcsexam backend configure --suite full --track solver --task bpp-bpplib \
  --judge-url http://host.docker.internal:8420 --config build/backend.yaml
```

这会写入 `build/backend.yaml` 和 `build/backend.plan.json`。
规划包含准备好的镜像身份信息、分别用于公开与最终判分的客户端设置，以及主机资源限制。
后续命令应保持相同的题目选择、Docker context 和缓存。

生成的服务只允许一个活跃会话，作业规划每次只允许一次试验。
在一道题内，独立实例可以根据容量使用并发工作容器。各工作容器保留声明的 CPU、内存和求解器预算。
共享时间池题目使用一个完整判分组。主机容量无法容纳一个所需工作容器时，
准备阶段会报错并指出缺少的容量。

<a id="configure-credentials-and-networking"></a>

## 配置凭证与网络

通过服务环境或密钥管理器提供以下值：

读法说明：每行给出一个环境变量及其用途。

| 变量 | 用途 |
|---|---|
| `TCSEXAM_TOKEN_ID` | 客户端和工作容器隧道使用的服务身份 |
| `TCSEXAM_TOKEN_SECRET` | 共享服务密钥 |
| `TCSEXAM_ARCHIVE_TOKEN` | 仅供验证器使用，授权隐藏会话创建、核对与归档访问 |
| `TCSEXAM_BASE_URL` | 开发容器和验证器容器可访问的服务地址 |

服务配置中的 `public_base_url` 是判分工作容器使用的回调地址。
服务运行在 Linux Docker 主机时，生成的 host-gateway 配置使用
`http://host.docker.internal:8420`。将客户端地址设置为相同路由：

```bash
export TCSEXAM_BASE_URL=http://host.docker.internal:8420
```

网络布局不同时，选择客户端和工作容器网络均可访问的地址，并检查两条路由。
容器的 `127.0.0.1` 指向该容器自身。守护进程运行于独立网络命名空间时，
使用该命名空间可访问的回调地址。跨越不可信网络时使用经身份认证的 HTTPS。
工作容器隧道向外建立连接；判分端口保持不对外发布。

Docker 套接字仅交给后端进程，归档令牌仅交给验证器。
两者均不得进入模型容器和判分工作容器。生成的配置要求服务启动时提供全部三个凭证变量。

<a id="check-and-start"></a>

## 检查并启动

在服务终端中运行：

```bash
: "${TCSEXAM_TOKEN_ID:?Set the service identity}"
: "${TCSEXAM_TOKEN_SECRET:?Set the service secret}"
: "${TCSEXAM_ARCHIVE_TOKEN:?Set the verifier-only secret}"
tcsexam backend check --config build/backend.yaml
tcsexam backend serve --config build/backend.yaml
```

`check` 验证配置并加载适配器。`serve` 持续运行服务。
在另一个终端中加载相同服务凭证，配置[模型提供方](../running.zh-CN.md#choose-an-agent)，然后运行：

```bash
tcsexam prepare --suite full --track solver --task bpp-bpplib \
  --solver-protocol online --backend-plan build/backend.plan.json \
  --output build/bpp-job.json
tcsexam doctor --suite full --track solver --task bpp-bpplib \
  --solver-protocol online --backend-plan build/backend.plan.json
tcsexam run --suite full --track solver --task bpp-bpplib \
  --solver-protocol online --backend-plan build/backend.plan.json \
  --output build/bpp-job.json
```

`TCSEXAM_BACKEND_PLAN` 是与 `--backend-plan` 等价的环境变量。
启动器向开发环境提供公开凭证，向验证器提供归档凭证。
判分结果和题目产物收集于作业输出中。

<a id="resources-and-lifecycle"></a>

## 资源与生命周期

Docker 工作容器获得 `NanoCpus`、`Memory`、`MemorySwap=Memory` 以及互不重叠的
`CpusetCpus` 预留。将内存与交换空间合计上限设为内存额度即可禁用交换空间，与 Offline 工作容器一致。
适配器检查 Docker 的交换空间限制支持，并验证创建后的镜像、网络和资源设置。
配置的存储配额通过 `StorageOpt.size` 传入，并在创建后检查。
工作容器不使用特权模式或主机绑定挂载。

生成的公开客户端在一次提交完成后释放工作容器（`TCSEXAM_CLOSE_SESSION_AFTER_SUBMIT=1`）。
最终客户端在创建隐藏会话前释放本次运行的公开会话（`TCSEXAM_CLOSE_AGENT_SESSIONS=1`）。
这些设置需与服务的单会话上限配合保留。释放计算资源后，后端仍保留提交记录和归档。

规划器根据选定工作负载推算启动、读取、空闲和会话截止时间，并检查镜像的 `JUDGE_TIMEOUT`。
题目计分器执行自身的求解器计时限制。自定义部署须为所配置并行度下的准备、编译、求解和检查留出足够时间。

工作容器带有 `org.tcsexam.*` 身份和到期标签。
服务重启后，在下一次创建时恢复资源统计并删除到期工作容器。
到期处理需要后端进程保持运行。查看受管理的工作容器：

```bash
docker ps -a --filter label=org.tcsexam.managed=docker-adapter
```

删除残留工作容器前先检查其归属。

<a id="troubleshooting"></a>

## 故障排查

读法说明：根据现象查看相应处理方法。

| 现象 | 处理方法 |
|---|---|
| 工作容器回调失败 | 从工作容器网络检查 `public_base_url` 和 Docker 网桥防火墙。 |
| 客户端无法连接服务 | 从开发与验证器网络检查 `TCSEXAM_BASE_URL`。 |
| CPU、内存或配额准入失败 | 解决规划报告的资源要求，或使用支持所配置配额的主机。 |
| Docker 不支持交换空间限制 | 在主机内核/cgroup 配置中启用交换空间统计，并验证 Docker 报告 `SwapLimit: true`。 |
| 恢复的工作容器缺少 CPU 预留或预留重叠 | 等待这些自有工作容器完成，或删除已确认归属的残留容器，然后再准入新工作容器。 |
| 恢复的工作容器未实施交换空间禁用 | 等待工作容器完成，或删除该自有容器；新建工作容器会应用更新后的资源设置。 |
| 镜像拉取超过 API 超时 | 镜像拉取使用完整工作容器创建时限；检查 `backend.ready_timeout_seconds` 和逐镜像路由。普通 Engine 调用使用 `docker_api_timeout_seconds`。 |
| Docker exec 超时 | 命令可能仍在工作容器内运行。检查工作容器，若必须停止执行则删除该自有工作容器。控制文件读取和捕获输出各限制为 64 MiB。 |

<a id="adapter-development-and-manual-configuration"></a>

## 适配器开发与手动配置

自定义服务设置可从 [config.example.yaml](config.example.yaml) 开始，
并参考[服务配置参考](service.zh-CN.md#configuration-reference)。
其他平台使用 `adapter: module:factory`，并遵循[平台适配器契约](service.zh-CN.md#writing-a-platform-adapter)。

实际测试 Docker 工作容器创建、执行和清理：

```bash
python -m tcsexam.backend.contracttest \
  --adapter docker --config build/backend.yaml \
  --image YOUR_REVIEWED_JUDGE_IMAGE --profile local
```

使用可用的判分镜像。测试套件创建一个 3-CPU/4096-MiB 工作容器，
以及使用配置默认值的其他工作容器，然后删除其资源。须为它们同时预留容量。
Docker 适配器将 `local` profile 保留为元数据。
