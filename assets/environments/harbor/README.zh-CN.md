<a id="harbor-egress-control-build-context"></a>

# Harbor 出站网络控制构建上下文

[English](README.md) | [简体中文](README.zh-CN.md)

这些说明供准备可选 Docker 网络控制辅助工具的维护者阅读，不作为任务说明。

`egress-control/` 是 [`harbor==0.22.0`](https://pypi.org/project/harbor/0.22.0/) Python 包内 Docker 出站网络控制上下文中五个文件的未修改副本。包元数据声明采用 Apache-2.0；随附许可原文保存在 `LICENSE` 中。

命令行工具先统一文件和目录权限，再使用 `Dockerfile`、空构建参数和 `linux/amd64` 平台计算 Harbor 的 `docker_build_context_hash`。声明的哈希值记录在 [`assets/sources.json`](../../sources.json) 的 `harbor-0220-egress-control` 项中；宿主机支持镜像的声明使用相同数值。一致性测试将这两处声明与 Harbor 已安装的上下文及统一权限后的随包文件进行比较：

```bash
python -m pytest src/tcsexam/tests/test_harbor_egress_control.py
```

来源材料应保存在 `egress-control/` 之外：Harbor 的哈希计算覆盖该目录中的每个文件及其权限模式。
