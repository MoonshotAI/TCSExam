#!/usr/bin/env python3
"""Rebuild the CPSolver 1.2_bld46 library from its official release source.

Uses a private build directory and never replaces a task's bundled JAR.
Requires a JDK supporting --release 8 (verified with JDK 21).
"""

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Extracted official source directory")
    parser.add_argument("output", type=Path, help="New JAR path; must not already exist")
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    if output.exists():
        parser.error("Output already exists; choose a new path")
    for name in ("src", "lib/dom4j-1.6.1.jar", "lib/log4j-1.2.8.jar", "lgpl.txt"):
        if not (source / name).exists():
            parser.error(f"Missing required source material: {name}")
    for program in ("javac", "jar"):
        if not shutil.which(program):
            parser.error(f"JDK command not found: {program}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cpsolver-build-") as temporary:
        work = Path(temporary)
        shutil.copytree(source / "src", work / "src")
        constants = work / "src/net/sf/cpsolver/ifs/Constants.java"
        text = constants.read_text()
        for old, new in (
            ("int BLD_NUMBER = -1", "int BLD_NUMBER = 46"),
            ('String REL_DATE = "Unknown"', 'String REL_DATE = "Fri, 13 May 2011"'),
        ):
            if text.count(old) != 1:
                parser.error(f"Unexpected release metadata: {old}")
            text = text.replace(old, new)
        constants.write_text(text)
        classes = work / "classes"
        classes.mkdir()
        java_files = sorted((work / "src").rglob("*.java"))
        subprocess.run(
            ["javac", "--release", "8", "-encoding", "UTF-8", "-g",
             "-cp", str(source / "lib/*"), "-d", str(classes),
             *map(str, java_files)], check=True,
        )
        shutil.copy2(source / "lgpl.txt", classes / "lgpl.txt")
        manifest = work / "MANIFEST.MF"
        manifest.write_text(
            "Manifest-Version: 1.0\n"
            "Ifs-Version: 1.2_bld46\nCourseTT-Version: 1.2_bld46\n"
            "StudentSct-Version: 1.2_bld46\nExamTT-Version: 1.2_bld46\n"
            "Main-Class: net.sf.cpsolver.coursett.Test\n"
            "Class-Path: log4j-1.2.8.jar dom4j-1.6.1.jar\n\n"
        )
        subprocess.run(
            ["jar", "--create", "--file", str(output), "--manifest", str(manifest),
             "-C", str(classes), "."], check=True,
        )
        print(f"Rebuilt {len(java_files)} Java sources into {output}")


if __name__ == "__main__":
    main()
