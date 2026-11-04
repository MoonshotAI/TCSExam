<a id="offline-solver-adapters"></a>

# Offline Solver 适配器

[English](offline-adapters.md) | [简体中文](offline-adapters.zh-CN.md)

本指南描述 Offline Solver 判分的本地 Docker 执行方式。
面向准备公开自测与隐藏终判的用户。

<a id="run-a-suite"></a>

## 运行套件

[安装运行时并配置模型](getting-started.zh-CN.md)后，运行：

```bash
tcsexam build --suite lite --track solver --solver-protocol offline
tcsexam doctor --suite lite --track solver --solver-protocol offline
tcsexam run --suite lite --track solver --solver-protocol offline
```

使用 `--suite full` 运行全部三十道 Solver 题，或用 `--task TASK_ID` 选择一道题。
构建器准备开发镜像和验证器镜像，并将其身份信息保存到本地缓存。
`doctor` 检查选定镜像和执行主机。开始运行前，先解决其报告的阻塞问题。

终判期间，Harbor 启动一个验证器控制器。控制器创建隔离的 Docker 工作容器，
提供提交内容和分配的隐藏输入，收集结果并删除其工作容器。
Offline 执行使用每次尝试独立的控制器；Online 服务部署见
[Docker 后端指南](backend/docker.zh-CN.md)。

<a id="execution-host-resources"></a>

## 执行主机资源

执行主机需使用以 root 权限运行的 Linux Docker 守护进程，并提供 `/var/run/docker.sock`。
验证器的 `tests/docker-compose.yaml` 挂载此套接字及只读主机 cgroup 树，
使用主机 PID 和 cgroup 命名空间。CLI 用户需要 Docker 访问权限。
此 compose 配置要求标准套接字路径，即使选择了 Docker context 也一样。

套接字仅供可信验证器控制器使用。开发容器和判分工作容器运行时均不持有该套接字。
判分工作容器还需要 [Landlock 和镜像预检](judge-execution-isolation.zh-CN.md)；
构建和求解器命令在 root 监督下以 UID/GID 65534 运行。

各题的 `tests/runtime/task.json` 声明工作容器资源预留。
只有 CPU 和内存预留资源足够时，控制器才允许启动工作容器，另外为控制器预留一个 CPU 和 512 MiB。
例如，32 GiB 的工作容器需要至少 33,280 MiB 可见主机内存，准入时还需有足够的空闲内存和磁盘。
四 CPU 工作容器需要至少五个可见 CPU，包含控制器预留。
开发容器另有资源要求，会在模型执行前检查。

每道题最多同时使用十个判分工作容器。较小主机同时运行较少的工作容器，
但保留各工作容器的资源和各实例的求解器预算。题目声明分片共享内存时，工作容器预留完整额度。
容量不足会产生环境错误，并在报告中列出所需资源。

<a id="judging-and-results"></a>

## 判分与结果

各工作容器为分配到的实例调用题目的准备脚本和检查器。
检查器验证候选输出并计算其目标值。控制器将完整实例记录合并成最终题目结果。
题目奖励、判分失败和 Index 计算见[计分](scoring.zh-CN.md)。

装箱、图划分、体育赛程安排、逻辑综合、二次指派和集合覆盖均只使用一个工作容器，
覆盖完整的共享时间池：所有实例共用一个求解器总预算。配置并行度时须保持这些组完整。
其他题目使用声明的逐实例限额和分组。

工作容器的外层截止时间为编译、求解和验证留出时间。
计分程序单独执行题目的求解器预算限制。计分器使用的 CPU 编号映射到为其工作容器预留的 CPU。

<a id="troubleshooting"></a>

## 故障排查

读法说明：根据现象查看相应处理方法。

| 现象 | 处理方法 |
|---|---|
| Docker 套接字或 cgroup 访问失败 | 在以 root 权限运行 Docker 的主机上执行，使用标准套接字和题目的验证器 compose 配置。 |
| 判分启动报告隔离错误 | 在该主机上运行镜像预检，解决所报告的内核、系统调用或身份切换要求。 |
| 工作容器准入报告容量不足 | 释放所需资源或选择更大的主机；保留题目声明的工作容器规格。 |
| 初始归档上传失败 | 检查 `resources.json`。对于特定的启动前根目录缺失错误，控制器会用相同提交和实例组自动重试，最多三次。其他错误会报告给运维人员处理。 |
| 缺少结果或判分失败 | 计算题目分数前，检查验证器日志和实例记录。 |

<a id="build-a-selected-adapter"></a>

## 构建选定适配器

```bash
tcsexam build --suite full --task ce-pace2021 --solver-protocol offline
```

题目的 `offline-adapter.json` 声明 Online 开发镜像、后端和验证工具依赖。
构建器解析这些依赖，并复用未变化的本地产物。资源输入和缓存选项见
[资源准备](resources.zh-CN.md)。开发和源码检查见[贡献指南](../.github/CONTRIBUTING.zh-CN.md)。
