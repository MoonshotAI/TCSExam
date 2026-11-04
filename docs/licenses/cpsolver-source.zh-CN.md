<a id="cpsolver-12_bld46-source-build-and-replacement"></a>

# CPSolver 1.2_bld46：源码、构建与替换

[English](cpsolver-source.md) | [简体中文](cpsolver-source.zh-CN.md)

中文译文供参考，许可条款以原文为准。

本指南给出 CPSolver 源码位置，并说明如何重建和替换其库。
供运行课程排课任务或分发其 Java 依赖的用户阅读。

课程排课的在线和离线任务使用 `environment/app/lib/cpsolver-all-1.2.jar`。其 SHA-256 为 `73d4b2e866ddf3646cd29db919675ed49b6425873ed4b92f63a81df669b12366`；JAR 报告的版本为 1.2_bld46，发布日期为 2011-05-13。

<a id="obtain-the-pinned-source"></a>

## 获取固定源码

[官方 UniTime/cpsolver 发布提交](https://github.com/UniTime/cpsolver/commit/e2a59acaec364748bebd415f642eb16ee47dc274) 对应 CPSolver build 46。下载并验证该源码归档：

```sh
curl -fL --retry 3 \
  https://codeload.github.com/UniTime/cpsolver/tar.gz/e2a59acaec364748bebd415f642eb16ee47dc274 \
  -o cpsolver-1.2_bld46-source.tar.gz
echo '205bc712f28f013858657e535cec001e00e5450420357576ba683c50d854b77a  cpsolver-1.2_bld46-source.tar.gz' | sha256sum -c -
tar -xzf cpsolver-1.2_bld46-source.tar.gz
```

<a id="build"></a>

## 构建

构建需要 Python 3，以及支持 `javac --release 8` 的 JDK（已用 JDK 21 测试）。从仓库根目录运行，将参数替换为已解压源码和所需输出路径：

```sh
python3 assets/environments/cpsolver/build_cpsolver_core.py \
  /path/to/cpsolver-e2a59acaec364748bebd415f642eb16ee47dc274 \
  /path/to/cpsolver-rebuilt.jar
```

[构建脚本](../../assets/environments/cpsolver/build_cpsolver_core.py)在临时目录中编译，若输出已存在则拒绝覆盖。上游提交的 `build.number` 为 47；脚本将其设为 46，以匹配任务 JAR。算法源码未修改。原始 Ant 文件面向 Java 5/6；此脚本生成兼容 Java 8 的类。

重建 JAR 的字节内容与任务 JAR 不同。[构建记录](third-party/cpsolver-build-verification.json)包含公开接口比较。替换库后执行任务级检查，并在发布评测结果时报告该替换。

<a id="replace-the-library"></a>

## 替换库

在任务工作目录的副本中，将重建 JAR 放到 `lib/cpsolver-all-1.2.jar`，在同一目录保留 `dom4j` 和 `log4j`，然后重新运行该副本的 `build.sh`。封装程序从 `classes:lib/*` 加载库，不检查签名或固定 JAR 哈希值。需要复现基准的运行应保留原始 JAR。

Java 核心源码采用 LGPL-3.0-or-later；原始 Ant 文件带有 LGPL-2.1-or-later 声明。分发二进制文件时，必须包含对应源码和构建材料、[LGPL 文本](third-party/CPSolver-LGPL-3.0.txt)、[GPL 文本](third-party/GNU-GPL-3.0.txt)，以及原始 [dom4j 声明](third-party/dom4j-1.6.1-LICENSE.txt)和 [log4j 条款](third-party/Log4j-1.2.8-Apache-1.1.txt)。为每份对应源码文件保留其适用声明。
