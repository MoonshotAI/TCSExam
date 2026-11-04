<a id="solver-judge-isolation"></a>

# Solver 判分隔离

[English](judge-execution-isolation.md) | [简体中文](judge-execution-isolation.zh-CN.md)

本文描述 Solver 判分中的进程权限、网络访问、文件系统写入和清理机制。
面向 Online 与 Offline 判分镜像及后端服务的维护者。

<a id="check-the-execution-host"></a>

## 检查执行主机

判分需要 Linux x86-64、root 监督进程、seccomp 过滤器，以及已启用且至少为 3 的
Landlock ABI，并包含截断保护。预检会检查镜像的用户和用户组切换以及实际系统调用策略。
工作容器在开启 HTTP 监听前运行有时间上限的隔离执行预检；Offline 工作容器在判分前运行同一检查。
检查失败会在启动时退出，并通过现有判分启动失败流程报告。重试前先解决所报告的要求。

在实际 Docker 主机上检查准备好的判分镜像，可运行：

```sh
docker run --rm --network none --entrypoint python3 JUDGE_IMAGE \
  /judge/process_supervisor.py preflight
```

成功时输出包含 `ok`、`landlock_abi`、uid/gid、groups、`network_denied` 和
`descendant_network_denied` 的 JSON。探测程序会实际降低权限、安装策略、写入允许的输出，
并检查一个对所有用户可写的受保护标记文件无法被修改。它还检查提交进程及其执行的子进程均无法使用套接字，
同时允许私有 Unix 套接字对。内核不支持、Landlock LSM 被禁用、系统调用被拒绝，或无法切换身份都会导致失败。
更换容器用户空间无法补足主机内核缺少的支持。内核构建和启动配置都必须启用 Landlock；
参见 [Linux 内核文档](https://docs.kernel.org/userspace-api/landlock.html#kernel-support)。
容器 seccomp 策略必须允许三个 Landlock 系统调用。更换主机或其安全配置后，重新运行同一预检。

在实际执行判分的同一主机和镜像上运行预检。通过后，使用正常题目流程执行提交。

<a id="privileges-file-access-and-cleanup"></a>

## 权限、文件访问与清理

全部 30 道 Solver 题目共用 `assets/environments/solver/judge-runtime/execution.py`。
Online 判分通过 `run_checker.py` 安装它；通用 Offline 工作程序和各题专用 Offline 工作程序使用同一隔离边界。
计分层定义实例、参考值、时限和共享时间池。

构建和求解命令以 uid/gid 65534 运行，不含附加用户组。
可信验证程序和输入准备保留检查器身份。适配器根据已审查的构建、求解函数对调用分类；
未分类的计分子进程会明确报错。`test_judge_execution.py` 检查各计分实现的子进程分类。

不可信命令使用 `no_new_privs`，防止通过 setuid 可执行文件或文件 capabilities 提升权限。
其环境包含固定的可执行文件搜索路径、工作目录和临时目录设置、区域设置、数值预算及所需输出路径。
搜索路径包括开发镜像声明的可信 MiniZinc 和图工具目录；任意继承的 PATH、加载器设置、
Python 搜索路径和服务凭证均被排除。

继承的 seccomp 过滤器会阻止构建和求解进程创建、连接及监听套接字，并阻止 `io_uring`。
其范围涵盖互联网、回环和 Unix 域服务套接字。私有 Unix 套接字对、管道、线程和子进程仍可用于本地计算。
监督进程在执行命令前关闭标准输入、输出和错误以外的继承文件描述符。
过滤器安装失败会停止命令。

可信工作服务及其隧道保留网络访问，以接收提交并返回结果。
Harbor 开发容器的允许列表仍单独配置；Online Docker 工作容器由后端适配器创建，
并通过此共享运行时实施提交网络隔离。

Landlock 将文件系统写入限定在构建目录、`/app`、显式输出文件或目录，以及各命令独立的私有临时目录。
与输出文件共处一个目录的输入仍受保护。JSSP 使用独立的 `out-<instance>` 输出目录；
该目录可写，因此其文档说明的“写入临时文件再重命名”输出协议仍可使用。
随附 QBF 包装脚本的显式 `mktemp /tmp/...` 模板会重定向到私有 TMPDIR。
其他临时写入应使用 TMPDIR 或工作目录。

提交归档拒绝符号链接、硬链接和特殊文件。构建时可根据编译工具需要在构建目录内创建符号链接；
返回检查器之前会删除指向构建目录之外的链接。求解命令不能创建符号链接，
可信 Python 写入会拒绝沿符号链接访问。独立编译目录在可写入输入之前会恢复为 root 所有，
并移除用户组和其他用户的写权限。

每次提交和每个不可信命令均有独立的 Linux subreaper 监督进程，即负责接管并回收后代进程的进程。
即使使用 `setsid` 或两次 fork，它仍会清理后代进程。计分器的 SIGTERM 会转发到候选程序进程组，
并保留计分器原有的宽限期。计分器随后发出的 SIGKILL 使用独立的监督进程控制信号，
请求立即清理后代进程。正常退出和异常也会清理后台后代进程。清理仅作用于该监督进程的子进程。

清理时限为五秒。失败时写入可信执行错误标记。Online 工作程序在等待期间观察该标记，
记录 `judge_error`，停止队列，拒绝新提交，并返回不健康状态。
有时间上限的关闭等待不允许在清理问题未解决时复用工作容器。`/submissions` 保留已完成和失败记录，
并报告工作程序错误；后端归档这些记录，再调用现有失败分片销毁流程，停止实际工作容器。
Offline 工作程序以失败状态退出，由控制器删除容器。清理失败计为判分基础设施失败，
与候选程序构建失败或超时分别处理。
