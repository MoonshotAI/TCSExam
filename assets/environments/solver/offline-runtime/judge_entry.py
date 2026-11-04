# SPDX-License-Identifier: Apache-2.0
"""Run an unchanged checker with CPU indices mapped to the worker's CPUs."""
import json
import os
from pathlib import Path
import runpy
import sys


def taskset_command(command, allowed, relative):
    if (not relative or not isinstance(command, (list, tuple)) or len(command) < 4
            or Path(str(command[0])).name != 'taskset' or command[1] != '-c'):
        return command
    indices = str(command[2]).split(',')
    if not all(x.isdigit() and int(x) < len(allowed) for x in indices):
        raise RuntimeError('Judge requested a CPU outside its reserved worker')
    result = list(command)
    result[2] = ','.join(str(allowed[int(index)]) for index in indices)
    return result


def main():
    config = json.loads(Path('/opt/public_judge/task.json').read_text())
    sys.path.insert(0, '/judge')
    from execution import install
    install(config)
    sys.path.insert(0, config['module_dir'])
    sys.argv = ['/tests/checker.py']
    runpy.run_path('/tests/checker.py', run_name='__main__')


if __name__ == '__main__':
    main()
