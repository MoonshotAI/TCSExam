# CPSolver 1.2_bld46: source, build, and replacement

[English](cpsolver-source.md) | [简体中文](cpsolver-source.zh-CN.md)

This guide locates the CPSolver source and explains how to rebuild and replace its library.
It is for users running the course-timetabling task or distributing its Java dependencies.

The course-timetabling online and offline tasks use `environment/app/lib/cpsolver-all-1.2.jar`. Its SHA-256 is `73d4b2e866ddf3646cd29db919675ed49b6425873ed4b92f63a81df669b12366`; the JAR reports version 1.2_bld46 and release date 2011-05-13.

## Obtain the pinned source

The [official UniTime/cpsolver release commit](https://github.com/UniTime/cpsolver/commit/e2a59acaec364748bebd415f642eb16ee47dc274) is CPSolver build 46. Download and verify that source archive:

```sh
curl -fL --retry 3 \
  https://codeload.github.com/UniTime/cpsolver/tar.gz/e2a59acaec364748bebd415f642eb16ee47dc274 \
  -o cpsolver-1.2_bld46-source.tar.gz
echo '205bc712f28f013858657e535cec001e00e5450420357576ba683c50d854b77a  cpsolver-1.2_bld46-source.tar.gz' | sha256sum -c -
tar -xzf cpsolver-1.2_bld46-source.tar.gz
```

## Build

Building requires Python 3 and a JDK that supports `javac --release 8` (tested with JDK 21). From the repository root, substitute the extracted source and desired output paths:

```sh
python3 assets/environments/cpsolver/build_cpsolver_core.py \
  /path/to/cpsolver-e2a59acaec364748bebd415f642eb16ee47dc274 \
  /path/to/cpsolver-rebuilt.jar
```

The [build script](../../assets/environments/cpsolver/build_cpsolver_core.py) compiles in a temporary directory and refuses to overwrite an existing output. The upstream commit's `build.number` is 47; the script sets it to 46 to match the task JAR. Algorithm source is unchanged. The original Ant files target Java 5/6; this script produces Java 8-compatible classes.

The rebuilt JAR has different bytes from the task JAR. The [build record](third-party/cpsolver-build-verification.json) contains the public-interface comparison. Run task-level checks after replacing the library, and report the replacement when publishing evaluation results.

## Replace the library

In a copy of a task working directory, put the rebuilt JAR at `lib/cpsolver-all-1.2.jar`, keep `dom4j` and `log4j` beside it, and rerun that copy's `build.sh`. The wrapper loads libraries from `classes:lib/*`; it imposes no signature check or fixed JAR hash. Keep the original JAR for runs intended to reproduce the benchmark.

The core Java source is LGPL-3.0-or-later; original Ant files carry LGPL-2.1-or-later notices. Distribution of the binary must include its corresponding source and build materials, the [LGPL text](third-party/CPSolver-LGPL-3.0.txt), the [GPL text](third-party/GNU-GPL-3.0.txt), and the original [dom4j notice](third-party/dom4j-1.6.1-LICENSE.txt) and [log4j terms](third-party/Log4j-1.2.8-Apache-1.1.txt). Retain the applicable notice on each corresponding source file.
